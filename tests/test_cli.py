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


def test_main_pushes_legacy_positional_json(monkeypatch):
    calls = []
    json_string = '{"date": "2026-06-19", "title": "Strength", "exercises": []}'
    workout = {"parsed": True}

    monkeypatch.setattr(sys, "argv", ["garmin-sync", json_string])
    monkeypatch.setattr(cli, "get_client", lambda: "client")
    monkeypatch.setattr(cli, "parse_workout", lambda raw: calls.append(("parse", raw)) or workout)
    monkeypatch.setattr(
        cli,
        "push_workout",
        lambda client, data: calls.append(("push", client, data)),
    )

    cli.main()

    assert calls == [
        ("parse", json_string),
        ("push", "client", workout),
    ]
