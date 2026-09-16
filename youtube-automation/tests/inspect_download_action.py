import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.browser.browser_manager import BrowserManager

def inspect_download_action():
    mgr = BrowserManager(headless=True)
    page = mgr.launch()
    
    page.goto("https://flow.google.com/project/4c894033-8593-4677-844e-506bc7b67657", wait_until="domcontentloaded")
    page.wait_for_timeout(5000)
    
    # Locate the video tile on canvas
    tile = page.locator("div:has(> [style*='background']), div[tabindex='0'], [role='gridcell']").first
    
    # Click the video tile to open/focus it
    print("Clicking video tile on canvas...")
    tile.click()
    page.wait_for_timeout(2000)
    
    screenshot = mgr.capture_debug_screenshot("video_tile_clicked")
    print(f"Clicked tile screenshot: {screenshot}")
    
    # Inspect all visible buttons and menu items now
    buttons = page.locator("button, [role='button'], [role='menuitem'], a")
    print(f"\nVisible actionable elements ({buttons.count()}):")
    for i in range(buttons.count()):
        b = buttons.nth(i)
        if b.is_visible():
            txt = b.inner_text().strip().replace("\n", " ")
            aria = b.get_attribute("aria-label")
            print(f"  [{i}] Text: '{txt}' | Aria: '{aria}'")

    mgr.close()

if __name__ == "__main__":
    inspect_download_action()
