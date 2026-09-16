import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.browser.browser_manager import BrowserManager

def inspect_existing_video():
    mgr = BrowserManager(headless=True)
    page = mgr.launch()
    
    # Read-only check on the generated project
    page.goto("https://flow.google.com/project/4c894033-8593-4677-844e-506bc7b67657", wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    
    # Close any open drawers/panels if open
    close_btn = page.locator("button[aria-label='Close account panel'], button[aria-label='Close']")
    if close_btn.count() > 0 and close_btn.first.is_visible():
        close_btn.first.click()
        page.wait_for_timeout(1000)
        
    screenshot_path = mgr.capture_debug_screenshot("verified_generated_video")
    print(f"Generated video screenshot saved: {screenshot_path}")
    print(f"Project Title: {page.title()}")
    
    # Check media card details
    media_cards = page.locator("div:has(> [style*='background']), [role='gridcell'], div:has(> video)")
    print(f"Media cards found on canvas: {media_cards.count()}")
    
    mgr.close()

if __name__ == "__main__":
    inspect_existing_video()
