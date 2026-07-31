import io
from base64 import b64encode

import pytest

from training_sync.intervals.client import (
    IntervalsClient, IntervalsError, IntervalsNotFoundError, IntervalsUnsupportedUpdateError,
)


class Response:
    def __init__(self, payload=None, status_code=200, content=b"fit"):
        self.payload, self.status_code, self.content = payload, status_code, content
    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http")
    def json(self): return self.payload


class Session:
    def __init__(self, responses): self.responses, self.calls = list(responses), []
    def _call(self, method, *args, **kwargs):
        self.calls.append((method, args, kwargs)); return self.responses.pop(0)
    def get(self, *args, **kwargs): return self._call("get", *args, **kwargs)
    def post(self, *args, **kwargs): return self._call("post", *args, **kwargs)
    def put(self, *args, **kwargs): return self._call("put", *args, **kwargs)
    def delete(self, *args, **kwargs): return self._call("delete", *args, **kwargs)


def row(**overrides):
    value = {"id": 1, "name": "Ride", "start_date_local": "2026-07-29T08:00:00", "type": "Ride", "external_id": "123", "source": "GARMIN", "distance": 20.0, "moving_time": 3600}
    value.update(overrides); return value


def test_inventory_is_bounded_and_decoded():
    session = Session([Response([row()])])
    rows = IntervalsClient("a", "secret", session).list_activities("2026-07-29", "2026-07-29")
    assert rows[0].id == "1"
    assert session.calls[0][2]["params"] == {"oldest": "2026-07-29", "newest": "2026-07-29"}


def test_inventory_uses_intervals_personal_key_basic_auth_shape():
    session = Session([Response([])])
    IntervalsClient("0", "secret", session).list_activities("2026-07-29", "2026-07-29")
    assert session.calls[0][2]["headers"]["Authorization"] == (
        "Basic " + b64encode(b"API_KEY:secret").decode()
    )


def test_exact_get_download_and_actionable_error_are_secret_safe():
    session = Session([Response(row()), Response(content=b"source"), Response(status_code=403)])
    client = IntervalsClient("a", "secret-value", session)
    assert client.get_activity("1").external_id == "123"
    assert client.download_source_artifact("1") == b"source"
    with pytest.raises(IntervalsError, match="authentication") as exc:
        client.get_activity("1")
    assert "secret-value" not in str(exc.value)


def test_upload_partial_update_strava_rejection_and_exact_delete():
    session = Session([Response({"id": 9}), Response(row()), Response({}), Response(row(source="STRAVA")), Response(status_code=204)])
    client = IntervalsClient("a", "secret", session)
    uploaded = client.upload(None, {"external_id": "123", "artifact": ("ride.fit", io.BytesIO(b"fit"))})
    assert uploaded == "9"
    assert session.calls[0][2]["params"] == {"external_id": "123"}
    assert client.update("1", {"name": "Fixed", "ignored": "x"}) == "1"
    assert session.calls[2][2]["json"] == {"name": "Fixed"}
    with pytest.raises(IntervalsUnsupportedUpdateError):
        client.update("2", {"name": "No"})
    client.delete("1")
    assert session.calls[-1][1][0].endswith("/activity/1")


def test_delete_tombstone_and_not_found_verification():
    client = IntervalsClient("a", "secret", Session([Response(row(source="GARMIN")), Response(status_code=404)]))
    assert "tombstone" in client.destructive_consequence(client.get_activity("1"))
    assert client.verify("1", {"deleted": True})
    with pytest.raises(ValueError, match="exact"):
        client.delete("")


def test_garmin_connect_source_deletion_discloses_tombstone():
    activity = row(source="GARMIN_CONNECT")
    client = IntervalsClient("a", "secret", Session([]))
    assert "creates an Intervals tombstone" in client.destructive_consequence(client._decode(activity))


@pytest.mark.parametrize("filename", ["ride.fit", "ride.tcx", "ride.gpx", "ride.zip", "ride.gz"])
def test_supported_artifact_types_are_uploaded(filename):
    session = Session([Response({"id": 1})])
    IntervalsClient("a", "secret", session).upload(None, {"external_id": "42", "artifact": (filename, io.BytesIO(b"x"))})
    assert session.calls


def test_unsupported_artifact_never_mutates():
    session = Session([])
    with pytest.raises(ValueError, match="FIT"):
        IntervalsClient("a", "secret", session).upload(None, {"external_id": "42", "artifact": ("ride.csv", io.BytesIO())})
    assert not session.calls
