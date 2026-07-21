from training_sync.garmin.exercise_mapping import get_mapping


def test_face_pull_uses_row_mapping_instead_of_suspension():
    garmin_dict = {
        "FACE PULL": {"category": "SUSPENSION", "name": "FACE_PULL"},
    }

    assert get_mapping("Face Pull", garmin_dict) == {
        "category": "ROW",
        "name": "FACE_PULL",
        "probability": 100.0,
    }


def test_cable_face_pull_maps_to_garmin_face_pull():
    assert get_mapping("Cable Face Pull", {}) == {
        "category": "ROW",
        "name": "FACE_PULL",
        "probability": 100.0,
    }


def test_fitbod_upper_body_aliases_use_garmin_enum_names():
    assert get_mapping("Single Arm Preacher Curl", {}) == {
        "category": "CURL",
        "name": "ONE_ARM_PREACHER_CURL",
        "probability": 100.0,
    }
    assert get_mapping("Skullcrusher", {}) == {
        "category": "TRICEPS_EXTENSION",
        "name": "LYING_EZ_BAR_TRICEPS_EXTENSION",
        "probability": 100.0,
    }
    assert get_mapping("Hammer Curls", {}) == {
        "category": "CURL",
        "name": "DUMBBELL_HAMMER_CURL",
        "probability": 100.0,
    }


def test_fitbod_lower_body_aliases_use_garmin_enum_names():
    assert get_mapping("Deadlift", {}) == {
        "category": "DEADLIFT",
        "name": "BARBELL_DEADLIFT",
        "probability": 100.0,
    }
    assert get_mapping("Barbell Hip Thrust", {}) == {
        "category": "HIP_RAISE",
        "name": "BARBELL_HIP_THRUST_WITH_BENCH",
        "probability": 100.0,
    }
    assert get_mapping("Cable Crunch", {}) == {
        "category": "CRUNCH",
        "name": "CABLE_CRUNCH",
        "probability": 100.0,
    }
