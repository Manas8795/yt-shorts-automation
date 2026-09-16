import os
import sys
import time
from playwright.sync_api import sync_playwright

profile_dir = r"d:\Temp\yt automation\youtube-automation\browser_profile"
debug_dir = r"d:\Temp\yt automation\youtube-automation\debug"
os.makedirs(debug_dir, exist_ok=True)

out_dir = r"d:\Temp\yt automation\youtube-automation\output\2026-09-05\job_0007_Nissan_Skyline_GT-R_R34_V-Spec_II"
os.makedirs(out_dir, exist_ok=True)
target_video_path = os.path.join(out_dir, "video.mp4")

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
    page.set_viewport_size({"width": 1400, "height": 900})
    
    print("Opening project https://flow.google.com/project/2805fba9-cb0b-4216-a690-8fe4c571cc06 ...", flush=True)
    page.goto("https://flow.google.com/project/2805fba9-cb0b-4216-a690-8fe4c571cc06", wait_until="domcontentloaded")
    time.sleep(4)
    
    print("Reloading page once...", flush=True)
    page.reload(wait_until="domcontentloaded")
    time.sleep(4)
    
    # Click card to open modal if not already opened
    if page.locator("button[aria-label='Download scene']").count() == 0:
        print("Clicking video card on canvas (250, 280)...", flush=True)
        page.mouse.click(250, 280)
        time.sleep(3)
        
    dl_btn = page.locator("button[aria-label='Download scene'], button:has-text('download')").first
    print(f"Target Download Scene Button found: {dl_btn.count() > 0}", flush=True)
    
    if dl_btn.count() > 0:
        print("Clicking 'Download scene' and waiting for download stream (timeout=180s)...", flush=True)
        with page.expect_download(timeout=180000) as dl_info:
            dl_btn.click()
            print("Button clicked. Waiting for file payload from Google Flow...", flush=True)
            
        dl = dl_info.value
        print(f"Download stream received: suggested filename = {dl.suggested_filename}", flush=True)
        dl.save_as(target_video_path)
        size_mb = round(os.path.getsize(target_video_path) / (1024 * 1024), 2)
        print(f"SUCCESS: Video successfully saved to {target_video_path} ({size_mb} MB)", flush=True)
    else:
        print("Download button not found", flush=True)

    context.close()
