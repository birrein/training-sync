import json
import logging
from datetime import datetime
from garminconnect import Garmin
from garmin_sync.mapper import get_mapping, load_garmin_dict

logger = logging.getLogger(__name__)

def parse_workout(json_str: str) -> dict:
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

def push_workout(client: Garmin, workout_data: dict):
    garmin_dict = load_garmin_dict()
    date = workout_data.get('date', datetime.today().strftime('%Y-%m-%d'))
    activities = client.get_activities_by_date(date, date)
        
    if not activities:
        raise RuntimeError(f"No activities found for date {date}")
        
    activity = activities[0]
    activity_id = activity.get('activityId')
    logger.info(f"Found activity: {activity_id} - {activity.get('activityName')}")
    
    title = workout_data.get('title')
    if title:
        client.set_activity_name(activity_id, title)
        logger.info(f"Updated title to: {title}")
        
    exercises = workout_data.get('exercises', [])
    if not exercises:
        return

    existing_sets = client.get_activity_exercise_sets(activity_id)
    existing_array = existing_sets.get('exerciseSets', [])
    
    sets_payload = []
    msg_idx = 0
    
    for ex in exercises:
        mapping = get_mapping(ex.get('name', 'UNKNOWN'), garmin_dict)
        
        for s in ex.get('sets', []):
            active_base = existing_array[msg_idx] if msg_idx < len(existing_array) else {}
            sets_payload.append({
                "exercises": [mapping],
                "repetitionCount": s.get('reps', 0),
                "weight": s.get('weight', 0) * 1000.0,
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
                "weight": -1.0,
                "setType": "REST",
                "duration": rest_base.get("duration", 60.0),
                "startTime": None,
                "wktStepIndex": None,
                "messageIndex": None
            })
            msg_idx += 1
            
    existing_sets['exerciseSets'] = sets_payload
    try:
        client.set_activity_exercise_sets(activity_id, existing_sets)
        logger.info("Successfully updated exercises.")
    except Exception as e:
        logger.error(f"Failed to update exercises: {e}")
