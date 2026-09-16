import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.browser.browser_manager import BrowserManager
from app.storage.file_manager import FileManager

def open_video_player_and_download():
    mgr = BrowserManager(headless=True)
    page = mgr.launch()
    
    file_mgr = FileManager()
    job_dir = file_mgr.prepare_job_directory("job_0001")
    target_video_path = os.path.join(job_dir, "video.mp4")
    
    page.goto("https://flow.google.com/project/4c894033-8593-4677-844e-506bc7b67657", wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    
    # Click the play button or the video tile
    play_icon = page.locator("button:has-text('play_arrow'), button:has-text('play_circle'), [aria-label*='Play'], [aria-label*='Open video']").first
    if play_icon.count() > 0:
        print("Clicking play icon on video tile...")
        play_icon.click()
    else:
        print("Clicking the video tile directly...")
        page.locator("div:has(> [style*='background'])").first.click()
        
    page.wait_for_timeout(3000)
    
    screenshot = mgr.capture_debug_screenshot("video_player_modal")
    print(f"Player modal screenshot: {screenshot}")
    
    # Check all buttons inside modal
    buttons = page.locator("button, [role='button'], a, [aria-label*='Download'], button:has-text('download')")
    print(f"\nModal buttons found ({buttons.count()}):")
    for i in range(buttons.count()):
        b = buttons.nth(i)
        if b.is_visible():
            txt = b.inner_text().strip().replace("\n", " ")
            aria = b.get_attribute("aria-label")
            print(f"  [{i}] Text: '{txt}' | Aria: '{aria}'")
            if (aria and "download" in aria.lower()) or "download" in txt.lower():
                print(f"Found download action! Triggering download to {target_video_path}...")
                with page.expect_download(timeout=30000) as download_info:
                    b.click()
                download = download_info.value
                download.save_as(target_video_path)
                print(f"SUCCESS! Video saved to: {target_video_path}")
                break

    if os.path.exists(target_video_path):
        size_mb = os.path.getsize(target_video_path) / (1024 * 1024)
        print(f"VERIFIED: {target_video_path} exists ({round(size_mb, 2)} MB)")

    mgr.close()

if __name__ == "__main__":
    open_video_player_and_download()
