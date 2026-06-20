"""End-to-end one-day sync use case."""


def sync_day(date: str, garmin, weightxreps) -> dict[str, str]:
    vault_result = garmin.sync_vault_day(date)
    weightxreps_result = weightxreps.push_day(date, yes=True)
    return {
        "date": date,
        "vault": vault_result,
        "weightxreps": weightxreps_result,
    }
