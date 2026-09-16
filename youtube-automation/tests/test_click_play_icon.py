import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.browser.browser_manager import BrowserManager
from app.storage.file_manager import FileManager

def test_click_play_icon():
    mgr = BrowserManager(headless=True)
    page = mgr.launch()
    
    file_mgr = FileManager()
    job_dir = file_mgr.prepare_job_directory("job_0001")
    target_video_path = os.path.join(job_dir, "video.mp4")
    
    page.goto("https://flow.google.com/project/4c894033-8593-4677-844e-506bc7b67657", wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    
    # Close account panel by pressing Escape or clicking close
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)
    
    # Click at the play button coordinates on the video card (x: 212, y: 110)
    print("Clicking play icon on video tile at (212, 110)...")
    page.mouse.click(212, 110)
    page.wait_for_timeout(3000)
    
    screenshot = mgr.capture_debug_screenshot("video_player_active")
    print(f"Player screenshot: {screenshot}")
    
    # Inspect video elements and buttons
    videos = page.locator("video")
    print(f"Video elements now on page: {videos.count()}")
    for i in range(videos.count()):
        v = videos.nth(i)
        print(f"  Video [{i}] src: {v.get_attribute('src')}")

    # Inspect all buttons visible now
    buttons = page.locator("button, [role='button'], a")
    print(f"Actionable buttons ({buttons.count()}):")
    for i in range(buttons.count()):
        b = buttons.nth(i)
        if b.is_visible():
            txt = b.inner_text().strip().replace("\n", " ")
            aria = b.get_attribute("aria-label")
            print(f"  [{i}] Text: '{txt}' | Aria: '{aria}'")
            if (aria and "download" in aria.lower()) or "download" in txt.lower():
                print(f"Found download button! Triggering download...")
                with page.expect_download(timeout=30000) as download_info:
                    b.click()
                download = download_info.value
                download.save_as(target_video_path)
                print(f"SUCCESS! Video downloaded to: {target_video_path}")
                break

    if os.path.exists(target_video_path):
        size_mb = os.path.getsize(target_video_path) / (1024 * 1024)
        print(f"VERIFIED: {target_video_path} exists ({round(size_mb, 2)} MB)")

    mgr.close()

if __name__ == "__main__":
    test_click_play_icon()
