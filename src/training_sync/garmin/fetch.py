"""Module for fetching and formatting Garmin activities."""

from garminconnect import Garmin
from training_sync.garmin.weight import find_nearest_weight, format_weight_tag

METERS_IN_KILOMETER = 1000.0
SECONDS_IN_HOUR = 3600
SECONDS_IN_MINUTE = 60

def fetch_and_print_activities(client: Garmin, date_str: str) -> None:
    """
    Fetch activities for a given date and print them in a formatted markdown block.
    
    Args:
        client: An authenticated Garmin connect client.
        date_str: The date to fetch activities for, in 'YYYY-MM-DD' format.
    """
    activities = client.get_activities_by_date(date_str, date_str)
    if not activities:
        print(f"No activities found for {date_str}")
        return
        
    for act in activities:
        name = act.get('activityName')
        dist_km = act.get('distance', 0) / METERS_IN_KILOMETER
        dur_s = act.get('duration', 0)
        
        hours, remainder = divmod(dur_s, SECONDS_IN_HOUR)
        minutes, seconds = divmod(remainder, SECONDS_IN_MINUTE)
        dur_str = f"{int(hours):02d}:{int(minutes):02d}:{seconds:04.1f}"
        
        if dist_km > 0:
            pace_s_per_km = dur_s / dist_km
            p_min, p_sec = divmod(pace_s_per_km, SECONDS_IN_MINUTE)
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
        
        # Output directly (this is user facing data, not logs)
        print(f"## 🏃 Training\n- {name}")
        print("```text")
        print(f"{date_str}\n")
        
        act_type = act.get('activityType', {}).get('typeKey', '')
        weight_tag = _body_weight_tag(client, date_str, act_type)
        if weight_tag:
            print(weight_tag)

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


def _body_weight_tag(client: Garmin, date_str: str, act_type: str) -> str | None:
    if act_type != 'strength_training':
        return None

    reading = find_nearest_weight(client, date_str)
    if reading is None:
        return None

    return format_weight_tag(reading)
