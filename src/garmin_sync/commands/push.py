"""
This module provides functionality to parse workout data and push it to Garmin Connect.
"""

import json
import logging
from garminconnect import Garmin
from garmin_sync.garmin_payloads import build_exercise_sets_payload
from garmin_sync.mapper import load_garmin_dict
from garmin_sync.workouts import strength_workout_from_dict

logger = logging.getLogger(__name__)


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
    workout = strength_workout_from_dict(workout_data)
    activities = client.get_activities_by_date(workout.date, workout.date)
        
    if not activities:
        raise RuntimeError(f"No activities found for date {workout.date}")
        
    activity = None
    for act in activities:
        activity_type = act.get('activityType', {})
        if activity_type.get('typeKey') == 'strength_training':
            activity = act
            break
            
    if not activity:
        raise RuntimeError(f"No strength training activity found for date {workout.date}")
        
    activity_id = activity.get('activityId')
    logger.info(f"Found activity: {activity_id} - {activity.get('activityName')}")
    
    if workout.title:
        client.set_activity_name(activity_id, workout.title)
        logger.info(f"Updated title to: {workout.title}")
        
    if not workout.exercises:
        return

    existing_sets = client.get_activity_exercise_sets(activity_id)
    existing_array = existing_sets.get('exerciseSets', [])
    existing_sets['exerciseSets'] = build_exercise_sets_payload(
        workout,
        existing_array,
        load_garmin_dict(),
    )
    try:
        client.set_activity_exercise_sets(activity_id, existing_sets)
        logger.info("Successfully updated exercises.")
    except Exception as e:
        logger.error(f"Failed to update exercises: {e}")
        raise
