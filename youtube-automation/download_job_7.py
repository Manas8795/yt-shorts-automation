import os
import sys
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

project_url = "https://flow.google.com/project/2805fba9-cb0b-4216-a690-8fe4c571cc06"
out_dir = r"d:\Temp\yt automation\youtube-automation\output\2026-09-05\job_0007_Nissan_Skyline_GT-R_R34_V-Spec_II"
os.makedirs(out_dir, exist_ok=True)
target_video_path = os.path.join(out_dir, "video.mp4")

profile_dir = r"d:\Temp\yt automation\youtube-automation\browser_profile"

print(f"Connecting to browser profile and navigating to project: {project_url}")

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=profile_dir,
        headless=False,
        channel="chrome",
        accept_downloads=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--no-first-run",
            "--disable-session-crashed-bubble",
            "--disable-restore-session-state"
        ]
    )
    
    page = context.pages[0] if context.pages else context.new_page()
    page.goto(project_url, wait_until="domcontentloaded")
    time.sleep(3)
    
    print("Reloading page once to refresh media assets...")
    page.reload(wait_until="domcontentloaded")
    time.sleep(4)
    
    # Dismiss any popups
    popups = page.locator("button:has-text('Got it'), button:has-text('Dismiss'), button:has-text('Close')")
    for i in range(popups.count()):
        try:
            if popups.nth(i).is_visible():
                popups.nth(i).click()
        except Exception:
            pass

    # Step 1: Click Videos tab on the left sidebar
    print("Switching to 'Videos' tab in the left sidebar...")
    videos_tab = page.locator("button:has-text('Videos'), [aria-label*='Videos' i], div:has-text('Videos'), span:has-text('videocam')")
    if videos_tab.count() > 0 and videos_tab.first.is_visible():
        try:
            videos_tab.first.click()
            time.sleep(2)
        except Exception as e:
            print(f"Videos tab click: {e}")

    # Take screenshot of canvas
    debug_dir = r"d:\Temp\yt automation\youtube-automation\debug"
    os.makedirs(debug_dir, exist_ok=True)
    screenshot_path = os.path.join(debug_dir, "download_attempt_view.png")
    page.screenshot(path=screenshot_path)
    print(f"Screenshot saved to {screenshot_path}")

    # Step 2: Locate video container / card
    print("Locating video card on canvas...")
    vid_box = page.locator(
        "div.video-container.clickable, "
        "div:has(> img.video-thumbnail), "
        "div:has(span:has-text('videocam')), "
        "[aria-label*='video' i], "
        "div.video-card, "
        "video, "
        "div:has(> img)"
    ).first

    if vid_box.count() > 0 and vid_box.is_visible():
        print("Clicking video card to open player modal...")
        vid_box.click(force=True)
        time.sleep(3)
    else:
        print("Clicking canvas coordinates (250, 280)...")
        page.mouse.click(250, 280)
        time.sleep(3)

    # Step 3: Click download in modal
    print("Locating download button...")
    download_btn = page.locator(
        "button[aria-label='Download scene'], "
        "[aria-label='Download scene'], "
        "button[aria-label*='Download video' i], "
        "button[aria-label*='Download' i], "
        "button:has-text('download')"
    ).first

    if download_btn.count() == 0 or not download_btn.is_visible():
        more_btn = page.locator("button[aria-label*='More'], button:has-text('more_vert')").first
        if more_btn.count() > 0 and more_btn.is_visible():
            more_btn.click()
            time.sleep(1)
            download_btn = page.locator("[role='menuitem']:has-text('Download'), button:has-text('Download')").first

    if download_btn.count() > 0 and download_btn.is_visible():
        print("Triggering download...")
        with page.expect_download(timeout=120000) as download_info:
            download_btn.click(force=True)

        download = download_info.value
        download.save_as(target_video_path)
        size_mb = round(os.path.getsize(target_video_path) / (1024 * 1024), 2)
        print(f"SUCCESS: Video downloaded to {target_video_path} ({size_mb} MB)")
    else:
        print("Download button not found in modal, taking debug screenshot...")
        page.screenshot(path=os.path.join(debug_dir, "modal_debug.png"))

    context.close()
