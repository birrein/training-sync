import getpass
import json
import sys
import os
import argparse
from datetime import datetime
from garminconnect import Garmin

def parse_workout(json_str: str) -> dict:
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

# Load Garmin exercises dictionary generated from the CSV
def load_garmin_dict():
    dict_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'garmin_exercises.json')
    try:
        with open(dict_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Garmin API rejects sub-categories that are identical to the category
            for k, v in data.items():
                if v.get('name') == v.get('category'):
                    v['name'] = None
            return data
    except FileNotFoundError:
        print("Warning: garmin_exercises.json not found. Using empty dictionary.")
        return {}

GARMIN_DICT = load_garmin_dict()

# Custom aliases for when Fitbod names don't match Garmin display names exactly
FITBOD_CUSTOM_MAP = {
    "BENCH PRESS": {"category": "BENCH_PRESS", "name": "BARBELL_BENCH_PRESS"},
    "BARBELL BENCH PRESS": {"category": "BENCH_PRESS", "name": "BARBELL_BENCH_PRESS"},
    "DIP": {"category": "TRICEPS_EXTENSION", "name": "BODY_WEIGHT_DIP"},
    "INCLINE DUMBBELL CURL": {"category": "CURL", "name": "INCLINE_DUMBBELL_BICEPS_CURL"},
    "DUMBBELL FLY": {"category": "FLYE", "name": "DUMBBELL_FLYE"},
    "DUMBBELL BICEP CURL": {"category": "CURL", "name": "DUMBBELL_BICEPS_CURL"},
    "BICEP CURL": {"category": "CURL", "name": "DUMBBELL_BICEPS_CURL"},
    "TRICEP EXTENSION": {"category": "TRICEPS_EXTENSION", "name": "TRICEPS_PRESSDOWN"},
}

def run_sync(workout_data: dict):
    profile_dir = os.path.dirname(os.path.abspath(__file__))
    token_file = os.path.join(profile_dir, "garmin_token.json")
    
    client = Garmin()
    
    needs_login = True
    if os.path.exists(token_file):
        try:
            client.login(tokenstore=token_file)
            needs_login = False
        except Exception:
            print("Stored token expired or invalid.")
            needs_login = True
            
    if needs_login:
        import sys
        if not sys.stdin.isatty():
            sys.exit("Error: Garmin session expired. Please run this script manually in your terminal to log in.")
        email = input("Garmin Email: ")
        password = getpass.getpass("Garmin Password: ")
        client = Garmin(email, password)
        try:
            client.login(tokenstore=token_file)
        except Exception as e:
            raise RuntimeError(f"Login failed: {e}")
            
    print("Logged in successfully.")
    
    date = workout_data.get('date', datetime.today().strftime('%Y-%m-%d'))
    activities = client.get_activities_by_date(date, date)
        
    if not activities:
        raise RuntimeError(f"No activities found for date {date}")
        
    activity = activities[0]
    activity_id = activity.get('activityId')
    
    print(f"Found activity: {activity_id} - {activity.get('activityName')}")
    
    title = workout_data.get('title')
    if title:
        client.set_activity_name(activity_id, title)
        print(f"Updated title to: {title}")
        
    exercises = workout_data.get('exercises', [])
    if exercises:
        existing_sets = client.get_activity_exercise_sets(activity_id)
        print("--- DEBUG: Original Garmin Sets Structure ---")
        print(json.dumps(existing_sets, indent=2))
        print("-------------------------------------------")
        
        existing_array = existing_sets.get('exerciseSets', [])
        
        sets_payload = []
        msg_idx = 0
        
        for ex in exercises:
            fitbod_name = ex.get('name', 'UNKNOWN').upper()
            
            # Check Custom Map first, then standard Garmin dict
            if fitbod_name in FITBOD_CUSTOM_MAP:
                mapping = dict(FITBOD_CUSTOM_MAP[fitbod_name])
            elif fitbod_name in GARMIN_DICT:
                mapping = dict(GARMIN_DICT[fitbod_name])
            else:
                mapping = {"category": "UNKNOWN", "name": None}
                print(f"Warning: Exercise '{fitbod_name}' not found in dictionary. Sent as UNKNOWN.")
                
            # Garmin Web UI requires probability to be 100.0 to display the name!
            mapping["probability"] = 100.0
            
            for s in ex.get('sets', []):
                # Retrieve existing active and rest objects to preserve timestamps and duration
                active_base = existing_array[msg_idx] if msg_idx < len(existing_array) else {}
                
                sets_payload.append({
                    "exercises": [mapping],
                    "repetitionCount": s.get('reps', 0),
                    "weight": s.get('weight', 0) * 1000.0, # Garmin uses grams
                    "setType": "ACTIVE",
                    "duration": active_base.get("duration", 30.0),
                    "startTime": active_base.get("startTime"),
                    "wktStepIndex": None,
                    "messageIndex": None
                })
                msg_idx += 1
                
                rest_base = existing_array[msg_idx] if msg_idx < len(existing_array) else {}
                sets_payload.append({
                    "exercises": [],
                    "repetitionCount": None,
                    "weight": -1.0,  # Garmin UI uses -1.0 for REST weight
                    "setType": "REST",
                    "duration": rest_base.get("duration", 60.0),
                    "startTime": None,  # Garmin UI sets REST startTime to null
                    "wktStepIndex": None,
                    "messageIndex": None
                })
                msg_idx += 1
                
        existing_sets['exerciseSets'] = sets_payload
        
        try:
            client.set_activity_exercise_sets(activity_id, existing_sets)
            print("Successfully updated exercises.")
        except Exception as e:
            print(f"Failed to update exercises: {e}")

def fetch_activities(date_str: str):
    profile_dir = os.path.dirname(os.path.abspath(__file__))
    token_file = os.path.join(profile_dir, "garmin_token.json")
    
    client = Garmin()
    needs_login = True
    if os.path.exists(token_file):
        try:
            client.login(tokenstore=token_file)
            needs_login = False
        except Exception:
            needs_login = True
            
    if needs_login:
        import sys
        if not sys.stdin.isatty():
            sys.exit("Error: Garmin session expired. Please run this script manually in your terminal to log in.")
        email = input("Garmin Email: ")
        password = getpass.getpass("Garmin Password: ")
        client = Garmin(email, password)
        client.login(tokenstore=token_file)
        
    activities = client.get_activities_by_date(date_str, date_str)
    if not activities:
        print(f"No activities found for {date_str}")
        return
        
    for act in activities:
        name = act.get('activityName')
        dist_km = act.get('distance', 0) / 1000.0
        dur_s = act.get('duration', 0)
        
        hours, remainder = divmod(dur_s, 3600)
        minutes, seconds = divmod(remainder, 60)
        dur_str = f"{int(hours):02d}:{int(minutes):02d}:{seconds:04.1f}"
        
        if dist_km > 0:
            pace_s_per_km = dur_s / dist_km
            p_min, p_sec = divmod(pace_s_per_km, 60)
            pace_str = f"{int(p_min):02d}:{p_sec:04.1f}"
        else:
            pace_str = "00:00.0"
            
        hr = act.get('averageHR', 0)
        max_hr = act.get('maxHR', 0)
        load = act.get('activityTrainingLoad', 0)
        elev = act.get('elevationGain', 0)
        power = act.get('avgPower', 0)
        cadence = act.get('averageRunningCadenceInStepsPerMinute', 0)
        cals = act.get('calories', 0)
        
        print(f"## 🏃 Training\n- {name}")
        print("```text")
        print(f"{date_str}\n")
        
        # Determine tag based on activity type
        act_type = act.get('activityType', {}).get('typeKey', '')
        if 'run' in act_type:
            print("#Running")
        elif 'cycl' in act_type:
            print("#Cycling")
        else:
            print(f"#{act_type.capitalize()}")
            
        print(f"{dist_km:.2f}km")
        print(f"@ Duration: {dur_str}")
        if 'run' in act_type:
            print(f"@ Avg Pace: {pace_str}")
        print(f"@ Avg HR: {int(hr)}")
        print(f"@ Max HR: {int(max_hr)}")
        if load: print(f"@ Training Load: {int(load)}")
        if elev: print(f"@ Elev Gain: {int(elev)}")
        if power: print(f"@ Avg Power: {int(power)}")
        if cadence: print(f"@ Avg Cadence: {int(cadence)}")
        if cals: print(f"@ Calories: {int(cals)}")
        print("```\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync Fitbod JSON to Garmin Connect, or fetch Garmin activities.")
    parser.add_argument("json_string", nargs="?", help="JSON string of the workout or path to JSON file")
    parser.add_argument("--fetch", help="Fetch activities for a given date (YYYY-MM-DD)", type=str)
    args = parser.parse_args()

    if args.fetch:
        fetch_activities(args.fetch)
    elif args.json_string:
        try:
            if os.path.isfile(args.json_string):
                with open(args.json_string, 'r') as f:
                    workout_data = parse_workout(f.read())
            else:
                workout_data = parse_workout(args.json_string)
        except ValueError as e:
            print(e)
            exit(1)
            
        run_sync(workout_data)
    else:
        parser.print_help()
