"""Command-line interface for training-sync."""

import argparse
from collections.abc import Callable, Sequence
from contextvars import ContextVar
from dataclasses import dataclass
import os
import sys

from garmin_sync.auth import get_client
from garmin_sync.commands.fetch import fetch_and_print_activities
from garmin_sync.commands.push import parse_workout, push_workout
from garmin_sync.commands.weight import print_weight_tag


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

    if argv and argv[0] == "garmin":
        _add_garmin_subcommands(parser)
    else:
        parser.add_argument("json_string", nargs="?", help=argparse.SUPPRESS)
        parser.add_argument("--fetch", type=str, help=argparse.SUPPRESS)
        parser.add_argument("--weight", type=str, help=argparse.SUPPRESS)

    return parser


def _add_garmin_subcommands(parser: argparse.ArgumentParser) -> None:
    subparsers = parser.add_subparsers(dest="command")
    garmin = subparsers.add_parser("garmin", help="Garmin Connect commands")
    garmin_subparsers = garmin.add_subparsers(dest="garmin_command")

    garmin_fetch = garmin_subparsers.add_parser("fetch", help="Fetch Garmin activities")
    garmin_fetch.add_argument("date")

    garmin_weight = garmin_subparsers.add_parser("weight", help="Print Garmin body-weight tag")
    garmin_weight.add_argument("date")

    garmin_import = garmin_subparsers.add_parser("import-strength", help="Import strength JSON to Garmin")
    garmin_import.add_argument("json_file")


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
