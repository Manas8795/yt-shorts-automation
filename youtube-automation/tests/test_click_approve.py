import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.browser.browser_manager import BrowserManager

def test_click_approve():
    mgr = BrowserManager(headless=True)
    page = mgr.launch()
    
    page.goto("https://flow.google.com/project/4c894033-8593-4677-844e-506bc7b67657", wait_until="domcontentloaded")
    page.wait_for_timeout(5000)
    
    # Try get_by_text
    always_btn = page.get_by_text("Always approve")
    approve_btn = page.get_by_text("Approve", exact=True)
    
    print(f"Always approve count: {always_btn.count()}")
    print(f"Approve count: {approve_btn.count()}")
    
    if always_btn.count() > 0:
        print("Clicking 'Always approve'...")
        always_btn.first.click()
        page.wait_for_timeout(6000)
    elif approve_btn.count() > 0:
        print("Clicking 'Approve'...")
        approve_btn.first.click()
        page.wait_for_timeout(6000)
        
    screenshot_path = mgr.capture_debug_screenshot("rendering_initiated")
    print(f"Post-click screenshot: {screenshot_path}")
    mgr.close()

if __name__ == "__main__":
    test_click_approve()
