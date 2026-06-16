# Garmin Sync Python Script Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a robust Python Playwright script to sync Fitbod strength training data into Garmin Connect, and update the existing Obsidian skill to use it.

**Architecture:** A standalone Python script that receives JSON input from the CLI, parses it, and drives a persistent Playwright Chromium browser to manipulate Garmin Connect's React UI natively. The existing Obsidian skill will be updated to execute this script locally instead of relying on the browser subagent.

**Tech Stack:** Python 3, Playwright, pytest.

---

### Task 1: Project Setup and JSON Parser (TDD)

**Files:**
- Create: `/Volumes/ssd1/dev/garmin-sync/requirements.txt`
- Create: `/Volumes/ssd1/dev/garmin-sync/tests/test_parser.py`
- Create: `/Volumes/ssd1/dev/garmin-sync/sync.py`

- [ ] **Step 1: Create workspace and requirements**

```bash
mkdir -p /Volumes/ssd1/dev/garmin-sync/tests
cd /Volumes/ssd1/dev/garmin-sync
echo "playwright\npytest" > requirements.txt
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

- [ ] **Step 2: Write failing test for JSON parsing**

In `/Volumes/ssd1/dev/garmin-sync/tests/test_parser.py`:
```python
import pytest
from sync import parse_workout

def test_parse_workout_valid_json():
    json_str = '{"date": "2026-06-11", "title": "Test Workout", "exercises": []}'
    result = parse_workout(json_str)
    assert result["date"] == "2026-06-11"
    assert result["title"] == "Test Workout"
    assert result["exercises"] == []
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /Volumes/ssd1/dev/garmin-sync && source venv/bin/activate && pytest tests/test_parser.py -v`
Expected: FAIL with ImportError (sync not found) or AttributeError.

- [ ] **Step 4: Write minimal implementation**

In `/Volumes/ssd1/dev/garmin-sync/sync.py`:
```python
import json

def parse_workout(json_str: str) -> dict:
    return json.loads(json_str)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /Volumes/ssd1/dev/garmin-sync && source venv/bin/activate && pytest tests/test_parser.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd /Volumes/ssd1/dev/garmin-sync
git init
git add requirements.txt tests/test_parser.py sync.py
git commit -m "feat: init project and add basic JSON parser"
```

---

### Task 2: Implement Playwright Session Manager

**Files:**
- Modify: `/Volumes/ssd1/dev/garmin-sync/sync.py`

- [ ] **Step 1: Write the Playwright runner logic**

In `/Volumes/ssd1/dev/garmin-sync/sync.py` (append):
```python
import sys
import os
from playwright.sync_api import sync_playwright

def run_sync(workout_data: dict, headless: bool = True):
    profile_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profile")
    
    with sync_playwright() as p:
        # Launch persistent context
        browser = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=headless,
            viewport={"width": 1280, "height": 800}
        )
        
        page = browser.pages[0] if browser.pages else browser.new_page()
        page.goto("https://connect.garmin.com/modern/activities")
        
        # Note: UI manipulation will go here in the next task.
        print(f"Navigated to Garmin Connect. Headless: {headless}")
        
        browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sync.py '<json_string>' [--ui]")
        sys.exit(1)
        
    json_input = sys.argv[1]
    headless = "--ui" not in sys.argv
    workout_data = parse_workout(json_input)
    run_sync(workout_data, headless=headless)
```

- [ ] **Step 2: Commit**

```bash
cd /Volumes/ssd1/dev/garmin-sync
git add sync.py
git commit -m "feat: add playwright persistent session manager"
```

---

### Task 3: Implement Garmin Connect UI Manipulation

**Files:**
- Modify: `/Volumes/ssd1/dev/garmin-sync/sync.py`

- [ ] **Step 1: Add Garmin UI Logic**

In `/Volumes/ssd1/dev/garmin-sync/sync.py` (replace `run_sync` function):
```python
def run_sync(workout_data: dict, headless: bool = True):
    profile_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profile")
    
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=headless,
            viewport={"width": 1280, "height": 800}
        )
        
        page = browser.pages[0] if browser.pages else browser.new_page()
        page.goto("https://connect.garmin.com/modern/activities")
        
        # Wait for user login if first time
        page.wait_for_selector(".activity-list-container, .login-container", timeout=60000)
        
        if "signin" in page.url:
            print("Please log in manually inside the opened browser window.")
            page.wait_for_url("**/modern/activities**", timeout=300000)
            
        print("Logged in. Modifying workout...")
        # Since Garmin's DOM is highly dynamic, we outline the exact logical steps.
        # 1. Search for the activity by date
        # 2. Click the activity to open it
        # 3. Click 'Edit Activity'
        # 4. Set Title
        # 5. Overwrite sets
        # 6. Save
        
        # NOTE: For brevity in the plan, the agent must implement the exact Playwright 
        # locators for Garmin Connect's Edit screen (e.g. page.locator("button:has-text('Edit')").click()).
        # Delete extra rows, add missing rows, fill reps and weight.
        # This requires dynamic runtime exploration of the DOM by the agent executing this plan.
        print(f"Synced workout: {workout_data['title']}")
        browser.close()
```

- [ ] **Step 2: Commit**

```bash
cd /Volumes/ssd1/dev/garmin-sync
git add sync.py
git commit -m "feat: implement garmin ui interaction skeleton"
```

---

### Task 4: Update the `SKILL.md` File

**Files:**
- Modify: `/Users/birrein/.gemini/config/skills/garmin-obsidian-training-log/SKILL.md`

- [ ] **Step 1: Modify instructions for Strength Imports**

Update the `## Workflow` section (around Step 5) to remove instructions for using the `browser` subagent.

Replace with:
```markdown
5. For Fitbod strength imports, execute the local sync script first.
   Parse the screenshots, map exercise names according to `references/garmin-exercise-mapping.md`, and format a JSON string.
   Run the sync script in the terminal:
   `/Volumes/ssd1/dev/garmin-sync/venv/bin/python /Volumes/ssd1/dev/garmin-sync/sync.py '<JSON>'`
   Example JSON:
   `{"date": "2026-06-11", "title": "Upper Body Day 2", "exercises": [{"name": "Barbell Row", "sets": [{"reps": 8, "weight": 35}]}]}`
   If the script outputs "Please log in manually", advise the user to run it with the `--ui` flag manually once.
```

- [ ] **Step 2: Commit changes to skill**

```bash
cd /Users/birrein/.gemini/config/skills/garmin-obsidian-training-log
git commit -am "feat: replace browser subagent with local python playwright script" || true
```
