import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.browser.browser_manager import BrowserManager

def test_approve_generation():
    mgr = BrowserManager(headless=True)
    page = mgr.launch()
    
    # Open the existing session project
    page.goto("https://flow.google.com/project/4c894033-8593-4677-844e-506bc7b67657", wait_until="domcontentloaded")
    page.wait_for_timeout(5000)
    
    # Check for "Always approve" or "Approve" buttons
    approve_btn = page.locator("button:has-text('Always approve'), button:has-text('Approve')")
    print(f"Approve buttons found: {approve_btn.count()}")
    if approve_btn.count() > 0:
        print("Clicking 'Always approve'...")
        # Prefer 'Always approve' so future generations start immediately
        always_btn = page.locator("button:has-text('Always approve')")
        if always_btn.count() > 0:
            always_btn.first.click()
        else:
            approve_btn.first.click()
            
        page.wait_for_timeout(5000)
        
    screenshot_path = mgr.capture_debug_screenshot("after_approve_clicked")
    print(f"Post-approval screenshot: {screenshot_path}")
    
    # Check if rendering tile appeared
    tiles = page.locator("[role='gridcell'], video, [data-testid*='tile'], [role='progressbar'], .media-tile")
    print(f"Canvas tiles count after approval: {tiles.count()}")
    
    mgr.close()

if __name__ == "__main__":
    test_approve_generation()
