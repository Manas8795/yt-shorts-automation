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
    
    # Right-click video card on canvas (x=250, y=280)
    print("Right-clicking video card on canvas...", flush=True)
    page.mouse.click(250, 280, button="right")
    time.sleep(1.5)
    
    # Hover over the Download menu item
    dl_item = page.locator("[role='menuitem']:has-text('Download')").first
    if dl_item.count() == 0:
        dl_item = page.locator("*:has-text('Download')").first
        
    print(f"Hovering on Download menu item...", flush=True)
    dl_item.hover()
    time.sleep(1)
    
    # Look for '720p' or 'Original size' option in submenu
    print("Locating '720p Original size' option...", flush=True)
    target_opt = page.locator("[role='menuitem']:has-text('720p'), [role='menuitem']:has-text('Original size'), *:has-text('720p Original size')").first
    
    if target_opt.count() == 0 or not target_opt.is_visible():
        # Move mouse over dl_item again or click it
        dl_item.click()
        time.sleep(1)
        target_opt = page.locator("[role='menuitem']:has-text('720p'), [role='menuitem']:has-text('Original size'), *:has-text('720p Original size')").first

    print(f"Submenu option found: {target_opt.count() > 0}", flush=True)
    page.screenshot(path=os.path.join(debug_dir, "ready_to_click_720p.png"))
    
    print("Clicking '720p Original size' and waiting for download...", flush=True)
    with page.expect_download(timeout=120000) as dl_info:
        target_opt.click(force=True)
        print("Clicked option. Waiting for download event...", flush=True)
        
    dl = dl_info.value
    print(f"Download event received: {dl.suggested_filename}", flush=True)
    dl.save_as(target_video_path)
    size_mb = round(os.path.getsize(target_video_path) / (1024 * 1024), 2)
    print(f"SUCCESS: Video downloaded to {target_video_path} ({size_mb} MB)", flush=True)

    context.close()
