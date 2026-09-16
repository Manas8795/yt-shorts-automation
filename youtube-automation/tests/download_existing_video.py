import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.browser.browser_manager import BrowserManager
from app.storage.file_manager import FileManager

def download_existing_video():
    mgr = BrowserManager(headless=True)
    page = mgr.launch()
    
    file_mgr = FileManager()
    job_dir = file_mgr.prepare_job_directory("job_0001")
    target_video_path = os.path.join(job_dir, "video.mp4")
    
    # Open the existing project
    page.goto("https://flow.google.com/project/4c894033-8593-4677-844e-506bc7b67657", wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    
    # Find the video tile on the canvas
    video_tile = page.locator("div:has(> [style*='background']), [role='gridcell']").first
    print("Hovering on video tile...")
    video_tile.hover()
    page.wait_for_timeout(1000)
    
    # Check if download button appears on hover or via more_vert
    print("Looking for download button...")
    
    # Right click or click to open context
    video_tile.click(button="right")
    page.wait_for_timeout(1000)
    
    screenshot = mgr.capture_debug_screenshot("context_menu_on_video")
    print(f"Context menu screenshot: {screenshot}")
    
    # Check menu items
    menu_items = page.locator("[role='menuitem'], button")
    for i in range(menu_items.count()):
        item = menu_items.nth(i)
        if item.is_visible():
            txt = item.inner_text().strip()
            print(f"  Menu item [{i}]: {txt}")
            if "Download" in txt:
                print(f"Found Download button! Triggering download to {target_video_path}...")
                with page.expect_download(timeout=30000) as download_info:
                    item.click()
                download = download_info.value
                download.save_as(target_video_path)
                print(f"Successfully downloaded video! Path: {target_video_path}")
                break

    if os.path.exists(target_video_path):
        size_mb = os.path.getsize(target_video_path) / (1024 * 1024)
        print(f"VERIFIED: {target_video_path} exists ({round(size_mb, 2)} MB)")
    else:
        print("Download file not yet on disk, checking video details...")

    mgr.close()

if __name__ == "__main__":
    download_existing_video()
