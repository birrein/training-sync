"""
This module provides functionality to parse workout data and push it to Garmin Connect.
"""

import json
import logging
from datetime import datetime
from garminconnect import Garmin
from garmin_sync.mapper import get_mapping, load_garmin_dict

logger = logging.getLogger(__name__)

GRAMS_PER_KG = 1000.0
DEFAULT_ACTIVE_DURATION = 30.0
DEFAULT_REST_DURATION = 60.0
REST_WEIGHT = -1.0

def parse_workout(json_str: str) -> dict:
    """
    Parse a JSON string containing workout data into a dictionary.

    Args:
        json_str (str): The JSON string representation of the workout.

    Returns:
        dict: The parsed workout data.

    Raises:
        ValueError: If the JSON string is invalid.
    """
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

def push_workout(client: Garmin, workout_data: dict):
    """
    Push a workout dictionary to an existing Garmin Connect activity.

    Args:
        client (Garmin): The authenticated Garmin Connect client.
        workout_data (dict): The parsed workout data to be pushed.

    Raises:
        RuntimeError: If no suitable strength training activity is found for the given date.
        Exception: Re-raises any exception encountered when updating exercises.
    """
    garmin_dict = load_garmin_dict()
    date = workout_data.get('date', datetime.today().strftime('%Y-%m-%d'))
    activities = client.get_activities_by_date(date, date)
        
    if not activities:
        raise RuntimeError(f"No activities found for date {date}")
        
    activity = None
    for act in activities:
        activity_type = act.get('activityType', {})
        if activity_type.get('typeKey') == 'strength_training':
            activity = act
            break
            
    if not activity:
        raise RuntimeError(f"No strength training activity found for date {date}")
        
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
                "weight": s.get('weight', 0) * GRAMS_PER_KG,
                "setType": "ACTIVE",
                "duration": active_base.get("duration", DEFAULT_ACTIVE_DURATION),
                "startTime": active_base.get("startTime"),
                "wktStepIndex": None,
                "messageIndex": None
            })
            msg_idx += 1
            
            rest_base = existing_array[msg_idx] if msg_idx < len(existing_array) else {}
            sets_payload.append({
                "exercises": [],
                "repetitionCount": None,
                "weight": REST_WEIGHT,
                "setType": "REST",
                "duration": rest_base.get("duration", DEFAULT_REST_DURATION),
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
        raise
