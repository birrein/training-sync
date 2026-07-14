"""GraphQL client for Weight x Reps."""

from collections.abc import Callable
from typing import Any

import requests

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
query ExerciseCatalog($uid: Int!) {
  getExercises(uid: $uid) {
    id
    name
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

        response.raise_for_status()
        payload = response.json()
        if payload.get("errors"):
            raise RuntimeError(payload["errors"])
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
        return {
            exercise["name"]: int(exercise["id"])
            for exercise in data.get("getExercises") or []
            if exercise.get("name") and exercise.get("id")
        }

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
    return [
        {
            "eid": row["eid"],
            "sets": [_normalize_expected_set(set_row) for set_row in row.get("erows") or []],
        }
        for row in rows
        if row.get("eid") is not None
    ]


def _normalize_expected_set(set_row: dict[str, Any]) -> dict[str, Any]:
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
    }


def _normalize_observed_blocks(day: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not day:
        return []
    return [
        {
            "eid": token.get("e"),
            "sets": [_normalize_observed_set(set_row) for set_row in token.get("sets") or []],
        }
        for token in day.get("did") or []
        if token.get("__typename") == "JEditorEBlock"
    ]


def _normalize_observed_set(set_row: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": set_row.get("type"),
        "t": set_row.get("t"),
        "d": set_row.get("d"),
        "dunit": set_row.get("dunit"),
    }
