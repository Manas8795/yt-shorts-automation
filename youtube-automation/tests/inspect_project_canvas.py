import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.browser.browser_manager import BrowserManager

def inspect_project_canvas():
    mgr = BrowserManager(headless=True)
    page = mgr.launch()
    
    # Open the exact project from the run
    page.goto("https://flow.google.com/project/4c894033-8593-4677-844e-506bc7b67657", wait_until="domcontentloaded")
    page.wait_for_timeout(6000)
    
    screenshot_path = mgr.capture_debug_screenshot("inspect_project_after_submit")
    print(f"Canvas screenshot saved: {screenshot_path}")
    
    # Dump text on page
    content = page.content()
    print("Page Title:", page.title())
    
    buttons = page.locator("button, [role='button']")
    print(f"Buttons on canvas ({buttons.count()}):")
    for i in range(buttons.count()):
        b = buttons.nth(i)
        if b.is_visible():
            txt = b.inner_text().strip().replace("\n", " ")
            aria = b.get_attribute("aria-label")
            print(f"  [{i}] Text: '{txt}' | Aria: '{aria}'")
            
    mgr.close()

if __name__ == "__main__":
    inspect_project_canvas()
