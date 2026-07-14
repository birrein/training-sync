import pytest

from training_sync.weightxreps.client import VerificationMismatch, WeightxRepsClient


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


def test_exercise_catalog_reads_remote_exercise_names():
    session = FakeSession(
        {
            "data": {
                "getExercises": [
                    {"id": "157721", "name": "Barbell Hip Thrust"},
                    {"id": "158078", "name": "Hanging Knee Raise"},
                ]
            }
        }
    )
    client = WeightxRepsClient(access_token="token-123", session=session)

    catalog = client.exercise_catalog(user_id=12345)

    assert catalog == {
        "Barbell Hip Thrust": 157721,
        "Hanging Knee Raise": 158078,
    }
    assert "getExercises" in session.calls[0][1]["query"]
    assert session.calls[0][1]["variables"] == {"uid": 12345}


def _expected_rows():
    return [
        {"on": "2026-06-20"},
        {
            "eid": 157728,
            "erows": [{"w": {"v": 47, "lb": 0}, "r": 8, "s": 1, "type": 0}],
        },
        {"eid": 157737, "erows": [{"type": 1, "t": 1_800_000}]},
        {
            "eid": 157740,
            "erows": [
                {
                    "type": 2,
                    "t": 2_700_000,
                    "d": {"val": 279_500_000, "unit": "km"},
                    "c": "ignored during verification",
                }
            ],
        },
    ]


def _observed_blocks():
    return [
        {
            "__typename": "JEditorEBlock",
            "e": 157728,
            "sets": [
                {
                    "v": 47,
                    "r": 8,
                    "s": 1,
                    "type": 0,
                    "t": None,
                    "d": None,
                    "dunit": None,
                }
            ],
        },
        {
            "__typename": "JEditorEBlock",
            "e": 157737,
            "sets": [{"type": 1, "t": 1_800_000, "d": None, "dunit": None}],
        },
        {
            "__typename": "JEditorEBlock",
            "e": 157740,
            "sets": [{"type": 2, "t": 2_700_000, "d": 279_500_000, "dunit": "km"}],
        },
    ]


def _verification_client(blocks):
    return WeightxRepsClient(
        access_token="token-123",
        session=FakeSession(
            {
                "data": {
                    "jeditor": {
                        "baseBW": None,
                        "did": blocks,
                        "exercises": [],
                    }
                }
            }
        ),
    )


def test_jeditor_query_requests_structured_set_fields():
    session = FakeSession(
        {
            "data": {
                "jeditor": {
                    "baseBW": None,
                    "did": [
                        {"__typename": "JEditorDayTag", "on": "2026-06-20"},
                        *_observed_blocks(),
                    ],
                    "exercises": [],
                }
            }
        }
    )
    client = WeightxRepsClient(access_token="token-123", session=session)

    client.verify_day("2026-06-20", _expected_rows())

    query = session.calls[0][1]["query"]
    for field in ("type", "t", "d", "dunit", "c"):
        assert field in query


def test_verify_day_accepts_exact_strength_duration_and_distance_blocks():
    client = _verification_client(_observed_blocks())

    assert client.verify_day("2026-06-20", _expected_rows()) is None


@pytest.mark.parametrize(
    ("mutate", "expected_value", "observed_value"),
    [
        (lambda blocks: blocks.pop(1), 157737, 157740),
        (lambda blocks: blocks[2]["sets"][0].pop("dunit"), "km", None),
        (lambda blocks: blocks[2]["sets"][0].update(type=1), 2, 1),
        (lambda blocks: blocks[1]["sets"][0].update(t=1_700_000), 1_800_000, 1_700_000),
        (lambda blocks: blocks[2]["sets"][0].update(d=123), 279_500_000, 123),
        (lambda blocks: blocks[2]["sets"][0].update(dunit="mi"), "km", "mi"),
    ],
    ids=[
        "missing-exercise",
        "missing-field",
        "wrong-type",
        "wrong-time",
        "wrong-distance",
        "wrong-unit",
    ],
)
def test_verify_day_raises_structured_mismatch_for_relevant_differences(
    mutate,
    expected_value,
    observed_value,
):
    blocks = _observed_blocks()
    mutate(blocks)
    client = _verification_client(blocks)

    with pytest.raises(VerificationMismatch) as exc:
        client.verify_day("2026-06-20", _expected_rows())

    assert expected_value in _nested_values(exc.value.expected)
    assert observed_value in _nested_values(exc.value.observed)


def test_verify_day_rejects_duplicate_exercise_blocks_and_preserves_sequence():
    blocks = _observed_blocks()
    blocks.insert(1, blocks[0].copy())
    client = _verification_client(blocks)

    with pytest.raises(VerificationMismatch) as exc:
        client.verify_day("2026-06-20", _expected_rows())

    assert [block["eid"] for block in exc.value.expected] == [157728, 157737, 157740]
    assert [block["eid"] for block in exc.value.observed] == [157728, 157728, 157737, 157740]


def test_verify_day_error_payload_contains_normalized_expected_and_observed_distance():
    blocks = _observed_blocks()
    blocks[2]["sets"][0]["dunit"] = "mi"
    client = _verification_client(blocks)

    with pytest.raises(VerificationMismatch) as exc:
        client.verify_day("2026-06-20", _expected_rows())

    assert exc.value.expected[2]["sets"][0]["d"] == 279_500_000
    assert exc.value.expected[2]["sets"][0]["dunit"] == "km"
    assert exc.value.observed[2]["sets"][0]["dunit"] == "mi"
    assert "expected=" in str(exc.value)
    assert "observed=" in str(exc.value)


def test_verify_day_treats_missing_day_as_empty_observed_payload():
    client = WeightxRepsClient(
        access_token="token-123",
        session=FakeSession({"data": {"jeditor": None}}),
    )

    with pytest.raises(VerificationMismatch) as exc:
        client.verify_day("2026-06-20", _expected_rows())

    assert exc.value.observed == []


def _nested_values(value):
    if isinstance(value, dict):
        return [item for child in value.values() for item in _nested_values(child)]
    if isinstance(value, list):
        return [item for child in value for item in _nested_values(child)]
    return [value]
