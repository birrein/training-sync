"""Command-line interface for training-sync."""

import argparse
from collections.abc import Callable, Sequence
from contextvars import ContextVar
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import secrets
import sys
from urllib.parse import parse_qs, urlparse
import webbrowser

from garmin_sync.auth import get_client
from garmin_sync.commands.fetch import fetch_and_print_activities
from garmin_sync.commands.push import parse_workout, push_workout
from garmin_sync.commands.weight import print_weight_tag
from training_sync.config import weightxreps_token_path
from training_sync.use_cases.weightxreps_preview import preview_weightxreps_day_from_vault
from training_sync.use_cases.weightxreps_push import push_weightxreps_day
from training_sync.weightxreps.auth import (
    build_authorization_url,
    exchange_code_for_tokens,
    generate_pkce_pair,
    load_tokens,
    save_tokens,
)
from training_sync.weightxreps.client import WeightxRepsClient

DEFAULT_VAULT_ROOT = Path("/Users/birrein/Library/Mobile Documents/iCloud~md~obsidian/Documents/brn-vault")
WEIGHTXREPS_CLIENT_ID = "training-sync"
WEIGHTXREPS_REDIRECT_URI = "http://127.0.0.1:8765/callback"
WEIGHTXREPS_SCOPE = "jread,jwrite"


@dataclass(frozen=True)
class CommandHandlers:
    get_client: Callable
    fetch_and_print_activities: Callable
    parse_workout: Callable
    print_weight_tag: Callable
    push_workout: Callable


_handler_context: ContextVar[CommandHandlers | None] = ContextVar("handler_context", default=None)


def main(argv: Sequence[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser(argv)
    args = parser.parse_args(argv)
    _dispatch(args, parser, _current_handlers())


def set_command_handlers(handlers: CommandHandlers):
    """Temporarily override command handlers for compatibility wrappers."""
    return _handler_context.set(handlers)


def reset_command_handlers(token) -> None:
    _handler_context.reset(token)


def _current_handlers() -> CommandHandlers:
    handlers = _handler_context.get()
    if handlers is not None:
        return handlers

    return CommandHandlers(
        get_client=get_client,
        fetch_and_print_activities=fetch_and_print_activities,
        parse_workout=parse_workout,
        print_weight_tag=print_weight_tag,
        push_workout=push_workout,
    )


def _build_parser(argv: Sequence[str]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=_program_name(),
        description="Sync training data across Garmin, Obsidian, and Weight x Reps.",
    )

    if argv and argv[0] in {"garmin", "weightxreps"}:
        _add_modern_subcommands(parser)
    else:
        parser.add_argument("json_string", nargs="?", help=argparse.SUPPRESS)
        parser.add_argument("--fetch", type=str, help=argparse.SUPPRESS)
        parser.add_argument("--weight", type=str, help=argparse.SUPPRESS)

    return parser


def _add_modern_subcommands(parser: argparse.ArgumentParser) -> None:
    subparsers = parser.add_subparsers(dest="command")
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


def _dispatch(args: argparse.Namespace, parser: argparse.ArgumentParser, handlers: CommandHandlers) -> None:
    if getattr(args, "fetch", None):
        client = handlers.get_client()
        handlers.fetch_and_print_activities(client, args.fetch)
        return

    if getattr(args, "weight", None):
        client = handlers.get_client()
        handlers.print_weight_tag(client, args.weight)
        return

    if getattr(args, "json_string", None):
        client = handlers.get_client()
        _push_json_argument(client, args.json_string, handlers)
        return

    if getattr(args, "command", None) == "garmin" and args.garmin_command == "fetch":
        client = handlers.get_client()
        handlers.fetch_and_print_activities(client, args.date)
        return

    if getattr(args, "command", None) == "garmin" and args.garmin_command == "weight":
        client = handlers.get_client()
        handlers.print_weight_tag(client, args.date)
        return

    if getattr(args, "command", None) == "garmin" and args.garmin_command == "import-strength":
        client = handlers.get_client()
        _push_json_argument(client, args.json_file, handlers)
        return

    if getattr(args, "command", None) == "weightxreps" and args.weightxreps_command == "preview":
        preview_weightxreps_day(args.date)
        return

    if getattr(args, "command", None) == "weightxreps" and args.weightxreps_command == "auth":
        auth_weightxreps_cli()
        return

    if getattr(args, "command", None) == "weightxreps" and args.weightxreps_command == "push":
        push_weightxreps_day_cli(args.date, yes=args.yes)
        return

    parser.print_help()


def _program_name() -> str:
    return os.path.basename(sys.argv[0]) or "training-sync"


def _push_json_argument(client, json_arg: str, handlers: CommandHandlers) -> None:
    try:
        if os.path.isfile(json_arg):
            with open(json_arg, "r", encoding="utf-8") as handle:
                workout_data = handlers.parse_workout(handle.read())
        else:
            workout_data = handlers.parse_workout(json_arg)
    except ValueError as exc:
        sys.exit(f"Data error: {exc}")

    handlers.push_workout(client, workout_data)


def preview_weightxreps_day(date: str) -> None:
    rows = preview_weightxreps_day_from_vault(
        DEFAULT_VAULT_ROOT,
        date,
        exercise_ids={},
    )
    print(json.dumps(rows, ensure_ascii=False, indent=2))


def push_weightxreps_day_cli(date: str, yes: bool) -> None:
    tokens = load_tokens(weightxreps_token_path())
    if tokens is None:
        sys.exit("Weight x Reps token not found. Run training-sync weightxreps auth first.")

    client = WeightxRepsClient(tokens.access_token)
    result = push_weightxreps_day(
        DEFAULT_VAULT_ROOT,
        date,
        client,
        exercise_ids={},
        yes=yes,
    )
    print(result)


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
