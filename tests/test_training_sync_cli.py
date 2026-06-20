import sys

from garmin_sync import cli as legacy_cli
from training_sync import cli


def test_training_sync_garmin_fetch_dispatches_to_existing_fetch(monkeypatch):
    calls = []

    monkeypatch.setattr(sys, "argv", ["training-sync", "garmin", "fetch", "2026-06-19"])
    monkeypatch.setattr(cli, "get_client", lambda: "client")
    monkeypatch.setattr(
        cli,
        "fetch_and_print_activities",
        lambda client, date: calls.append(("fetch", client, date)),
    )

    cli.main()

    assert calls == [("fetch", "client", "2026-06-19")]


def test_training_sync_weight_command_dispatches_to_existing_weight(monkeypatch):
    calls = []

    monkeypatch.setattr(sys, "argv", ["training-sync", "garmin", "weight", "2026-06-19"])
    monkeypatch.setattr(cli, "get_client", lambda: "client")
    monkeypatch.setattr(
        cli,
        "print_weight_tag",
        lambda client, date: calls.append(("weight", client, date)),
    )

    cli.main()

    assert calls == [("weight", "client", "2026-06-19")]


def test_training_sync_legacy_positional_json_dispatches_to_push(monkeypatch):
    calls = []
    json_string = '{"date": "2026-06-19", "title": "Strength", "exercises": []}'
    workout = {"parsed": True}

    monkeypatch.setattr(sys, "argv", ["training-sync", json_string])
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


def test_training_sync_garmin_import_strength_reads_file_and_pushes(monkeypatch, tmp_path):
    calls = []
    json_file = tmp_path / "workout.json"
    json_string = '{"date": "2026-06-19", "title": "Strength", "exercises": []}'
    json_file.write_text(json_string, encoding="utf-8")
    workout = {"parsed": True}

    monkeypatch.setattr(sys, "argv", ["training-sync", "garmin", "import-strength", str(json_file)])
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


def test_training_sync_garmin_import_strength_reports_data_errors(monkeypatch, tmp_path):
    json_file = tmp_path / "workout.json"
    json_file.write_text('{"bad": true}', encoding="utf-8")

    def raise_value_error(raw):
        raise ValueError("missing exercises")

    monkeypatch.setattr(sys, "argv", ["training-sync", "garmin", "import-strength", str(json_file)])
    monkeypatch.setattr(cli, "get_client", lambda: "client")
    monkeypatch.setattr(cli, "parse_workout", raise_value_error)

    try:
        cli.main()
    except SystemExit as exc:
        assert str(exc) == "Data error: missing exercises"
    else:
        raise AssertionError("Expected SystemExit")


def test_legacy_garmin_sync_cli_still_uses_training_sync_main(monkeypatch):
    calls = []
    original_training_main = cli.main

    def spy_training_main():
        calls.append(("training-main",))
        original_training_main()

    monkeypatch.setattr(sys, "argv", ["garmin-sync", "--weight", "2026-06-19"])
    monkeypatch.setattr(legacy_cli, "get_client", lambda: "client")
    monkeypatch.setattr(
        legacy_cli,
        "print_weight_tag",
        lambda client, date: calls.append(("legacy-weight", client, date)),
    )
    monkeypatch.setattr(cli, "main", spy_training_main)

    legacy_cli.main()

    assert calls == [
        ("training-main",),
        ("legacy-weight", "client", "2026-06-19"),
    ]


def test_training_sync_weightxreps_preview_dispatches(monkeypatch):
    calls = []

    monkeypatch.setattr(sys, "argv", ["training-sync", "weightxreps", "preview", "2026-06-19"])
    monkeypatch.setattr(
        cli,
        "preview_weightxreps_day",
        lambda date: calls.append(("preview", date)),
    )

    cli.main()

    assert calls == [("preview", "2026-06-19")]


def test_training_sync_weightxreps_push_dispatches(monkeypatch):
    calls = []

    monkeypatch.setattr(sys, "argv", ["training-sync", "weightxreps", "push", "2026-06-19", "--yes"])
    monkeypatch.setattr(
        cli,
        "push_weightxreps_day_cli",
        lambda date, yes: calls.append(("push", date, yes)),
    )

    cli.main()

    assert calls == [("push", "2026-06-19", True)]
