"""Secret-safe, deliberately small Intervals.icu activity adapter.

All network access is injected through ``session`` so unit tests never contact
Intervals.  Mutation callers must still use the reconciliation preview/apply
flow; this module only implements provider capabilities.
"""
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, BinaryIO

import requests

BASE_URL = "https://intervals.icu/api/v1"
SUPPORTED_ARTIFACT_SUFFIXES = (".fit", ".tcx", ".gpx", ".zip", ".gz")


@dataclass(frozen=True)
class IntervalsActivity:
    id: str
    name: str
    start_date_local: str
    type: str
    source: str | None = None
    external_id: str | None = None
    distance: float | None = None
    moving_time: float | None = None

    def fingerprint(self) -> str:
        values = (self.id, self.name, self.start_date_local, self.type, self.source,
                  self.external_id, self.distance, self.moving_time)
        return sha256(repr(values).encode()).hexdigest()


class IntervalsError(RuntimeError):
    """An actionable provider error which never includes credentials."""


class IntervalsNotFoundError(IntervalsError):
    pass


class IntervalsUnsupportedUpdateError(IntervalsError):
    pass


class IntervalsClient:
    def __init__(self, athlete_id: str, api_key: str, session: Any = None):
        if not api_key:
            raise ValueError("Intervals API key is required")
        self.athlete_id = str(athlete_id)
        self._api_key = api_key
        self.session = session or requests.Session()

    @property
    def _headers(self) -> dict[str, str]:
        # requests accepts Basic auth too, but preserving this header keeps the
        # adapter compatible with the documented personal-key contract.
        return {"Authorization": f"Basic {self._api_key}"}

    def list_activities(self, oldest: str, newest: str) -> list[IntervalsActivity]:
        if not oldest or not newest:
            raise ValueError("Intervals inventory requires bounded oldest and newest dates")
        response = self.session.get(
            f"{BASE_URL}/athlete/{self.athlete_id}/activities",
            params={"oldest": oldest, "newest": newest}, headers=self._headers,
        )
        payload = self._json(response)
        if not isinstance(payload, list):
            raise IntervalsError("Intervals activity inventory returned an invalid response")
        return [self._decode(item) for item in payload]

    def get_activity(self, activity_id: str) -> IntervalsActivity:
        response = self.session.get(f"{BASE_URL}/activity/{activity_id}", headers=self._headers)
        return self._decode(self._json(response))

    def download_source_artifact(self, activity_id: str) -> bytes:
        response = self.session.get(f"{BASE_URL}/activity/{activity_id}/file", headers=self._headers)
        self._raise_for_status(response)
        return bytes(response.content)

    def upload(self, remote_id: str | None, payload: dict[str, Any]) -> str:
        artifact = payload.get("artifact")
        external_id = payload.get("external_id")
        if artifact is None or external_id is None:
            raise ValueError("Intervals upload requires artifact and external_id")
        filename, stream = self._artifact_file(artifact)
        response = self.session.post(
            f"{BASE_URL}/athlete/{self.athlete_id}/activities",
            params={"external_id": str(external_id)}, headers=self._headers,
            files={"file": (filename, stream)},
        )
        decoded = self._json(response)
        return str(decoded.get("id", external_id)) if isinstance(decoded, dict) else str(external_id)

    create = upload

    def update(self, remote_id: str, payload: dict[str, Any]) -> str:
        if not remote_id:
            raise ValueError("Intervals update requires an exact activity id")
        existing = self.get_activity(remote_id)
        if (existing.source or "").upper() == "STRAVA":
            raise IntervalsUnsupportedUpdateError("Intervals does not support updating Strava-sourced activities")
        allowed = {"name", "type", "start_date_local", "distance", "moving_time"}
        changes = {key: value for key, value in payload.items() if key in allowed}
        if not changes:
            raise ValueError("Intervals update contains no supported changed fields")
        response = self.session.put(f"{BASE_URL}/activity/{remote_id}", json=changes, headers=self._headers)
        self._json(response)
        return str(remote_id)

    def delete(self, remote_id: str, payload: dict[str, Any] | None = None) -> None:
        if not remote_id:
            raise ValueError("Intervals deletion requires an exact activity id")
        response = self.session.delete(f"{BASE_URL}/activity/{remote_id}", headers=self._headers)
        self._raise_for_status(response)

    def destructive_consequence(self, activity: IntervalsActivity) -> str:
        if (activity.source or "").upper() in {"GARMIN", "STRAVA", "FITBIT", "POLAR"}:
            return "Deletes an externally sourced activity and creates an Intervals tombstone; it is not removed automatically."
        return "Deletes this application-uploaded activity without an external-service tombstone."

    def verify(self, remote_id: str | None, payload: dict[str, Any]) -> bool:
        if remote_id is None:
            return False
        try:
            actual = self.get_activity(remote_id)
        except IntervalsNotFoundError:
            return payload.get("deleted") is True
        return all(getattr(actual, key) == value for key, value in payload.items()
                   if key in {"name", "type", "start_date_local", "external_id", "distance", "moving_time"})

    def fingerprint_for(self, remote_id: str | None) -> str | None:
        return self.get_activity(remote_id).fingerprint() if remote_id else None

    def _artifact_file(self, artifact: Any) -> tuple[str, BinaryIO]:
        if isinstance(artifact, tuple) and len(artifact) == 2:
            filename, stream = artifact
        else:
            filename, stream = getattr(artifact, "name", "activity.fit"), artifact
        if not str(filename).lower().endswith(SUPPORTED_ARTIFACT_SUFFIXES):
            raise ValueError("Intervals source artifact must be FIT, TCX, GPX, ZIP, or GZ")
        return str(filename), stream

    def _json(self, response: Any) -> Any:
        self._raise_for_status(response)
        try:
            return response.json()
        except Exception as exc:
            raise IntervalsError("Intervals returned invalid JSON") from exc

    def _raise_for_status(self, response: Any) -> None:
        code = getattr(response, "status_code", None)
        if code == 404:
            raise IntervalsNotFoundError("Intervals activity was not found")
        if code in {401, 403}:
            raise IntervalsError("Intervals authentication or access was denied")
        if code == 429 or (isinstance(code, int) and code >= 500):
            raise IntervalsError("Intervals is temporarily unavailable; retry later")
        try:
            response.raise_for_status()
        except Exception as exc:
            raise IntervalsError(f"Intervals request failed ({code if code is not None else 'unknown'})") from exc

    @staticmethod
    def _decode(raw: dict[str, Any]) -> IntervalsActivity:
        try:
            return IntervalsActivity(str(raw["id"]), str(raw.get("name", "")),
                str(raw.get("start_date_local", "")), str(raw.get("type", "")),
                raw.get("source"), str(raw["external_id"]) if raw.get("external_id") is not None else None,
                raw.get("distance"), raw.get("moving_time"))
        except (KeyError, TypeError) as exc:
            raise IntervalsError("Intervals activity response is missing an id") from exc
