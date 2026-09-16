import time
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.browser.browser_manager import BrowserManager
from app.browser.flow_client import FlowClient

def inspect_editor_after_dismiss():
    mgr = BrowserManager(headless=True)
    page = mgr.launch()
    
    flow_client = FlowClient(page, flow_url="https://flow.google.com/")
    flow_client.open()
    page.wait_for_timeout(3000)
    
    # Click "+ New project"
    new_proj_btn = page.get_by_text("New project")
    if new_proj_btn.count() > 0:
        new_proj_btn.first.click()
        page.wait_for_timeout(4000)
        
    # Dismiss any welcome / onboarding modal (e.g. "Get started" or "Close")
    get_started_btn = page.locator("button:has-text('Get started'), button[aria-label='Close']")
    if get_started_btn.count() > 0 and get_started_btn.first.is_visible():
        print("Dismissing onboarding modal...")
        get_started_btn.first.click()
        page.wait_for_timeout(2000)
        
    screenshot_path = mgr.capture_debug_screenshot("flow_studio_clean")
    print(f"Clean editor screenshot saved: {screenshot_path}")
    
    # Inspect prompt box and settings
    print("\n--- PROMPT BOX & SETTINGS INSPECTION ---")
    
    # Inspect editable area
    editables = page.locator("[contenteditable='true'], textarea, input")
    print(f"Editable elements count: {editables.count()}")
    for i in range(editables.count()):
        el = editables.nth(i)
        tag = el.evaluate("e => e.tagName")
        cls = el.get_attribute("class")
        vis = el.is_visible()
        print(f"  [{i}] Tag: {tag} | Visible: {vis} | Class: {cls[:40] if cls else ''}")
        
    # Click the Settings (tune) button to see aspect ratio / model options
    tune_btn = page.locator("button[aria-label='Settings']")
    if tune_btn.count() > 0 and tune_btn.first.is_visible():
        print("\nClicking Settings (tune) button...")
        tune_btn.first.click()
        page.wait_for_timeout(2000)
        mgr.capture_debug_screenshot("settings_panel_open")
        
        # List all options in settings
        settings_items = page.locator("[role='menuitem'], [role='option'], [role='radio'], button, select")
        print(f"Settings items visible count: {settings_items.count()}")
        for j in range(min(settings_items.count(), 30)):
            item = settings_items.nth(j)
            if item.is_visible():
                txt = item.inner_text().strip().replace("\n", " ")
                print(f"    Item [{j}]: '{txt}' | Aria: {item.get_attribute('aria-label')}")

    mgr.close()

if __name__ == "__main__":
    inspect_editor_after_dismiss()
