from training_sync.use_cases.sync_day import sync_day


class FakeGarmin:
    def __init__(self):
        self.synced = []

    def sync_vault_day(self, date):
        self.synced.append(date)
        return "vault-updated"


class FakeWeightxReps:
    def __init__(self):
        self.pushed = []

    def push_day(self, date, yes):
        self.pushed.append((date, yes))
        return "replaced"


def test_sync_day_updates_vault_then_pushes_weightxreps():
    garmin = FakeGarmin()
    weightxreps = FakeWeightxReps()

    result = sync_day("2026-06-19", garmin=garmin, weightxreps=weightxreps)

    assert result == {
        "date": "2026-06-19",
        "vault": "vault-updated",
        "weightxreps": "replaced",
    }
    assert garmin.synced == ["2026-06-19"]
    assert weightxreps.pushed == [("2026-06-19", True)]
