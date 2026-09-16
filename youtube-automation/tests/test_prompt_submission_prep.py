import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.browser.browser_manager import BrowserManager
from app.browser.flow_client import FlowClient

def test_prep():
    mgr = BrowserManager(headless=True)
    page = mgr.launch()

    client = FlowClient(page, flow_url="https://flow.google.com/")
    client.open()

    # Navigate to create
    client.navigate_to_create()

    # Configure 9:16 aspect ratio
    client.configure_generation(aspect_ratio="9:16", count=1)

    # Load prompt
    with open("prompts/test_prompt.txt", "r", encoding="utf-8") as f:
        prompt = f.read().strip()

    # Enter prompt
    client.enter_prompt(prompt)

    # Capture screenshot of prompt entered
    screenshot_path = mgr.capture_debug_screenshot("prompt_entered_verified")
    print(f"Verified prompt entry screenshot: {screenshot_path}")

    mgr.close()

if __name__ == "__main__":
    test_prep()
