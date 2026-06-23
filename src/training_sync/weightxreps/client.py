"""GraphQL client for Weight x Reps."""

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
        }
      }
    }
  }
}
"""


class WeightxRepsClient:
    def __init__(self, access_token: str, session=None) -> None:
        self.access_token = access_token
        self.session = session or requests.Session()

    def graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.session.post(
            GRAPHQL_ENDPOINT,
            json={"query": query, "variables": variables or {}},
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("errors"):
            raise RuntimeError(payload["errors"])
        return payload.get("data", {})

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

    def verify_day(self, date: str, rows: list[dict[str, Any]]) -> bool:
        day = self.jeditor_day(date)
        if not day:
            return False

        expected_blocks = sum(
            1
            for row in rows
            if row.get("eid") is not None
        )
        saved_blocks = [
            token
            for token in day.get("did") or []
            if token.get("__typename") == "JEditorEBlock"
        ]
        if len(saved_blocks) < expected_blocks:
            return False

        for block in saved_blocks[:expected_blocks]:
            sets = block.get("sets") or []
            if not sets:
                return False
            if any(set_row.get("type") != 0 for set_row in sets):
                return False

        return True


def _default_date_from_rows(rows: list[dict[str, Any]]) -> str:
    for row in rows:
        if row.get("on"):
            return row["on"]
    raise ValueError("JEditor rows must include an on date")
