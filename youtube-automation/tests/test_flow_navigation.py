import time
from app.browser.browser_manager import BrowserManager
from app.browser.flow_client import FlowClient

def test_flow_navigation():
    mgr = BrowserManager()
    page = mgr.launch()
    page.goto("https://labs.google/fx/tools/flow", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    create_btn = page.get_by_text("Create with Google Flow")
    print(f"Create button found count: {create_btn.count()}")
    if create_btn.count() > 0:
        print("Clicking 'Create with Google Flow' button...")
        create_btn.first.click()
        page.wait_for_timeout(6000)
    
    print(f"Current URL: {page.url}")
    print(f"Current Title: {page.title()}")
    screenshot_path = mgr.capture_debug_screenshot("flow_studio_page")
    print(f"Screenshot saved: {screenshot_path}")
    mgr.close()

if __name__ == "__main__":
    test_flow_navigation()
