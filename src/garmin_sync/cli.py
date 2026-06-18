import os
import sys
import argparse
import logging
from garmin_sync.auth import get_client
from garmin_sync.commands.push import push_workout, parse_workout
from garmin_sync.commands.fetch import fetch_and_print_activities

def setup_logging():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="Sync Fitbod JSON to Garmin Connect, or fetch Garmin activities.")
    parser.add_argument("json_string", nargs="?", help="JSON string of the workout or path to JSON file")
    parser.add_argument("--fetch", help="Fetch activities for a given date (YYYY-MM-DD)", type=str)
    args = parser.parse_args()

    # The auth flow needs to run before any commands are executed.
    client = get_client()

    if args.fetch:
        fetch_and_print_activities(client, args.fetch)
    elif args.json_string:
        try:
            if os.path.isfile(args.json_string):
                with open(args.json_string, 'r') as f:
                    workout_data = parse_workout(f.read())
            else:
                workout_data = parse_workout(args.json_string)
        except ValueError as e:
            sys.exit(f"Data error: {e}")
            
        push_workout(client, workout_data)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
