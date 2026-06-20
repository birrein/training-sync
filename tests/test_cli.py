import sys

from garmin_sync import cli


def test_main_prints_weight_tag_for_weight_option(monkeypatch):
    calls = []

    monkeypatch.setattr(sys, "argv", ["garmin-sync", "--weight", "2026-06-19"])
    monkeypatch.setattr(cli, "get_client", lambda: "client")
    monkeypatch.setattr(
        cli,
        "print_weight_tag",
        lambda client, target_date: calls.append((client, target_date)),
    )

    cli.main()

    assert calls == [("client", "2026-06-19")]
