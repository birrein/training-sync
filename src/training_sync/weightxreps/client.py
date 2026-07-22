"""GraphQL client for Weight x Reps."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import requests

from training_sync.renderers.weightxreps_text import (
    ParsedExercise,
    ParsedSetLine,
    ParsedTrainingDay,
    validate_strength_round_trip,
)

GRAPHQL_ENDPOINT = "https://weightxreps.net/api/graphql"

SAVE_JEDITOR_MUTATION = """
mutation SaveJEditor($rows: [JEditorSaveRow], $defaultDate: YMD!) {
  saveJEditor(rows: $rows, defaultDate: $defaultDate)
}
"""

JEDITOR_QUERY = """
query JEditorDay($ymd: YMD!, $range: Int) {
  jeditor(ymd: $ymd, range: $range) {
    baseBW
    exercises {
      e {
        id
        name
      }
    }
    did {
      __typename
      ... on JEditorDayTag {
        on
      }
      ... on JEditorBWTag {
        bw
      }
      ... on JEditorEBlock {
        e
        sets {
          v
          r
          s
          lb
          usebw
          type
          t
          d
          dunit
          c
        }
      }
    }
  }
}
"""

EXERCISE_CATALOG_QUERY = """
query ExerciseCatalog($uid: ID!) {
  getExercises(uid: $uid) {
    e {
      id
      name
    }
  }
}
"""


class VerificationMismatch(RuntimeError):
    def __init__(
        self,
        *,
        expected: list[dict[str, Any]],
        observed: list[dict[str, Any]],
    ) -> None:
        self.expected = expected
        self.observed = observed
        super().__init__(
            f"Weight x Reps verification mismatch: expected={expected!r}, observed={observed!r}"
        )


class UnrepresentableRemoteDay(RuntimeError):
    """Raised when a remote day cannot be preserved without losing data."""


@dataclass(frozen=True)
class RemoteDaySnapshot:
    preserved: ParsedTrainingDay
    has_content: bool


class WeightxRepsClient:
    def __init__(
        self,
        access_token: str,
        session=None,
        token_refresher: Callable[[], str] | None = None,
    ) -> None:
        self.access_token = access_token
        self.session = session or requests.Session()
        self.token_refresher = token_refresher

    def graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._post_graphql(query, variables)
        if response.status_code == 401 and self.token_refresher is not None:
            self.access_token = self.token_refresher()
            response = self._post_graphql(query, variables)

        try:
            payload = response.json()
        except ValueError:
            response.raise_for_status()
            raise

        if isinstance(payload, dict) and payload.get("errors"):
            raise RuntimeError(payload["errors"])
        response.raise_for_status()
        if not isinstance(payload, dict):
            raise RuntimeError("Weight x Reps GraphQL response must be a JSON object")
        return payload.get("data", {})

    def _post_graphql(self, query: str, variables: dict[str, Any] | None = None):
        return self.session.post(
            GRAPHQL_ENDPOINT,
            json={"query": query, "variables": variables or {}},
            headers={"Authorization": f"Bearer {self.access_token}"},
        )

    def save_jeditor(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        default_date = _default_date_from_rows(rows)
        return self.graphql(
            SAVE_JEDITOR_MUTATION,
            {"rows": rows, "defaultDate": default_date},
        )

    def jeditor_day(self, date: str) -> dict[str, Any] | None:
        data = self.graphql(JEDITOR_QUERY, {"ymd": date, "range": 0})
        return data.get("jeditor")

    def day_has_content(self, date: str) -> bool:
        day = self.jeditor_day(date)
        if not day:
            return False
        return bool(day.get("did") or day.get("baseBW"))

    def remote_day_snapshot(self, date: str) -> RemoteDaySnapshot:
        """Read the remote day and retain every safely representable preserved field."""

        return _remote_day_snapshot(date, self.jeditor_day(date))

    def exercise_ids(self, date: str) -> dict[str, int]:
        day = self.jeditor_day(date)
        if not day:
            return {}

        ids: dict[str, int] = {}
        for exercise_stat in day.get("exercises") or []:
            exercise = exercise_stat.get("e") or {}
            name = exercise.get("name")
            exercise_id = exercise.get("id")
            if name and exercise_id:
                ids[name] = int(exercise_id)
        return ids

    def exercise_catalog(self, user_id: int) -> dict[str, int]:
        data = self.graphql(EXERCISE_CATALOG_QUERY, {"uid": user_id})
        ids: dict[str, int] = {}
        for exercise_stat in data.get("getExercises") or []:
            exercise = exercise_stat.get("e") or {}
            name = exercise.get("name")
            exercise_id = exercise.get("id")
            if name and exercise_id:
                ids[name] = int(exercise_id)
        return ids

    def verify_day(self, date: str, rows: list[dict[str, Any]]) -> None:
        day = self.jeditor_day(date)
        expected = _normalize_expected_blocks(rows)
        observed = _normalize_observed_blocks(day)
        if expected != observed:
            raise VerificationMismatch(expected=expected, observed=observed)


def _default_date_from_rows(rows: list[dict[str, Any]]) -> str:
    for row in rows:
        if row.get("on"):
            return row["on"]
    raise ValueError("JEditor rows must include an on date")


def _normalize_expected_blocks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if "bw" in row:
            normalized.append({"bw": row["bw"]})
        elif row.get("eid") is not None:
            normalized.append(
                {
                    "eid": row["eid"],
                    "sets": [
                        _normalize_expected_set(set_row)
                        for set_row in row.get("erows") or []
                    ],
                }
            )
    return normalized


def _normalize_expected_set(set_row: dict[str, Any]) -> dict[str, Any]:
    set_type = set_row.get("type")
    if set_type == 0:
        weight = set_row.get("w") or {}
        return {
            "type": set_type,
            "v": weight.get("v"),
            "r": set_row.get("r"),
            "s": set_row.get("s"),
            "lb": _zero_default(weight.get("lb")),
            "usebw": _zero_default(weight.get("usebw")),
            "c": _empty_comment_default(set_row.get("c")),
        }
    distance = set_row.get("d")
    if isinstance(distance, dict):
        distance_value = distance.get("val")
        distance_unit = distance.get("unit")
    else:
        distance_value = distance
        distance_unit = set_row.get("dunit")
    return {
        "type": set_row.get("type"),
        "t": set_row.get("t"),
        "d": distance_value,
        "dunit": distance_unit,
        "c": _empty_comment_default(set_row.get("c")),
    }


def _normalize_observed_blocks(day: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not day:
        return []
    normalized: list[dict[str, Any]] = []
    for token in day.get("did") or []:
        token_type = token.get("__typename")
        if token_type == "JEditorBWTag":
            normalized.append({"bw": token.get("bw")})
        elif token_type == "JEditorEBlock":
            normalized.append(
                {
                    "eid": token.get("e"),
                    "sets": [
                        _normalize_observed_set(set_row)
                        for set_row in token.get("sets") or []
                    ],
                }
            )
    return normalized


def _normalize_observed_set(set_row: dict[str, Any]) -> dict[str, Any]:
    set_type = set_row.get("type")
    if set_type == 0:
        return {
            "type": set_type,
            "v": set_row.get("v"),
            "r": set_row.get("r"),
            "s": set_row.get("s"),
            "lb": _zero_default(set_row.get("lb")),
            "usebw": _zero_default(set_row.get("usebw")),
            "c": _empty_comment_default(set_row.get("c")),
        }
    return {
        "type": set_type,
        "t": set_row.get("t"),
        "d": set_row.get("d"),
        "dunit": set_row.get("dunit"),
        "c": _empty_comment_default(set_row.get("c")),
    }


def _zero_default(value: Any) -> Any:
    return 0 if value is None else value


def _empty_comment_default(value: Any) -> Any:
    return None if value in (None, "") else value


def _remote_day_snapshot(
    date: str,
    day: dict[str, Any] | None,
) -> RemoteDaySnapshot:
    if not day:
        return RemoteDaySnapshot(
            preserved=ParsedTrainingDay(date=date, body_weight_kg=None),
            has_content=False,
        )

    exercise_names = {
        int(exercise["id"]): str(exercise["name"])
        for stat in day.get("exercises") or []
        if (exercise := stat.get("e"))
        and exercise.get("id") is not None
        and exercise.get("name")
    }
    body_weight: float | None = None
    exercises: list[ParsedExercise] = []
    has_content = False

    for token in day.get("did") or []:
        token_type = token.get("__typename")
        if token_type == "JEditorDayTag":
            continue
        has_content = True
        if token_type == "JEditorBWTag":
            if body_weight is not None or token.get("bw") is None:
                _unrepresentable(date, "duplicate or missing bodyweight")
            body_weight = float(token["bw"])
            continue
        if token_type != "JEditorEBlock":
            _unrepresentable(date, f"unsupported token {token_type!r}")

        sets = token.get("sets") or []
        set_types = {set_row.get("type") for set_row in sets}
        if sets and set_types.issubset({1, 2}):
            continue
        if not sets or set_types != {0}:
            _unrepresentable(date, f"exercise {token.get('e')!r} has unsupported set types")

        exercise_id = token.get("e")
        try:
            exercise_name = exercise_names[int(exercise_id)]
        except (KeyError, TypeError, ValueError):
            _unrepresentable(date, f"exercise {exercise_id!r} has no resolvable name")
        exercises.append(
            ParsedExercise(
                name=exercise_name,
                sets=[_remote_strength_set(date, exercise_id, set_row) for set_row in sets],
            )
        )

    preserved = ParsedTrainingDay(
        date=date,
        body_weight_kg=body_weight,
        exercises=exercises,
    )
    try:
        validate_strength_round_trip(preserved)
    except ValueError as exc:
        _unrepresentable(date, str(exc))
    return RemoteDaySnapshot(preserved=preserved, has_content=has_content)


def _remote_strength_set(
    date: str,
    exercise_id: object,
    set_row: dict[str, Any],
) -> ParsedSetLine:
    if set_row.get("lb") not in (None, False, 0):
        _unrepresentable(date, f"exercise {exercise_id!r} uses non-metric weight")
    if set_row.get("c") not in (None, ""):
        _unrepresentable(date, f"exercise {exercise_id!r} has a strength comment")
    if (
        set_row.get("t") not in (None, 0)
        or set_row.get("d") not in (None, 0)
        or set_row.get("dunit") not in (None, "")
    ):
        _unrepresentable(date, f"exercise {exercise_id!r} has mixed strength metadata")
    try:
        weight = float(set_row["v"])
        reps = int(set_row["r"])
        set_count = int(set_row["s"])
    except (KeyError, TypeError, ValueError):
        _unrepresentable(date, f"exercise {exercise_id!r} has invalid strength fields")
    if set_count < 1 or reps < 0:
        _unrepresentable(date, f"exercise {exercise_id!r} has invalid reps or set count")
    usebw = set_row.get("usebw")
    if usebw not in (None, False, True, 0, 1):
        _unrepresentable(date, f"exercise {exercise_id!r} has invalid usebw")
    return ParsedSetLine(
        weight_kg=weight,
        reps=(reps,) * set_count,
        uses_bodyweight=bool(usebw),
    )


def _unrepresentable(date: str, detail: str) -> None:
    raise UnrepresentableRemoteDay(
        f"Weight x Reps day {date} is unrepresentable without data loss: {detail}"
    )
