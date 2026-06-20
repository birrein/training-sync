"""Backward-compatible garmin-sync CLI entrypoint."""

from training_sync import cli as training_cli

get_client = training_cli.get_client
fetch_and_print_activities = training_cli.fetch_and_print_activities
parse_workout = training_cli.parse_workout
print_weight_tag = training_cli.print_weight_tag
push_workout = training_cli.push_workout


def main() -> None:
    handlers = training_cli.CommandHandlers(
        get_client=get_client,
        fetch_and_print_activities=fetch_and_print_activities,
        parse_workout=parse_workout,
        print_weight_tag=print_weight_tag,
        push_workout=push_workout,
    )
    token = training_cli.set_command_handlers(handlers)
    try:
        training_cli.main()
    finally:
        training_cli.reset_command_handlers(token)

if __name__ == "__main__":
    main()
