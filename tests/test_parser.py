import pytest
from sync import parse_workout

def test_parse_workout_valid_json():
    json_str = '{"date": "2026-06-11", "title": "Test Workout", "exercises": []}'
    result = parse_workout(json_str)
    assert result["date"] == "2026-06-11"
    assert result["title"] == "Test Workout"
    assert result["exercises"] == []

def test_parse_workout_invalid_json():
    json_str = '{"date": "2026-06-11", "title": "Test Workout"' # Missing closing brace
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse_workout(json_str)
