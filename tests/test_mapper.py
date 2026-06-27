from garmin_sync.mapper import get_mapping


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
