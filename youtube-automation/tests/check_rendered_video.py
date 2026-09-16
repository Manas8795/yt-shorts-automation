import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.browser.browser_manager import BrowserManager
from app.browser.flow_client import FlowClient

def check_rendered_video():
    mgr = BrowserManager(headless=True)
    page = mgr.launch()
    
    page.goto("https://flow.google.com/project/4c894033-8593-4677-844e-506bc7b67657", wait_until="domcontentloaded")
    page.wait_for_timeout(5000)
    
    screenshot = mgr.capture_debug_screenshot("check_video_completion")
    print(f"Canvas screenshot: {screenshot}")
    
    # Check if video is present
    videos = page.locator("video")
    print(f"Video elements count: {videos.count()}")
    for i in range(videos.count()):
        v = videos.nth(i)
        src = v.get_attribute("src")
        print(f"  Video [{i}] src: {src[:60] if src else 'No src'}")

    mgr.close()

if __name__ == "__main__":
    check_rendered_video()
