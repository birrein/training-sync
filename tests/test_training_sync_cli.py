import io
import json
import sys

import pytest

from training_sync import cli
from training_sync.weightxreps.auth import TokenSet
from training_sync.weightxreps.exercise_resolution import (
    ExerciseResolutionRequired,
    UnresolvedExercise,
)


def test_training_sync_version_uses_installed_distribution_metadata(monkeypatch, capsys):
    monkeypatch.setattr(cli, "distribution_version", lambda name: "9.8.7")
    monkeypatch.setattr(cli, "_program_name", lambda: "training-sync")

    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])

    assert exc.value.code == 0
    assert capsys.readouterr().out == "training-sync 9.8.7\n"


def test_training_sync_sync_dispatches_yes(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "sync_day_cli", lambda date, yes: calls.append((date, yes)), raising=False)

    cli.main(["sync", "2026-07-03", "--yes"])

    assert calls == [("2026-07-03", True)]


def test_intervals_list_and_show_are_read_only(monkeypatch, capsys):
    calls = []
    class Client:
        def list_activities(self, oldest, newest): calls.append(("list", oldest, newest)); return []
        def get_activity(self, activity_id): calls.append(("show", activity_id)); return type("A", (), {"id": "1"})()
    monkeypatch.setattr(cli, "build_intervals_client", lambda: Client())
    cli.main(["intervals", "list", "2026-07-01", "2026-07-02"])
    assert calls == [("list", "2026-07-01", "2026-07-02")]
    assert '"status"' not in capsys.readouterr().out


def test_intervals_update_is_preview_by_default_and_apply_is_verified(monkeypatch, capsys):
    calls = []
    class Client:
        def update(self, remote_id, payload): calls.append(("update", remote_id, payload))
        def verify(self, remote_id, payload): calls.append(("verify", remote_id, payload)); return True
    monkeypatch.setattr(cli, "build_intervals_client", lambda: Client())
    cli.main(["intervals", "update", "42", "--name", "Fixed"])
    assert calls == []
    assert '"status": "preview"' in capsys.readouterr().out
    cli.main(["intervals", "update", "42", "--name", "Fixed", "--yes"])
    assert [call[0] for call in calls] == ["update", "verify"]


def test_reconcile_requires_exact_targets_or_explicit_all(capsys):
    cli.main(["reconcile", "--target", "intervals", "--target", "vault"])
    assert '"status": "preview"' in capsys.readouterr().out
    with pytest.raises(SystemExit):
        cli.main(["reconcile"])


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


@pytest.mark.parametrize(
    "legacy_argv",
    [
        ["--fetch", "2026-06-19"],
        ["--weight", "2026-06-19"],
        ['{"date": "2026-06-19", "title": "Strength", "exercises": []}'],
    ],
)
def test_training_sync_rejects_legacy_arguments_before_constructing_clients(
    monkeypatch,
    legacy_argv,
):
    monkeypatch.setattr(cli, "get_client", lambda: pytest.fail("client must not be constructed"))

    with pytest.raises(SystemExit) as exc:
        cli.main(legacy_argv)

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
    monkeypatch.setattr(cli, "vault_root", lambda: tmp_path / "vault")
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

    monkeypatch.setattr(cli, "vault_root", lambda: tmp_path / "vault")
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
    monkeypatch.setattr(cli, "vault_root", lambda: tmp_path / "vault")
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

    monkeypatch.setattr(cli, "vault_root", lambda: tmp_path / "vault")
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
    monkeypatch.setattr(cli, "vault_root", lambda: tmp_path / "vault")
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

    monkeypatch.setattr(cli, "vault_root", lambda: tmp_path / "vault")
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
                tmp_path / "vault",
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


def test_push_weightxreps_day_cli_prints_direct_weightxreps_url(monkeypatch, tmp_path, capsys):
    class Client:
        def journal_url(self, date):
            return f"https://weightxreps.net/journal/birrein/{date}"

    monkeypatch.setattr(cli, "vault_root", lambda: tmp_path / "vault")
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
    monkeypatch.setattr(cli, "build_weightxreps_client", lambda tokens, token_path: Client())
    monkeypatch.setattr(cli, "load_exercise_mappings", lambda path: [])
    monkeypatch.setattr(cli, "push_weightxreps_day", lambda *args, **kwargs: "saved")

    cli.push_weightxreps_day_cli("2026-06-19", yes=True, user_id=12345)

    output = capsys.readouterr().out
    assert '"weightxreps_url": "https://weightxreps.net/journal/birrein/2026-06-19"' in output


def test_push_weightxreps_day_cli_uses_env_user_id_fallback(monkeypatch, tmp_path):
    calls = []

    monkeypatch.setenv("WEIGHTXREPS_USER_ID", "67890")
    monkeypatch.setattr(cli, "vault_root", lambda: tmp_path / "vault")
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


def test_vault_backed_cli_requires_vault_configuration_before_loading_tokens(monkeypatch):
    monkeypatch.setattr(
        cli,
        "vault_root",
        lambda: (_ for _ in ()).throw(
            ValueError(
                "TRAINING_SYNC_VAULT_ROOT is not set. "
                "Set it to the absolute path of the local Obsidian vault before running this command."
            )
        ),
    )
    monkeypatch.setattr(cli, "load_tokens", lambda path: pytest.fail("tokens must not be loaded"))

    with pytest.raises(SystemExit, match="TRAINING_SYNC_VAULT_ROOT"):
        cli.preview_weightxreps_day("2026-06-19")


def test_training_sync_top_level_help_shows_command_groups(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["training-sync", "--help"])

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 0
    output = capsys.readouterr().out
    assert "garmin" in output
    assert "weightxreps" in output
    assert "sync" in output


def planned_json(name="CLI Plan"):
    return {
        "schema_version": 1,
        "key": "cli-plan",
        "name": name,
        "sport": "strength_training",
        "exercises": [
            {
                "name": "Squat",
                "sets": [{"reps": 5, "load": {"kind": "bodyweight"}}],
                "rest_between_sets": None,
                "rest_after_exercise": {"until": "time", "seconds": 30},
            }
        ],
    }


def test_planned_workout_preview_is_offline_and_does_not_need_vault_or_garmin(
    monkeypatch, tmp_path, capsys
):
    json_file = tmp_path / "plan.json"
    json_file.write_text(json.dumps(planned_json()), encoding="utf-8")
    monkeypatch.setattr(cli, "get_client", lambda: pytest.fail("preview must not authenticate"))

    cli.main(["garmin", "workout", "preview", str(json_file)])

    output = capsys.readouterr().out
    assert "CLI Plan" in output
    assert "bodyweight" in output


def test_planned_workout_preview_has_file_and_stdin_parity(monkeypatch, tmp_path, capsys):
    json_file = tmp_path / "plan.json"
    raw = json.dumps(planned_json())
    json_file.write_text(raw, encoding="utf-8")

    cli.main(["garmin", "workout", "preview", str(json_file)])
    from_file = capsys.readouterr().out
    monkeypatch.setattr(cli.sys, "stdin", io.StringIO(raw))
    cli.main(["garmin", "workout", "preview", "-"])
    from_stdin = capsys.readouterr().out

    assert from_file == from_stdin


def test_compact_and_explicit_strength_json_have_identical_file_stdin_preview(
    monkeypatch, tmp_path, capsys
):
    compact = planned_json()
    compact["key"] = "compact-cli-plan"
    compact["exercises"][0]["sets"] = [
        {"reps": 5, "load": {"kind": "bodyweight"}, "repeat": 2}
    ]
    compact["exercises"][0]["rest_between_sets"] = {
        "until": "time",
        "seconds": 30,
    }
    explicit = planned_json()
    explicit["key"] = "compact-cli-plan"
    explicit["exercises"][0]["sets"] = [
        {"reps": 5, "load": {"kind": "bodyweight"}},
        {"reps": 5, "load": {"kind": "bodyweight"}},
    ]
    explicit["exercises"][0]["rest_between_sets"] = {
        "until": "time",
        "seconds": 30,
    }
    compact_file = tmp_path / "compact.json"
    compact_file.write_text(json.dumps(compact), encoding="utf-8")

    cli.main(["garmin", "workout", "preview", str(compact_file)])
    compact_preview = capsys.readouterr().out
    monkeypatch.setattr(cli.sys, "stdin", io.StringIO(json.dumps(explicit)))
    cli.main(["garmin", "workout", "preview", "-"])
    explicit_preview = capsys.readouterr().out

    assert compact_preview == explicit_preview


def test_invalid_repeat_is_rejected_before_authentication(monkeypatch, tmp_path, capsys):
    invalid = planned_json()
    invalid["exercises"][0]["sets"][0]["repeat"] = True
    json_file = tmp_path / "invalid.json"
    json_file.write_text(json.dumps(invalid), encoding="utf-8")
    monkeypatch.setattr(cli, "get_client", lambda: pytest.fail("must not authenticate"))

    with pytest.raises(SystemExit) as exc:
        cli.main(["garmin", "workout", "create", str(json_file), "--yes"])

    assert exc.value.code == 2
    assert "repeat" in capsys.readouterr().err


def test_authorized_cli_create_submits_grouped_payload_to_fake_client(
    monkeypatch, tmp_path, capsys
):
    payload = planned_json()
    payload["exercises"][0]["sets"] = [
        {"reps": 5, "load": {"kind": "bodyweight"}, "repeat": 2}
    ]
    payload["exercises"][0]["rest_between_sets"] = {
        "until": "time",
        "seconds": 30,
    }
    json_file = tmp_path / "grouped.json"
    json_file.write_text(json.dumps(payload), encoding="utf-8")

    class FakeClient:
        def __init__(self):
            self.payload = None
            self.workout_id = 41

        def upload_workout(self, payload):
            self.payload = json.loads(json.dumps(payload))
            return {"workoutId": self.workout_id}

        def get_workout_by_id(self, workout_id):
            result = json.loads(json.dumps(self.payload))
            result["workoutId"] = workout_id
            return result

    client = FakeClient()
    monkeypatch.setattr(cli, "get_client", lambda: client)
    from training_sync.use_cases.publish_workout import publish_workout as publish_impl

    monkeypatch.setattr(
        cli,
        "publish_workout",
        lambda remote, plan, **kwargs: publish_impl(
            remote, plan, journal_path=None, **kwargs
        ),
    )

    cli.main(["garmin", "workout", "create", str(json_file), "--yes"])

    assert capsys.readouterr().out
    assert client.payload["workoutSegments"][0]["workoutSteps"][0]["type"] == "RepeatGroupDTO"


def test_planned_workout_create_only_authenticates_with_yes(monkeypatch, tmp_path, capsys):
    json_file = tmp_path / "plan.json"
    json_file.write_text(json.dumps(planned_json()), encoding="utf-8")
    calls = []

    class Client:
        pass

    monkeypatch.setattr(cli, "get_client", lambda: calls.append("auth") or Client())
    monkeypatch.setattr(
        cli,
        "publish_workout",
        lambda client, plan, **kwargs: calls.append((client, plan.name, kwargs))
        or type("Result", (), {"to_dict": lambda self: {"state": "verified"}})(),
    )

    cli.main(["garmin", "workout", "create", str(json_file)])
    assert calls == []
    assert "CLI Plan" in capsys.readouterr().out

    cli.main(["garmin", "workout", "create", str(json_file), "--date", "2026-09-13", "--yes"])
    assert calls[0] == "auth"
    assert calls[1][2] == {"authorized": True, "schedule_date": "2026-09-13"}
    assert '"state": "verified"' in capsys.readouterr().out


def test_planned_workout_cli_wires_crud_and_calendar_commands(monkeypatch, tmp_path, capsys):
    json_file = tmp_path / "plan.json"
    json_file.write_text(json.dumps(planned_json()), encoding="utf-8")
    calls = []

    monkeypatch.setattr(cli, "get_client", lambda: "client")
    monkeypatch.setattr(cli, "read_workout", lambda client, workout_id: {"workoutId": workout_id})
    monkeypatch.setattr(cli, "list_workouts", lambda client, **kwargs: type("I", (), {"to_dict": lambda self: {"items": []}})())
    monkeypatch.setattr(cli, "update_workout", lambda *args, **kwargs: calls.append("update") or type("R", (), {"to_dict": lambda self: {"state": "verified"}})())
    monkeypatch.setattr(cli, "duplicate_workout", lambda *args, **kwargs: calls.append("duplicate") or type("R", (), {"to_dict": lambda self: {"state": "verified"}})())
    monkeypatch.setattr(cli, "delete_workout", lambda *args, **kwargs: calls.append("delete") or type("R", (), {"to_dict": lambda self: {"state": "verified"}})())
    monkeypatch.setattr(cli, "list_calendar", lambda *args, **kwargs: type("I", (), {"to_dict": lambda self: {"items": []}})())
    monkeypatch.setattr(cli, "schedule_calendar_workout", lambda *args, **kwargs: calls.append("schedule") or type("R", (), {"to_dict": lambda self: {"state": "verified"}})())
    monkeypatch.setattr(cli, "move_calendar_workout", lambda *args, **kwargs: calls.append("move") or type("R", (), {"to_dict": lambda self: {"state": "verified"}})())
    monkeypatch.setattr(cli, "remove_calendar_workout", lambda *args, **kwargs: calls.append("remove") or type("R", (), {"to_dict": lambda self: {"state": "verified"}})())
    monkeypatch.setattr(cli, "replace_calendar_workout", lambda *args, **kwargs: calls.append("replace") or type("R", (), {"to_dict": lambda self: {"state": "verified"}})())

    cli.main(["garmin", "workout", "show", "7"])
    cli.main(["garmin", "workout", "list"])
    cli.main(["garmin", "workout", "update", "7", str(json_file), "--yes"])
    cli.main(["garmin", "workout", "duplicate", "7", "--name", "Copy", "--yes"])
    cli.main(["garmin", "workout", "delete", "7", "--yes"])
    cli.main(["garmin", "calendar", "list", "--from", "2026-09-13", "--to", "2026-09-13"])
    cli.main(["garmin", "calendar", "schedule", "7", "--date", "2026-09-13", "--yes"])
    cli.main(["garmin", "calendar", "move", "900", "--date", "2026-09-14", "--yes"])
    cli.main(["garmin", "calendar", "remove", "900", "--yes"])
    cli.main(["garmin", "calendar", "replace", "900", str(json_file), "--yes"])

    assert calls == ["update", "duplicate", "delete", "schedule", "move", "remove", "replace"]
    assert capsys.readouterr().out.count('"state": "verified"') == 7


def test_planned_workout_cli_reports_nonzero_failure_without_claiming_success(
    monkeypatch, tmp_path, capsys
):
    json_file = tmp_path / "plan.json"
    json_file.write_text(json.dumps(planned_json()), encoding="utf-8")
    monkeypatch.setattr(cli, "get_client", lambda: "client")
    monkeypatch.setattr(
        cli,
        "publish_workout",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("verification failed")),
    )

    with pytest.raises(SystemExit) as exc:
        cli.main(["garmin", "workout", "create", str(json_file), "--yes"])

    assert exc.value.code == 2
    assert "verification failed" in capsys.readouterr().err


def test_planned_workout_cli_returns_nonzero_for_partial_lifecycle_result(
    monkeypatch, tmp_path, capsys
):
    json_file = tmp_path / "plan.json"
    json_file.write_text(json.dumps(planned_json()), encoding="utf-8")
    monkeypatch.setattr(cli, "get_client", lambda: "client")
    monkeypatch.setattr(
        cli,
        "publish_workout",
        lambda *args, **kwargs: type(
            "Result",
            (),
            {
                "state": "partial",
                "to_dict": lambda self: {"state": "partial"},
            },
        )(),
    )

    with pytest.raises(SystemExit) as exc:
        cli.main(["garmin", "workout", "create", str(json_file), "--yes"])

    assert exc.value.code == 2
    assert '"state": "partial"' in capsys.readouterr().out
