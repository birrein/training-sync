"""
Exercise mapping module for translating Fitbod exercise names to Garmin exercise categories.
"""
import os
import json
import logging

logger = logging.getLogger(__name__)

FITBOD_CUSTOM_MAP = {
    "BENCH PRESS": {"category": "BENCH_PRESS", "name": "BARBELL_BENCH_PRESS"},
    "BARBELL BENCH PRESS": {"category": "BENCH_PRESS", "name": "BARBELL_BENCH_PRESS"},
    "FACE PULL": {"category": "ROW", "name": "FACE_PULL"},
    "CABLE FACE PULL": {"category": "ROW", "name": "FACE_PULL"},
    "DEADLIFT": {"category": "DEADLIFT", "name": "BARBELL_DEADLIFT"},
    "BARBELL DEADLIFT": {"category": "DEADLIFT", "name": "BARBELL_DEADLIFT"},
    "BARBELL HIP THRUST": {
        "category": "HIP_RAISE",
        "name": "BARBELL_HIP_THRUST_WITH_BENCH",
    },
    "CABLE CRUNCH": {"category": "CRUNCH", "name": "CABLE_CRUNCH"},
    "DIP": {"category": "TRICEPS_EXTENSION", "name": "BODY_WEIGHT_DIP"},
    "BODY-WEIGHT DIP": {"category": "TRICEPS_EXTENSION", "name": "BODY_WEIGHT_DIP"},
    "INCLINE DUMBBELL CURL": {"category": "CURL", "name": "INCLINE_DUMBBELL_BICEPS_CURL"},
    "SINGLE ARM PREACHER CURL": {"category": "CURL", "name": "ONE_ARM_PREACHER_CURL"},
    "ONE-ARM PREACHER CURL": {"category": "CURL", "name": "ONE_ARM_PREACHER_CURL"},
    "DUMBBELL FLY": {"category": "FLYE", "name": "DUMBBELL_FLYE"},
    "DUMBBELL BICEP CURL": {"category": "CURL", "name": "DUMBBELL_BICEPS_CURL"},
    "DUMBBELL HAMMER CURL": {"category": "CURL", "name": "DUMBBELL_HAMMER_CURL"},
    "HAMMER CURLS": {"category": "CURL", "name": "DUMBBELL_HAMMER_CURL"},
    "BICEP CURL": {"category": "CURL", "name": "DUMBBELL_BICEPS_CURL"},
    "TRICEP EXTENSION": {"category": "TRICEPS_EXTENSION", "name": "TRICEPS_PRESSDOWN"},
    "SKULLCRUSHER": {"category": "TRICEPS_EXTENSION", "name": "LYING_EZ_BAR_TRICEPS_EXTENSION"},
    "LYING EZ-BAR TRICEPS EXTENSION": {
        "category": "TRICEPS_EXTENSION",
        "name": "LYING_EZ_BAR_TRICEPS_EXTENSION",
    },
}

DEFAULT_PROBABILITY = 100.0

def load_garmin_dict() -> dict:
    """
    Load the dictionary of Garmin exercises from a JSON file.

    Returns:
        dict: A dictionary mapping exercise names to their Garmin categories and sub-names.
    """
    dict_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'garmin_exercises.json')
    try:
        with open(dict_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for k, v in data.items():
                if v.get('name') == v.get('category'):
                    v['name'] = None
            return data
    except FileNotFoundError:
        logger.warning("garmin_exercises.json not found. Using empty dictionary.")
        return {}

def get_mapping(fitbod_name: str, garmin_dict: dict) -> dict:
    """
    Get the corresponding Garmin exercise mapping for a given Fitbod exercise name.

    Args:
        fitbod_name (str): The name of the exercise from Fitbod.
        garmin_dict (dict): The loaded dictionary of Garmin exercises.

    Returns:
        dict: A dictionary containing the Garmin 'category', 'name', and 'probability'.
    """
    name_upper = fitbod_name.upper()
    if name_upper in FITBOD_CUSTOM_MAP:
        mapping = dict(FITBOD_CUSTOM_MAP[name_upper])
    elif name_upper in garmin_dict:
        mapping = dict(garmin_dict[name_upper])
    else:
        mapping = {"category": "UNKNOWN", "name": None}
        logger.warning(f"Exercise '{name_upper}' not found. Sent as UNKNOWN.")
    
    mapping["probability"] = DEFAULT_PROBABILITY
    return mapping
