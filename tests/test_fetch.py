from training_sync.garmin.fetch import fetch_and_print_activities


class FakeGarminClient:
    def get_activities_by_date(self, startdate, enddate):
        assert (startdate, enddate) == ("2026-06-19", "2026-06-19")
        return [
            {
                "activityName": "Upper Body Day 2",
                "activityType": {"typeKey": "strength_training"},
                "distance": 0,
                "duration": 4280.331,
                "averageHR": 90,
                "maxHR": 138,
                "activityTrainingLoad": 4.7,
                "calories": 217,
            }
        ]

    def get_weigh_ins(self, startdate, enddate):
        assert (startdate, enddate) == ("2026-06-05", "2026-07-03")
        return {
            "dailyWeightSummaries": [
                {
                    "summaryDate": "2026-06-18",
                    "latestWeight": {
                        "calendarDate": "2026-06-18",
                        "weight": 71389.0,
                        "sourceType": "INDEX_SCALE",
                    },
                }
            ]
        }


def test_fetch_strength_activity_includes_nearest_body_weight(capsys):
    fetch_and_print_activities(FakeGarminClient(), "2026-06-19")

    output = capsys.readouterr().out

    assert "- Upper Body Day 2" in output
    assert "@ 71.4 bw" in output
    assert "@ Duration: 01:11:20.3" in output
