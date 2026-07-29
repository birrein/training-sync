"""Command-line interface for training-sync."""

import argparse
from collections.abc import Sequence
from dataclasses import asdict
from datetime import date as calendar_date
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import secrets
import sys
from urllib.parse import parse_qs, urlparse
import webbrowser

from training_sync.config import (
    load_intervals_api_key,
    load_weightxreps_user_id,
    weightxreps_exercise_mapping_path,
    weightxreps_token_path,
)
from training_sync.intervals.client import IntervalsClient, IntervalsError
from training_sync.garmin.auth import get_client
from training_sync.garmin.fetch import fetch_and_print_activities
from training_sync.garmin.import_strength import parse_workout, push_workout
from training_sync.garmin.weight import print_weight_tag
from training_sync.use_cases.sync_day import SyncDependencies, sync_day
from training_sync.use_cases.weightxreps_preview import preview_weightxreps_day_from_vault
from training_sync.use_cases.weightxreps_push import push_weightxreps_day
from training_sync.weightxreps.auth import (
    TokenSet,
    build_authorization_url,
    exchange_code_for_tokens,
    generate_pkce_pair,
    load_tokens,
    refresh_access_token,
    save_tokens,
)
from training_sync.weightxreps.client import WeightxRepsClient
from training_sync.weightxreps.exercise_mapping import add_alias_mapping, add_create_mapping, load_exercise_mappings
from training_sync.weightxreps.exercise_resolution import ExerciseResolutionRequired

DEFAULT_VAULT_ROOT = Path("/Users/birrein/Library/Mobile Documents/iCloud~md~obsidian/Documents/brn-vault")
WEIGHTXREPS_CLIENT_ID = "training-sync"
WEIGHTXREPS_REDIRECT_URI = "http://127.0.0.1:8765/callback"
WEIGHTXREPS_SCOPE = "jread,jwrite"

def main(argv: Sequence[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()
    args = parser.parse_args(argv)
    _dispatch(args, parser)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=_program_name(),
        description="Sync training data across Garmin, Obsidian, and Weight x Reps.",
    )
    _add_modern_subcommands(parser)
    return parser


def _add_modern_subcommands(parser: argparse.ArgumentParser) -> None:
    subparsers = parser.add_subparsers(dest="command")
    sync_parser = subparsers.add_parser("sync", help="Sync one date across Garmin, vault, and Weight x Reps")
    sync_parser.add_argument("date", type=_iso_date)
    sync_parser.add_argument("--yes", action="store_true", help="Replace existing daily and Weight x Reps content")

    garmin = subparsers.add_parser("garmin", help="Garmin Connect commands")
    garmin_subparsers = garmin.add_subparsers(dest="garmin_command")

    garmin_fetch = garmin_subparsers.add_parser("fetch", help="Fetch Garmin activities")
    garmin_fetch.add_argument("date")

    garmin_weight = garmin_subparsers.add_parser("weight", help="Print Garmin body-weight tag")
    garmin_weight.add_argument("date")

    garmin_import = garmin_subparsers.add_parser("import-strength", help="Import strength JSON to Garmin")
    garmin_import.add_argument("json_file")

    weightxreps = subparsers.add_parser("weightxreps", help="Weight x Reps commands")
    weightxreps_subparsers = weightxreps.add_subparsers(dest="weightxreps_command")

    weightxreps_subparsers.add_parser("auth", help="Authenticate Weight x Reps")

    weightxreps_preview = weightxreps_subparsers.add_parser("preview", help="Preview Weight x Reps rows")
    weightxreps_preview.add_argument("date")

    weightxreps_push = weightxreps_subparsers.add_parser("push", help="Push Weight x Reps rows")
    weightxreps_push.add_argument("date")
    weightxreps_push.add_argument("--yes", action="store_true", help="Replace existing Weight x Reps content")
    weightxreps_push.add_argument("--user-id", type=int, help="Weight x Reps user id for full exercise catalog lookup")

    weightxreps_exercises = weightxreps_subparsers.add_parser(
        "exercises",
        help="Manage Weight x Reps exercise mappings",
    )
    weightxreps_exercise_subparsers = weightxreps_exercises.add_subparsers(
        dest="weightxreps_exercise_command",
    )

    weightxreps_map = weightxreps_exercise_subparsers.add_parser(
        "map",
        help="Map an incoming exercise to an existing Weight x Reps exercise",
    )
    weightxreps_map.add_argument("--incoming", required=True)
    weightxreps_map.add_argument("--existing-name", required=True)
    weightxreps_map.add_argument("--existing-id", required=True, type=int)

    weightxreps_create = weightxreps_exercise_subparsers.add_parser(
        "create",
        help="Allow creating a new Weight x Reps exercise",
    )
    weightxreps_create.add_argument("--incoming", required=True)

    weightxreps_resolve = weightxreps_exercise_subparsers.add_parser(
        "resolve",
        help="Resolve exercise mappings for a vault date",
    )
    weightxreps_resolve.add_argument("date")

    intervals = subparsers.add_parser("intervals", help="Intervals.icu activity commands")
    intervals_subparsers = intervals.add_subparsers(dest="intervals_command")
    intervals_list = intervals_subparsers.add_parser("list", help="List a bounded, read-only activity inventory")
    intervals_list.add_argument("oldest", type=_iso_date)
    intervals_list.add_argument("newest", type=_iso_date)
    intervals_show = intervals_subparsers.add_parser("show", help="Read one exact activity")
    intervals_show.add_argument("activity_id")
    intervals_upload = intervals_subparsers.add_parser("upload", help="Preview or upload one source artifact")
    intervals_upload.add_argument("artifact")
    intervals_upload.add_argument("--external-id", required=True)
    intervals_upload.add_argument("--yes", action="store_true", help="Authorize exactly this upload")
    intervals_update = intervals_subparsers.add_parser("update", help="Preview or update supported fields")
    intervals_update.add_argument("activity_id")
    intervals_update.add_argument("--name", required=True)
    intervals_update.add_argument("--yes", action="store_true")
    intervals_delete = intervals_subparsers.add_parser("delete", help="Preview or delete an exact activity")
    intervals_delete.add_argument("activity_id")
    intervals_delete.add_argument("--yes", action="store_true")

    reconcile = subparsers.add_parser("reconcile", help="Preview a scoped activity lifecycle plan")
    reconcile.add_argument("--target", action="append", choices=("vault", "weightxreps", "intervals"))
    reconcile.add_argument("--all", action="store_true", help="Select every configured compatible target explicitly")


def _dispatch(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if getattr(args, "command", None) == "sync":
        sync_day_cli(args.date, yes=args.yes)
        return

    if getattr(args, "command", None) == "intervals":
        intervals_cli(args)
        return

    if getattr(args, "command", None) == "reconcile":
        if args.all == bool(args.target):
            parser.error("select repeatable --target values or --all, but not both")
        print(json.dumps({"scope": "all" if args.all else args.target, "status": "preview", "operations": []}))
        return

    if getattr(args, "command", None) == "garmin" and args.garmin_command == "fetch":
        client = get_client()
        fetch_and_print_activities(client, args.date)
        return

    if getattr(args, "command", None) == "garmin" and args.garmin_command == "weight":
        client = get_client()
        print_weight_tag(client, args.date)
        return

    if getattr(args, "command", None) == "garmin" and args.garmin_command == "import-strength":
        client = get_client()
        _push_json_argument(client, args.json_file)
        return

    if getattr(args, "command", None) == "weightxreps" and args.weightxreps_command == "preview":
        preview_weightxreps_day(args.date)
        return

    if getattr(args, "command", None) == "weightxreps" and args.weightxreps_command == "auth":
        auth_weightxreps_cli()
        return

    if getattr(args, "command", None) == "weightxreps" and args.weightxreps_command == "push":
        push_weightxreps_day_cli(args.date, yes=args.yes, user_id=args.user_id)
        return

    if (
        getattr(args, "command", None) == "weightxreps"
        and args.weightxreps_command == "exercises"
        and args.weightxreps_exercise_command == "map"
    ):
        add_alias_mapping(
            weightxreps_exercise_mapping_path(),
            incoming_name=args.incoming,
            weightxreps_name=args.existing_name,
            weightxreps_id=args.existing_id,
        )
        print("mapped")
        return

    if (
        getattr(args, "command", None) == "weightxreps"
        and args.weightxreps_command == "exercises"
        and args.weightxreps_exercise_command == "create"
    ):
        add_create_mapping(
            weightxreps_exercise_mapping_path(),
            incoming_name=args.incoming,
        )
        print("created")
        return

    if (
        getattr(args, "command", None) == "weightxreps"
        and args.weightxreps_command == "exercises"
        and args.weightxreps_exercise_command == "resolve"
    ):
        preview_weightxreps_day(args.date)
        return

    parser.print_help()


def build_intervals_client() -> IntervalsClient:
    key = load_intervals_api_key()
    if not key:
        raise RuntimeError("Intervals API key not found; set INTERVALS_API_KEY or ~/.config/training-sync/intervals-api-key")
    return IntervalsClient("0", key)


def intervals_cli(args: argparse.Namespace) -> None:
    """Provider-local commands are preview-first and never touch other adapters."""
    try:
        client = build_intervals_client()
        if args.intervals_command == "list":
            print(json.dumps([asdict(item) for item in client.list_activities(args.oldest, args.newest)], indent=2))
        elif args.intervals_command == "show":
            print(json.dumps(asdict(client.get_activity(args.activity_id)), indent=2))
        elif args.intervals_command == "upload":
            payload = {"external_id": args.external_id, "artifact": (args.artifact, open(args.artifact, "rb"))}
            _intervals_mutation(client, "upload", None, payload, yes=args.yes)
        elif args.intervals_command == "update":
            _intervals_mutation(client, "update", args.activity_id, {"name": args.name}, yes=args.yes)
        elif args.intervals_command == "delete":
            activity = client.get_activity(args.activity_id)
            _intervals_mutation(client, "delete", args.activity_id, {"deleted": True, "consequence": client.destructive_consequence(activity)}, yes=args.yes)
        else:
            raise ValueError("Intervals command is required")
    except (IntervalsError, ValueError, RuntimeError) as exc:
        # Client errors intentionally do not include API-key material.
        raise SystemExit(str(exc)) from exc


def _intervals_mutation(client: IntervalsClient, operation: str, remote_id: str | None, payload: dict, *, yes: bool) -> None:
    preview = {"provider": "intervals", "operation": operation, "remote_id": remote_id,
               "payload": {key: value for key, value in payload.items() if key != "artifact"},
               "status": "apply" if yes else "preview"}
    print(json.dumps(preview, default=str))
    if not yes:
        return
    result = getattr(client, operation)(remote_id, payload)
    verified_id = str(result) if operation == "upload" else remote_id
    if not client.verify(verified_id, payload):
        raise SystemExit("Intervals read-back verification failed")
    print(json.dumps({"provider": "intervals", "remote_id": verified_id, "state": "verified"}))


def _iso_date(value: str) -> str:
    try:
        calendar_date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid ISO date: {value}") from exc
    return value


def _program_name() -> str:
    return os.path.basename(sys.argv[0]) or "training-sync"


def _push_json_argument(client, json_arg: str) -> None:
    try:
        if os.path.isfile(json_arg):
            with open(json_arg, "r", encoding="utf-8") as handle:
                workout_data = parse_workout(handle.read())
        else:
            workout_data = parse_workout(json_arg)
    except ValueError as exc:
        sys.exit(f"Data error: {exc}")

    push_workout(client, workout_data)


def preview_weightxreps_day(date: str) -> None:
    token_path = weightxreps_token_path()
    tokens = load_tokens(token_path)
    if tokens is None:
        sys.exit("Weight x Reps token not found. Run training-sync weightxreps auth first.")

    client = build_weightxreps_client(tokens, token_path)
    try:
        rows = preview_weightxreps_day_from_vault(
            DEFAULT_VAULT_ROOT,
            date,
            exercise_ids=client.exercise_ids(date),
            exercise_mappings=load_exercise_mappings(weightxreps_exercise_mapping_path()),
        )
    except ExerciseResolutionRequired as exc:
        _exit_with_resolution_payload(exc)
    print(json.dumps(rows, ensure_ascii=False, indent=2))


def sync_day_cli(date: str, yes: bool) -> None:
    token_path = weightxreps_token_path()
    tokens = load_tokens(token_path)
    if tokens is None:
        sys.exit("Weight x Reps token not found. Run training-sync weightxreps auth first.")

    try:
        user_id = load_weightxreps_user_id()
    except ValueError as exc:
        sys.exit(str(exc))

    deps = SyncDependencies(
        garmin=get_client(),
        weightxreps=build_weightxreps_client(tokens, token_path),
        vault_root=DEFAULT_VAULT_ROOT,
        mappings=load_exercise_mappings(weightxreps_exercise_mapping_path()),
        user_id=user_id,
    )
    try:
        result = sync_day(date, yes=yes, deps=deps)
    except ExerciseResolutionRequired as exc:
        _exit_with_resolution_payload(exc)
    print(json.dumps(asdict(result), default=str))


def push_weightxreps_day_cli(date: str, yes: bool, user_id: int | None = None) -> None:
    token_path = weightxreps_token_path()
    tokens = load_tokens(token_path)
    if tokens is None:
        sys.exit("Weight x Reps token not found. Run training-sync weightxreps auth first.")

    if user_id is None:
        try:
            user_id = load_weightxreps_user_id()
        except ValueError as exc:
            sys.exit(str(exc))

    client = build_weightxreps_client(tokens, token_path)
    try:
        result = push_weightxreps_day(
            DEFAULT_VAULT_ROOT,
            date,
            client,
            exercise_ids={},
            yes=yes,
            exercise_mappings=load_exercise_mappings(weightxreps_exercise_mapping_path()),
            user_id=user_id,
        )
    except ExerciseResolutionRequired as exc:
        _exit_with_resolution_payload(exc)
    print(result)


def _exit_with_resolution_payload(exc: ExerciseResolutionRequired) -> None:
    print(json.dumps(exc.payload(), ensure_ascii=False, indent=2))
    raise SystemExit(2) from exc


def build_weightxreps_client(tokens: TokenSet, token_path: Path) -> WeightxRepsClient:
    current_tokens = tokens

    def refresh_token() -> str:
        nonlocal current_tokens
        if not current_tokens.refresh_token:
            raise RuntimeError("Weight x Reps refresh token not found. Run training-sync weightxreps auth first.")

        current_tokens = refresh_access_token(
            client_id=WEIGHTXREPS_CLIENT_ID,
            refresh_token=current_tokens.refresh_token,
        )
        save_tokens(token_path, current_tokens)
        return current_tokens.access_token

    return WeightxRepsClient(tokens.access_token, token_refresher=refresh_token)


def auth_weightxreps_cli() -> None:
    pkce = generate_pkce_pair()
    state = secrets.token_urlsafe(24)
    auth_url = build_authorization_url(
        client_id=WEIGHTXREPS_CLIENT_ID,
        redirect_uri=WEIGHTXREPS_REDIRECT_URI,
        scope=WEIGHTXREPS_SCOPE,
        state=state,
        code_challenge=pkce.code_challenge,
    )
    print(f"Opening Weight x Reps authorization URL: {auth_url}")
    webbrowser.open(auth_url)
    code = _wait_for_weightxreps_callback(WEIGHTXREPS_REDIRECT_URI, expected_state=state)
    tokens = exchange_code_for_tokens(
        client_id=WEIGHTXREPS_CLIENT_ID,
        redirect_uri=WEIGHTXREPS_REDIRECT_URI,
        code=code,
        code_verifier=pkce.code_verifier,
    )
    save_tokens(weightxreps_token_path(), tokens)
    print(f"Weight x Reps token saved to {weightxreps_token_path()}")


def _wait_for_weightxreps_callback(redirect_uri: str, expected_state: str) -> str:
    parsed = urlparse(redirect_uri)
    result: dict[str, str] = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            query = parse_qs(urlparse(self.path).query)
            if query.get("state", [""])[0] != expected_state:
                self.send_error(400, "Invalid OAuth state")
                return
            if "error" in query:
                result["error"] = query["error"][0]
                self.send_error(400, result["error"])
                return
            result["code"] = query.get("code", [""])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Weight x Reps authorization complete. You can close this tab.")

        def log_message(self, format: str, *args) -> None:
            return

    server = HTTPServer((parsed.hostname or "127.0.0.1", parsed.port or 80), CallbackHandler)
    print("Waiting for Weight x Reps authorization callback...")
    server.handle_request()
    server.server_close()

    if result.get("error"):
        raise RuntimeError(result["error"])
    if not result.get("code"):
        raise RuntimeError("Weight x Reps authorization code was not received")
    return result["code"]
