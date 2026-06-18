# Garmin Sync Modular Refactoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the single `sync.py` script into a modular, installable Python package (`garmin_sync`).

**Architecture:** We are using a Pragmatic Modular Architecture. The code will be divided into `cli.py` (entry point), `auth.py` (login logic), `mapper.py` (JSON dictionary and alias mapping), and `commands/` for the push and fetch logic. A `pyproject.toml` will make it installable.

**Tech Stack:** Python 3, `garminconnect`, `argparse`.

---

### Task 1: Initialize Package Structure and Config

**Files:**
- Create: `pyproject.toml`
- Create: `src/garmin_sync/__init__.py`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "garmin-sync"
version = "0.1.0"
description = "Bidirectional Garmin Connect sync for strength and running"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "garminconnect",
    "requests"
]

[project.scripts]
garmin-sync = "garmin_sync.cli:main"
```

- [ ] **Step 2: Create package `__init__.py`**

```python
__version__ = "0.1.0"
```

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml src/garmin_sync/__init__.py
git commit -m "chore: setup pyproject.toml and package structure"
```

---

### Task 2: Implement `mapper.py`

**Files:**
- Create: `src/garmin_sync/mapper.py`
- Modify: Move `garmin_exercises.json` into `src/garmin_sync/` so it is part of the package data.

- [ ] **Step 1: Move dictionary file**

```bash
mv garmin_exercises.json src/garmin_sync/garmin_exercises.json
```

- [ ] **Step 2: Write `mapper.py` implementation**

```python
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
```

- [ ] **Step 3: Test `mapper.py` execution**

```bash
python -c "from src.garmin_sync.mapper import load_garmin_dict; d = load_garmin_dict(); assert len(d) > 0"
```
Expected: No output (success).

- [ ] **Step 4: Commit**

```bash
git add src/garmin_sync/garmin_exercises.json src/garmin_sync/mapper.py
git commit -m "refactor: extract exercise mapping logic to mapper.py"
```

---

### Task 3: Implement `auth.py`

**Files:**
- Create: `src/garmin_sync/auth.py`

- [ ] **Step 1: Write `auth.py` implementation**

```python
import os
import sys
import getpass
import logging
from garminconnect import Garmin

logger = logging.getLogger(__name__)

def get_client() -> Garmin:
    # Try looking in current working directory first, fallback to package dir
    token_file = "garmin_token.json"
    if not os.path.exists(token_file):
        token_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "garmin_token.json")
        
    client = Garmin()
    needs_login = True
    
    if os.path.exists(token_file):
        try:
            client.login(tokenstore=token_file)
            needs_login = False
            logger.info("Logged in using stored token.")
        except Exception:
            logger.warning("Stored token expired or invalid.")
            needs_login = True
            
    if needs_login:
        if not sys.stdin.isatty():
            sys.exit("Error: Garmin session expired. Please run interactively to log in.")
        email = input("Garmin Email: ")
        password = getpass.getpass("Garmin Password: ")
        client = Garmin(email, password)
        try:
            client.login(tokenstore=token_file)
            logger.info("Interactive login successful.")
        except Exception as e:
            raise RuntimeError(f"Login failed: {e}")
            
    return client
```

- [ ] **Step 2: Commit**

```bash
git add src/garmin_sync/auth.py
git commit -m "refactor: centralize garmin authentication logic"
```

---

### Task 4: Implement `commands/push.py`

**Files:**
- Create: `src/garmin_sync/commands/__init__.py`
- Create: `src/garmin_sync/commands/push.py`

- [ ] **Step 1: Write `push.py`**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add src/garmin_sync/commands/__init__.py src/garmin_sync/commands/push.py
git commit -m "refactor: extract workout pushing logic"
```

---

### Task 5: Implement `commands/fetch.py`

**Files:**
- Create: `src/garmin_sync/commands/fetch.py`

- [ ] **Step 1: Write `fetch.py`**

```python
from garminconnect import Garmin

def fetch_and_print_activities(client: Garmin, date_str: str):
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
        
        # Output directly (this is user facing data, not logs)
        print(f"## 🏃 Training\n- {name}")
        print("```text")
        print(f"{date_str}\n")
        
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
```

- [ ] **Step 2: Commit**

```bash
git add src/garmin_sync/commands/fetch.py
git commit -m "refactor: extract activity fetching and formatting logic"
```

---

### Task 6: Implement `cli.py` and Clean Up Monolith

**Files:**
- Create: `src/garmin_sync/cli.py`
- Modify: Delete original `sync.py`
- Modify: `.gitignore` to ignore the built package (`*.egg-info`)

- [ ] **Step 1: Write `cli.py`**

```python
import os
import sys
import argparse
import logging
from garmin_sync.auth import get_client
from garmin_sync.commands.push import push_workout, parse_workout
from garmin_sync.commands.fetch import fetch_and_print_activities

def setup_logging():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="Sync Fitbod JSON to Garmin Connect, or fetch Garmin activities.")
    parser.add_argument("json_string", nargs="?", help="JSON string of the workout or path to JSON file")
    parser.add_argument("--fetch", help="Fetch activities for a given date (YYYY-MM-DD)", type=str)
    args = parser.parse_args()

    client = get_client()

    if args.fetch:
        fetch_and_print_activities(client, args.fetch)
    elif args.json_string:
        try:
            if os.path.isfile(args.json_string):
                with open(args.json_string, 'r') as f:
                    workout_data = parse_workout(f.read())
            else:
                workout_data = parse_workout(args.json_string)
        except ValueError as e:
            sys.exit(f"Data error: {e}")
            
        push_workout(client, workout_data)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test installation and execution**

```bash
pip install -e .
garmin-sync -h
```
Expected: Usage text is printed successfully.

- [ ] **Step 3: Update `.gitignore`**

```bash
echo "*.egg-info/" >> .gitignore
```

- [ ] **Step 4: Remove monolith**

```bash
rm sync.py
```

- [ ] **Step 5: Commit**

```bash
git add src/garmin_sync/cli.py .gitignore sync.py
git commit -m "refactor: implement CLI entrypoint and remove monolith"
```
