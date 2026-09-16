import os
import sys
import time
from playwright.sync_api import sync_playwright

project_url = "https://flow.google.com/project/2805fba9-cb0b-4216-a690-8fe4c571cc06"
out_dir = r"d:\Temp\yt automation\youtube-automation\output\2026-09-05\job_0007_Nissan_Skyline_GT-R_R34_V-Spec_II"
os.makedirs(out_dir, exist_ok=True)
target_video_path = os.path.join(out_dir, "video.mp4")
profile_dir = r"d:\Temp\yt automation\youtube-automation\browser_profile"

print(f"Connecting to browser and opening {project_url}...", flush=True)

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
    
    print("Reloading page once...", flush=True)
    page.reload(wait_until="domcontentloaded")
    time.sleep(4)

    # Click video card on canvas (top-left card at 250, 280)
    print("Clicking video card on canvas...", flush=True)
    page.mouse.click(250, 280)
    time.sleep(3)

    # Save screenshot of opened modal
    debug_dir = r"d:\Temp\yt automation\youtube-automation\debug"
    modal_screen = os.path.join(debug_dir, "modal_opened_now.png")
    page.screenshot(path=modal_screen)
    print(f"Modal screenshot saved: {modal_screen}", flush=True)

    # Inspect all visible buttons
    buttons = page.locator("button, [role='button']")
    btn_count = buttons.count()
    print(f"Found {btn_count} buttons on screen:", flush=True)
    download_btn = None
    for i in range(btn_count):
        try:
            b = buttons.nth(i)
            if b.is_visible():
                txt = b.inner_text().strip().replace("\n", " ")
                aria = b.get_attribute("aria-label") or ""
                if "download" in txt.lower() or "download" in aria.lower():
                    print(f"  -> Found Download Button: text='{txt}', aria-label='{aria}'", flush=True)
                    download_btn = b
        except Exception:
            pass

    if download_btn:
        print("Clicking download button...", flush=True)
        with page.expect_download(timeout=180000) as download_info:
            download_btn.click(force=True)
        
        download = download_info.value
        download.save_as(target_video_path)
        size_mb = round(os.path.getsize(target_video_path) / (1024 * 1024), 2)
        print(f"SUCCESS: Video downloaded successfully to {target_video_path} ({size_mb} MB)", flush=True)
    else:
        # Check more_vert menu
        more_btn = page.locator("button:has-text('more_vert'), button[aria-label*='More']").last
        if more_btn.count() > 0 and more_btn.is_visible():
            print("Opening more_vert menu...", flush=True)
            more_btn.click()
            time.sleep(1)
            menu_dl = page.locator("[role='menuitem']:has-text('Download'), button:has-text('Download')").first
            if menu_dl.count() > 0 and menu_dl.is_visible():
                print("Clicking download in menu...", flush=True)
                with page.expect_download(timeout=180000) as download_info:
                    menu_dl.click(force=True)
                download = download_info.value
                download.save_as(target_video_path)
                size_mb = round(os.path.getsize(target_video_path) / (1024 * 1024), 2)
                print(f"SUCCESS: Video downloaded via menu to {target_video_path} ({size_mb} MB)", flush=True)

    context.close()
