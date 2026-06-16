import json
import sys
import os
import argparse
from playwright.sync_api import sync_playwright, TimeoutError

def parse_workout(json_str: str) -> dict:
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

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
        
        try:
            page.wait_for_url("**/modern/activities**", timeout=5000)
        except TimeoutError:
            pass
            
        if "signin" in page.url:
            if headless:
                raise RuntimeError("Authentication required. Please run the script with --ui for the initial login.")
            print("Please log in manually inside the opened browser window.")
            page.wait_for_url("**/modern/activities**", timeout=300000)
            
        print("Logged in. Modifying workout...")
        
        # 1. Search for the activity by date (skeleton)
        print(f"Assuming we found the activity for {workout_data.get('date')}...")
        
        # 2. Click 'Edit Activity'
        # page.get_by_role("button", name="Edit").click()
        
        # 3. Set Title
        # page.locator("input[name='title']").fill(workout_data.get('title', ''))
        
        # 4. Overwrite sets
        # for exercise in workout_data.get('exercises', []):
        #     page.get_by_role("button", name="Add Exercise").click()
        
        # 5. Save
        # page.get_by_role("button", name="Save").click()
        
        print(f"Synced workout: {workout_data.get('title')}")
        browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync Fitbod workout to Garmin Connect.")
    parser.add_argument("json_string", help="JSON string containing the workout data")
    parser.add_argument("--ui", action="store_true", help="Run with UI visible (non-headless mode)")
    
    args = parser.parse_args()
    
    try:
        workout_data = parse_workout(args.json_string)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
        
    run_sync(workout_data, headless=not args.ui)
