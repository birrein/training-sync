import os
import json
import logging

logger = logging.getLogger(__name__)

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

def load_garmin_dict() -> dict:
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
    name_upper = fitbod_name.upper()
    if name_upper in FITBOD_CUSTOM_MAP:
        mapping = dict(FITBOD_CUSTOM_MAP[name_upper])
    elif name_upper in garmin_dict:
        mapping = dict(garmin_dict[name_upper])
    else:
        mapping = {"category": "UNKNOWN", "name": None}
        logger.warning(f"Exercise '{name_upper}' not found. Sent as UNKNOWN.")
    
    mapping["probability"] = 100.0
    return mapping
