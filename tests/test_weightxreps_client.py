from training_sync.weightxreps.client import WeightxRepsClient


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payload=None):
        self.calls = []
        self.responses = [
            response if isinstance(response, FakeResponse) else FakeResponse(response)
            for response in (
                payload
                if isinstance(payload, list)
                else [payload or {"data": {"saveJEditor": True}}]
            )
        ]

    def post(self, url, json, headers):
        self.calls.append((url, json, headers))
        return self.responses.pop(0)


def test_graphql_posts_with_bearer_token():
    session = FakeSession()
    client = WeightxRepsClient(access_token="token-123", session=session)

    result = client.graphql("mutation X { x }", {"rows": []})

    assert result == {"saveJEditor": True}
    assert session.calls[0][0] == "https://weightxreps.net/api/graphql"
    assert session.calls[0][2]["Authorization"] == "Bearer token-123"


def test_graphql_refreshes_token_once_after_unauthorized_response():
    session = FakeSession(
        [
            FakeResponse({"errors": ["expired"]}, status_code=401),
            FakeResponse({"data": {"saveJEditor": True}}),
        ]
    )
    refresh_calls = []

    def refresh_token():
        refresh_calls.append("refresh")
        return "fresh-token"

    client = WeightxRepsClient(
        access_token="expired-token",
        session=session,
        token_refresher=refresh_token,
    )

    result = client.graphql("mutation X { x }", {"rows": []})

    assert result == {"saveJEditor": True}
    assert refresh_calls == ["refresh"]
    assert session.calls[0][2]["Authorization"] == "Bearer expired-token"
    assert session.calls[1][2]["Authorization"] == "Bearer fresh-token"


def test_save_jeditor_sends_rows_variable():
    session = FakeSession()
    client = WeightxRepsClient(access_token="token-123", session=session)

    client.save_jeditor([{"on": "2026-06-19", "did": []}])

    payload = session.calls[0][1]
    assert "saveJEditor" in payload["query"]
    assert payload["variables"] == {
        "rows": [{"on": "2026-06-19", "did": []}],
        "defaultDate": "2026-06-19",
    }


def test_jeditor_day_reads_existing_editor_data():
    session = FakeSession(
        {
            "data": {
                "jeditor": {
                    "baseBW": 71.4,
                    "did": [{"__typename": "JEditorDayTag", "on": "2026-06-19"}],
                    "exercises": [],
                }
            }
        }
    )
    client = WeightxRepsClient(access_token="token-123", session=session)

    data = client.jeditor_day("2026-06-19")

    assert data["baseBW"] == 71.4
    assert "jeditor" in session.calls[0][1]["query"]
    assert "type" in session.calls[0][1]["query"]
    assert session.calls[0][1]["variables"] == {"ymd": "2026-06-19", "range": 0}


def test_day_has_content_uses_jeditor_data():
    session = FakeSession(
        {
            "data": {
                "jeditor": {
                    "baseBW": None,
                    "did": [{"__typename": "JEditorDayTag", "on": "2026-06-19"}],
                    "exercises": [],
                }
            }
        }
    )
    client = WeightxRepsClient(access_token="token-123", session=session)

    assert client.day_has_content("2026-06-19") is True


def test_exercise_ids_reads_existing_editor_exercises():
    session = FakeSession(
        {
            "data": {
                "jeditor": {
                    "baseBW": None,
                    "did": [],
                    "exercises": [
                        {"e": {"id": "157728", "name": "Barbell Back Squat"}},
                        {"e": {"id": "158078", "name": "Hanging Knee Raise"}},
                    ],
                }
            }
        }
    )
    client = WeightxRepsClient(access_token="token-123", session=session)

    assert client.exercise_ids("2026-06-20") == {
        "Barbell Back Squat": 157728,
        "Hanging Knee Raise": 158078,
    }


def test_verify_day_requires_saved_exercise_blocks_with_weight_x_reps_type():
    session = FakeSession(
        {
            "data": {
                "jeditor": {
                    "baseBW": None,
                    "did": [
                        {"__typename": "JEditorDayTag", "on": "2026-06-20"},
                        {
                            "__typename": "JEditorEBlock",
                            "e": 157728,
                            "sets": [{"v": 47, "r": 8, "s": 1, "type": 0}],
                        },
                    ],
                    "exercises": [],
                }
            }
        }
    )
    client = WeightxRepsClient(access_token="token-123", session=session)

    assert client.verify_day("2026-06-20", [{"eid": 157728, "erows": []}]) is True


def test_verify_day_rejects_saved_sets_without_type():
    session = FakeSession(
        {
            "data": {
                "jeditor": {
                    "baseBW": None,
                    "did": [
                        {
                            "__typename": "JEditorEBlock",
                            "e": 157728,
                            "sets": [{"v": 47, "r": 8, "s": 1, "type": None}],
                        },
                    ],
                    "exercises": [],
                }
            }
        }
    )
    client = WeightxRepsClient(access_token="token-123", session=session)

    assert client.verify_day("2026-06-20", [{"eid": 157728, "erows": []}]) is False
