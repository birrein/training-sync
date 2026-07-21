from training_sync.garmin.weight import (
    WeightReading,
    find_nearest_weight,
    format_weight_tag,
)


class FakeGarminClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get_weigh_ins(self, startdate, enddate):
        self.calls.append((startdate, enddate))
        return self.response


def test_find_nearest_weight_returns_closest_reading_in_kg():
    client = FakeGarminClient(
        {
            "dailyWeightSummaries": [
                {
                    "summaryDate": "2026-06-14",
                    "latestWeight": {
                        "calendarDate": "2026-06-14",
                        "weight": 72000.0,
                        "sourceType": "INDEX_SCALE",
                    },
                },
                {
                    "summaryDate": "2026-06-18",
                    "latestWeight": {
                        "calendarDate": "2026-06-18",
                        "weight": 71389.0,
                        "sourceType": "INDEX_SCALE",
                    },
                },
            ]
        }
    )

    reading = find_nearest_weight(client, "2026-06-19", window_days=7)

    assert reading == WeightReading(
        calendar_date="2026-06-18",
        weight_kg=71.389,
        source_type="INDEX_SCALE",
        day_delta=-1,
    )
    assert client.calls == [("2026-06-12", "2026-06-26")]


def test_find_nearest_weight_ignores_empty_weight_records():
    client = FakeGarminClient(
        {
            "dailyWeightSummaries": [
                {
                    "summaryDate": "2026-06-18",
                    "latestWeight": {
                        "calendarDate": "2026-06-18",
                        "weight": None,
                    },
                }
            ],
            "previousDateWeight": {
                "calendarDate": None,
                "weight": None,
            },
        }
    )

    assert find_nearest_weight(client, "2026-06-19", window_days=7) is None


def test_format_weight_tag_rounds_to_one_decimal_for_weightxreps():
    reading = WeightReading(
        calendar_date="2026-06-18",
        weight_kg=71.389,
        source_type="INDEX_SCALE",
        day_delta=-1,
    )

    assert format_weight_tag(reading) == "@ 71.4 bw"
