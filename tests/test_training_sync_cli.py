import sys

import pytest

from garmin_sync import cli as legacy_cli
from training_sync import cli
from training_sync.weightxreps.auth import TokenSet
from training_sync.weightxreps.exercise_resolution import (
    ExerciseResolutionRequired,
    UnresolvedExercise,
)


def test_training_sync_sync_dispatches_yes(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "sync_day_cli", lambda date, yes: calls.append((date, yes)), raising=False)

    cli.main(["sync", "2026-07-03", "--yes"])

    assert calls == [("2026-07-03", True)]


def test_training_sync_sync_dispatches_without_confirmation(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "sync_day_cli", lambda date, yes: calls.append((date, yes)), raising=False)

    cli.main(["sync", "2026-07-03"])

    assert calls == [("2026-07-03", False)]


def test_training_sync_sync_rejects_invalid_date_before_client_construction(monkeypatch):
    monkeypatch.setattr(cli, "get_client", lambda: pytest.fail("client must not be constructed"))

    with pytest.raises(SystemExit) as exc:
        cli.main(["sync", "07-03-2026"])

    assert exc.value.code == 2


def test_sync_day_cli_prints_structured_exercise_resolution_error(monkeypatch, tmp_path, capsys):
    unresolved = UnresolvedExercise(
        incoming_exercise="Walking",
        normalized_name="walking",
        reason="no_local_mapping",
        candidates=[],
    )
    monkeypatch.setattr(
        cli,
        "load_tokens",
        lambda path: TokenSet(
            access_token="token",
            refresh_token="refresh",
            expires_in=3600,
            token_type="Bearer",
        ),
    )
    monkeypatch.setattr(cli, "weightxreps_token_path", lambda: tmp_path / "token.json")
    monkeypatch.setattr(cli, "build_weightxreps_client", lambda tokens, token_path: "client")
    monkeypatch.setattr(cli, "get_client", lambda: "garmin")
    monkeypatch.setattr(cli, "load_weightxreps_user_id", lambda: None)
    monkeypatch.setattr(cli, "load_exercise_mappings", lambda path: [])
    monkeypatch.setattr(
        cli,
        "sync_day",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            ExerciseResolutionRequired("2026-07-03", [unresolved])
        ),
    )

    with pytest.raises(SystemExit) as exc:
        cli.sync_day_cli("2026-07-03", yes=True)

    assert exc.value.code == 2
    assert '"status": "exercise_resolution_required"' in capsys.readouterr().out


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


def test_preview_weightxreps_day_uses_remote_exercise_ids(monkeypatch, tmp_path, capsys):
    calls = []
    tokens = TokenSet(
        access_token="token",
        refresh_token="refresh",
        expires_in=3600,
        token_type="Bearer",
    )

    class FakeWeightxRepsClient:
        def exercise_ids(self, date):
            calls.append(("exercise_ids", date))
            return {"Chin Up": 10}

    monkeypatch.setattr(cli, "DEFAULT_VAULT_ROOT", tmp_path / "vault")
    monkeypatch.setattr(cli, "weightxreps_token_path", lambda: tmp_path / "token.json")
    monkeypatch.setattr(cli, "weightxreps_exercise_mapping_path", lambda: tmp_path / "exercises.toml")
    monkeypatch.setattr(cli, "load_tokens", lambda path: tokens)
    monkeypatch.setattr(
        cli,
        "build_weightxreps_client",
        lambda loaded_tokens, token_path: calls.append(("client", loaded_tokens, token_path))
        or FakeWeightxRepsClient(),
    )
    monkeypatch.setattr(cli, "load_exercise_mappings", lambda path: ["mapping"])
    monkeypatch.setattr(
        cli,
        "preview_weightxreps_day_from_vault",
        lambda vault_root, date, exercise_ids, exercise_mappings: calls.append(
            ("preview", vault_root, date, exercise_ids, exercise_mappings)
        )
        or [{"eid": 10}],
    )

    cli.preview_weightxreps_day("2026-06-19")

    assert calls == [
        ("client", tokens, tmp_path / "token.json"),
        ("exercise_ids", "2026-06-19"),
        ("preview", tmp_path / "vault", "2026-06-19", {"Chin Up": 10}, ["mapping"]),
    ]
    assert capsys.readouterr().out == '[\n  {\n    "eid": 10\n  }\n]\n'


def test_preview_weightxreps_day_requires_auth_tokens(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "weightxreps_token_path", lambda: tmp_path / "token.json")
    monkeypatch.setattr(cli, "load_tokens", lambda path: None)

    with pytest.raises(SystemExit) as exc:
        cli.preview_weightxreps_day("2026-06-19")

    assert str(exc.value) == "Weight x Reps token not found. Run training-sync weightxreps auth first."


def test_training_sync_weightxreps_push_dispatches(monkeypatch):
    calls = []

    monkeypatch.setattr(sys, "argv", ["training-sync", "weightxreps", "push", "2026-06-19", "--yes"])
    monkeypatch.setattr(
        cli,
        "push_weightxreps_day_cli",
        lambda date, yes, user_id=None: calls.append(("push", date, yes, user_id)),
    )

    cli.main()

    assert calls == [("push", "2026-06-19", True, None)]


def test_training_sync_weightxreps_push_passes_user_id_option(monkeypatch):
    calls = []

    monkeypatch.setattr(
        sys,
        "argv",
        ["training-sync", "weightxreps", "push", "2026-06-19", "--yes", "--user-id", "12345"],
    )
    monkeypatch.setattr(
        cli,
        "push_weightxreps_day_cli",
        lambda date, yes, user_id=None: calls.append(("push", date, yes, user_id)),
    )

    cli.main()

    assert calls == [("push", "2026-06-19", True, 12345)]


def test_training_sync_weightxreps_auth_dispatches(monkeypatch):
    calls = []

    monkeypatch.setattr(sys, "argv", ["training-sync", "weightxreps", "auth"])
    monkeypatch.setattr(cli, "auth_weightxreps_cli", lambda: calls.append(("auth",)))

    cli.main()

    assert calls == [("auth",)]


def test_training_sync_weightxreps_exercises_map_dispatches(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(cli, "weightxreps_exercise_mapping_path", lambda: tmp_path / "map.toml")
    monkeypatch.setattr(
        cli,
        "add_alias_mapping",
        lambda path, incoming_name, weightxreps_name, weightxreps_id: calls.append(
            (path, incoming_name, weightxreps_name, weightxreps_id)
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "training-sync",
            "weightxreps",
            "exercises",
            "map",
            "--incoming",
            "Barbell Hip Thrust with Bench",
            "--existing-name",
            "Barbell Hip Thrust",
            "--existing-id",
            "157721",
        ],
    )

    cli.main()

    assert calls == [
        (
            tmp_path / "map.toml",
            "Barbell Hip Thrust with Bench",
            "Barbell Hip Thrust",
            157721,
        )
    ]


def test_training_sync_weightxreps_exercises_create_dispatches(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(cli, "weightxreps_exercise_mapping_path", lambda: tmp_path / "map.toml")
    monkeypatch.setattr(
        cli,
        "add_create_mapping",
        lambda path, incoming_name: calls.append((path, incoming_name)),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "training-sync",
            "weightxreps",
            "exercises",
            "create",
            "--incoming",
            "New Exercise Name",
        ],
    )

    cli.main()

    assert calls == [(tmp_path / "map.toml", "New Exercise Name")]


def test_training_sync_weightxreps_exercises_resolve_prints_resolution_json(monkeypatch, tmp_path, capsys):
    class FakeWeightxRepsClient:
        def exercise_ids(self, date):
            return {}

    monkeypatch.setattr(cli, "DEFAULT_VAULT_ROOT", tmp_path / "vault")
    monkeypatch.setattr(cli, "weightxreps_token_path", lambda: tmp_path / "token.json")
    monkeypatch.setattr(cli, "weightxreps_exercise_mapping_path", lambda: tmp_path / "map.toml")
    monkeypatch.setattr(
        cli,
        "load_tokens",
        lambda path: TokenSet(
            access_token="token",
            refresh_token="refresh",
            expires_in=3600,
            token_type="Bearer",
        ),
    )
    monkeypatch.setattr(
        cli,
        "build_weightxreps_client",
        lambda tokens, token_path: FakeWeightxRepsClient(),
    )
    monkeypatch.setattr(cli, "load_exercise_mappings", lambda path: [])
    monkeypatch.setattr(
        cli,
        "preview_weightxreps_day_from_vault",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            ExerciseResolutionRequired(
                "2026-06-20",
                [
                    UnresolvedExercise(
                        incoming_exercise="Hip Thrust",
                        normalized_name="hip thrust",
                        reason="no_local_mapping",
                        candidates=[],
                    )
                ],
            )
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["training-sync", "weightxreps", "exercises", "resolve", "2026-06-20"],
    )

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 2
    assert '"status": "exercise_resolution_required"' in capsys.readouterr().out


def test_weightxreps_client_refresher_saves_new_tokens(monkeypatch, tmp_path):
    saved = []
    initial_tokens = TokenSet(
        access_token="expired-token",
        refresh_token="refresh-token",
        expires_in=3600,
        token_type="Bearer",
    )
    refreshed_tokens = TokenSet(
        access_token="fresh-token",
        refresh_token="new-refresh-token",
        expires_in=3600,
        token_type="Bearer",
    )

    monkeypatch.setattr(
        cli,
        "refresh_access_token",
        lambda client_id, refresh_token: refreshed_tokens,
    )
    monkeypatch.setattr(cli, "save_tokens", lambda path, tokens: saved.append((path, tokens)))

    client = cli.build_weightxreps_client(initial_tokens, tmp_path / "token.json")
    refreshed_access_token = client.token_refresher()

    assert refreshed_access_token == "fresh-token"
    assert saved == [(tmp_path / "token.json", refreshed_tokens)]
    assert client.access_token == "expired-token"


def test_training_sync_weightxreps_push_prints_resolution_json(monkeypatch, tmp_path, capsys):
    unresolved = UnresolvedExercise(
        incoming_exercise="Hip Thrust",
        normalized_name="hip thrust",
        reason="no_local_mapping",
        candidates=[],
    )

    monkeypatch.setattr(
        cli,
        "load_tokens",
        lambda path: TokenSet(
            access_token="token",
            refresh_token="refresh",
            expires_in=3600,
            token_type="Bearer",
        ),
    )
    monkeypatch.setattr(cli, "weightxreps_token_path", lambda: tmp_path / "token.json")
    monkeypatch.setattr(cli, "weightxreps_exercise_mapping_path", lambda: tmp_path / "exercises.toml")
    monkeypatch.setattr(cli, "build_weightxreps_client", lambda tokens, token_path: "client")
    monkeypatch.setattr(cli, "load_exercise_mappings", lambda path: [])
    monkeypatch.setattr(
        cli,
        "push_weightxreps_day",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            ExerciseResolutionRequired("2026-06-19", [unresolved])
        ),
    )

    with pytest.raises(SystemExit) as exc:
        cli.push_weightxreps_day_cli("2026-06-19", yes=True)

    output = capsys.readouterr().out
    assert exc.value.code == 2
    assert '"status": "exercise_resolution_required"' in output
    assert '"incoming_exercise": "Hip Thrust"' in output


def test_push_weightxreps_day_cli_passes_explicit_user_id(monkeypatch, tmp_path):
    calls = []

    monkeypatch.setattr(
        cli,
        "load_tokens",
        lambda path: TokenSet(
            access_token="token",
            refresh_token="refresh",
            expires_in=3600,
            token_type="Bearer",
        ),
    )
    monkeypatch.setattr(cli, "weightxreps_token_path", lambda: tmp_path / "token.json")
    monkeypatch.setattr(cli, "weightxreps_exercise_mapping_path", lambda: tmp_path / "exercises.toml")
    monkeypatch.setattr(cli, "build_weightxreps_client", lambda tokens, token_path: "client")
    monkeypatch.setattr(cli, "load_exercise_mappings", lambda path: ["mapping"])
    monkeypatch.setattr(
        cli,
        "push_weightxreps_day",
        lambda *args, **kwargs: calls.append((args, kwargs)) or "saved",
    )

    cli.push_weightxreps_day_cli("2026-06-19", yes=True, user_id=12345)

    assert calls == [
        (
            (
                cli.DEFAULT_VAULT_ROOT,
                "2026-06-19",
                "client",
            ),
            {
                "exercise_ids": {},
                "yes": True,
                "exercise_mappings": ["mapping"],
                "user_id": 12345,
            },
        )
    ]


def test_push_weightxreps_day_cli_uses_env_user_id_fallback(monkeypatch, tmp_path):
    calls = []

    monkeypatch.setenv("WEIGHTXREPS_USER_ID", "67890")
    monkeypatch.setattr(
        cli,
        "load_tokens",
        lambda path: TokenSet(
            access_token="token",
            refresh_token="refresh",
            expires_in=3600,
            token_type="Bearer",
        ),
    )
    monkeypatch.setattr(cli, "weightxreps_token_path", lambda: tmp_path / "token.json")
    monkeypatch.setattr(cli, "weightxreps_exercise_mapping_path", lambda: tmp_path / "exercises.toml")
    monkeypatch.setattr(cli, "build_weightxreps_client", lambda tokens, token_path: "client")
    monkeypatch.setattr(cli, "load_exercise_mappings", lambda path: ["mapping"])
    monkeypatch.setattr(
        cli,
        "push_weightxreps_day",
        lambda *args, **kwargs: calls.append(kwargs) or "saved",
    )

    cli.push_weightxreps_day_cli("2026-06-19", yes=True)

    assert calls[0]["user_id"] == 67890


def test_training_sync_top_level_help_shows_command_groups(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["training-sync", "--help"])

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 0
    output = capsys.readouterr().out
    assert "garmin" in output
    assert "weightxreps" in output
    assert "sync" in output
