import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.browser.browser_manager import BrowserManager
from app.storage.file_manager import FileManager

def test_download_flow():
    mgr = BrowserManager(headless=True)
    page = mgr.launch()
    
    file_mgr = FileManager()
    job_dir = file_mgr.prepare_job_directory("job_0001")
    target_video_path = os.path.join(job_dir, "video.mp4")
    
    page.goto("https://flow.google.com/project/4c894033-8593-4677-844e-506bc7b67657", wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    
    # Close account panel if open
    close_acc = page.locator("button[aria-label='Close account panel']")
    if close_acc.count() > 0 and close_acc.first.is_visible():
        close_acc.first.click()
        page.wait_for_timeout(500)
        
    # Click 'Videos' tab in left sidebar
    videos_tab = page.get_by_text("Videos")
    if videos_tab.count() > 0 and videos_tab.first.is_visible():
        print("Clicking 'Videos' tab in left navigation...")
        videos_tab.first.click()
        page.wait_for_timeout(2000)
        
    # Hover over the media card
    card = page.locator("div:has(> [style*='background']), [role='gridcell']").first
    card.hover()
    page.wait_for_timeout(1000)
    
    # Take screenshot of hover state
    mgr.capture_debug_screenshot("video_card_hovered")
    
    # Double click the card to open video view
    print("Double clicking card...")
    card.dblclick()
    page.wait_for_timeout(3000)
    
    screenshot = mgr.capture_debug_screenshot("video_modal_view")
    print(f"Video modal screenshot: {screenshot}")
    
    # Check for download button
    dl_btn = page.locator("button[aria-label*='Download'], button:has-text('Download'), [data-testid*='download'], a[download]")
    print(f"Download buttons found: {dl_btn.count()}")
    if dl_btn.count() > 0:
        for i in range(dl_btn.count()):
            btn = dl_btn.nth(i)
            if btn.is_visible():
                print(f"Clicking download button [{i}]...")
                with page.expect_download(timeout=30000) as download_info:
                    btn.click()
                download = download_info.value
                download.save_as(target_video_path)
                print(f"SUCCESS! Video downloaded to: {target_video_path}")
                break

    mgr.close()

if __name__ == "__main__":
    test_download_flow()
