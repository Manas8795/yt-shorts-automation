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
    
    print("Navigating to https://flow.google.com/ ...", flush=True)
    page.goto("https://flow.google.com/", wait_until="networkidle")
    time.sleep(3)
    
    # Scroll down to reveal recent projects
    print("Scrolling down to reveal projects...", flush=True)
    page.mouse.wheel(0, 600)
    time.sleep(2)
    page.screenshot(path=os.path.join(debug_dir, "scrolled_projects.png"))
    
    # Inspect all project links/cards
    print("Searching for project links...", flush=True)
    links = page.locator("a[href*='/project/']").all()
    print(f"Found {len(links)} project links:", flush=True)
    target_link = None
    for idx, l in enumerate(links):
        href = l.get_attribute("href")
        text = l.inner_text().strip().replace("\n", " ")
        print(f"  [{idx}] href={href} | text='{text}'", flush=True)
        if "Sep 05 - 12:53" in text or "12:53" in text:
            target_link = l
            print(f"  -> Matched project: {href}", flush=True)

    if not target_link and len(links) > 0:
        # Check all visible cards
        print("Checking cards without direct text in <a> tag...", flush=True)
        for idx, l in enumerate(links):
            parent_text = l.evaluate("el => el.closest('div').innerText")
            print(f"  [{idx}] Parent text: {parent_text.replace(chr(10), ' ')}", flush=True)
            if "Sep 05 - 12:53" in parent_text or "12:53" in parent_text:
                target_link = l
                break

    if target_link:
        print("Navigating to matched project...", flush=True)
        proj_href = target_link.get_attribute("href")
        if not proj_href.startswith("http"):
            proj_href = "https://flow.google.com" + proj_href
        page.goto(proj_href, wait_until="domcontentloaded")
    else:
        print("Looking for any element with 'Sep 05 - 12:53'...", flush=True)
        el = page.locator("*:has-text('Sep 05 - 12:53')").last
        if el.count() > 0:
            el.click()
            time.sleep(4)
        else:
            print("Fallback: clicking the latest project card at the top...", flush=True)
            if len(links) > 0:
                page.goto("https://flow.google.com" + links[0].get_attribute("href"), wait_until="domcontentloaded")

    print(f"Current Project URL: {page.url}", flush=True)
    time.sleep(4)
    
    print("Reloading project page once to refresh media...", flush=True)
    page.reload(wait_until="domcontentloaded")
    time.sleep(5)
    
    page.screenshot(path=os.path.join(debug_dir, "inside_project.png"))
    print("Inside project screenshot saved.", flush=True)
    
    # Switch to Videos tab if available
    v_tab = page.locator("button:has-text('Videos'), [role='tab']:has-text('Videos')").first
    if v_tab.count() > 0 and v_tab.is_visible():
        print("Switching to Videos tab...", flush=True)
        v_tab.click()
        time.sleep(2)
        page.screenshot(path=os.path.join(debug_dir, "videos_tab.png"))

    # Let's inspect video elements or canvas cards
    print("Looking for video or canvas elements...", flush=True)
    # Click top-left card on canvas
    page.mouse.click(250, 280)
    time.sleep(3)
    page.screenshot(path=os.path.join(debug_dir, "video_modal.png"))
    
    # Check for download button or more_vert menu
    download_btn = page.locator("button:has-text('Download'), button[aria-label*='Download'], [role='button']:has-text('Download')").first
    if download_btn.count() > 0 and download_btn.is_visible():
        print(f"Found download button! Initiating download...", flush=True)
        with page.expect_download(timeout=180000) as dl_info:
            download_btn.click(force=True)
        dl = dl_info.value
        dl.save_as(target_video_path)
        size_mb = round(os.path.getsize(target_video_path) / (1024 * 1024), 2)
        print(f"SUCCESS: Video downloaded to {target_video_path} ({size_mb} MB)", flush=True)
    else:
        # Check more_vert menu
        more_btn = page.locator("button:has-text('more_vert'), button[aria-label*='More options'], button[aria-label*='More']").last
        if more_btn.count() > 0 and more_btn.is_visible():
            print("Opening more_vert options menu...", flush=True)
            more_btn.click()
            time.sleep(1)
            page.screenshot(path=os.path.join(debug_dir, "more_menu.png"))
            menu_dl = page.locator("[role='menuitem']:has-text('Download'), button:has-text('Download')").first
            if menu_dl.count() > 0 and menu_dl.is_visible():
                print("Clicking download in menu...", flush=True)
                with page.expect_download(timeout=180000) as dl_info:
                    menu_dl.click(force=True)
                dl = dl_info.value
                dl.save_as(target_video_path)
                size_mb = round(os.path.getsize(target_video_path) / (1024 * 1024), 2)
                print(f"SUCCESS: Video downloaded via menu to {target_video_path} ({size_mb} MB)", flush=True)
        else:
            print("Could not find download or more options button directly.")

    context.close()
