import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.browser.browser_manager import BrowserManager
from app.browser.flow_client import FlowClient

def inspect_studio():
    mgr = BrowserManager(headless=True)
    page = mgr.launch()
    
    flow_client = FlowClient(page, flow_url="https://flow.google.com/")
    flow_client.open()
    
    # Wait for the main page to load
    page.wait_for_timeout(4000)
    
    # Click "+ New project"
    print("\nLooking for '+ New project' button...")
    new_proj_btn = page.get_by_text("New project")
    if new_proj_btn.count() > 0:
        print(f"Found 'New project' button! Clicking it...")
        new_proj_btn.first.click()
        page.wait_for_timeout(6000)
    else:
        print("Could not find 'New project' by text. Checking other selectors...")
        page.locator("button:has-text('New project'), [aria-label*='New project'], [aria-label*='Create project']").first.click()
        page.wait_for_timeout(6000)
        
    print(f"Studio Page URL: {page.url}")
    print(f"Studio Page Title: {page.title()}")
    
    # Take full page screenshot of the studio editor
    screenshot_path = mgr.capture_debug_screenshot("flow_studio_editor")
    print(f"Studio editor screenshot saved to: {screenshot_path}")
    
    # Inspect inputs, textareas, buttons, contenteditable elements
    print("\n--- DOM INSPECTION ---")
    
    textareas = page.locator("textarea, input[type='text'], [contenteditable='true']")
    print(f"Found {textareas.count()} prompt/input candidate elements:")
    for i in range(textareas.count()):
        el = textareas.nth(i)
        try:
            placeholder = el.get_attribute("placeholder")
            aria_label = el.get_attribute("aria-label")
            tag_name = el.evaluate("e => e.tagName")
            print(f"  [{i}] Tag: {tag_name} | Placeholder: {placeholder} | Aria-label: {aria_label} | Visible: {el.is_visible()}")
        except Exception as e:
            print(f"  [{i}] Error: {e}")

    buttons = page.locator("button, [role='button']")
    print(f"\nFound {buttons.count()} buttons on page:")
    for i in range(min(buttons.count(), 30)):
        el = buttons.nth(i)
        try:
            text = el.inner_text().strip().replace("\n", " ")
            aria_label = el.get_attribute("aria-label")
            data_testid = el.get_attribute("data-testid")
            if el.is_visible():
                print(f"  [{i}] Text: '{text}' | Aria-label: '{aria_label}' | TestId: '{data_testid}'")
        except Exception as e:
            pass

    mgr.close()

if __name__ == "__main__":
    inspect_studio()
