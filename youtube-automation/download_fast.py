import os
import sys
import time
import urllib.request
from playwright.sync_api import sync_playwright

profile_dir = r"d:\Temp\yt automation\youtube-automation\browser_profile"
debug_dir = r"d:\Temp\yt automation\youtube-automation\debug"
os.makedirs(debug_dir, exist_ok=True)

out_dir = r"d:\Temp\yt automation\youtube-automation\output\2026-09-05\job_0007_Nissan_Skyline_GT-R_R34_V-Spec_II"
os.makedirs(out_dir, exist_ok=True)
target_video_path = os.path.join(out_dir, "video.mp4")

captured_video_urls = []

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

    def handle_response(response):
        try:
            url = response.url
            ct = response.headers.get("content-type", "")
            if "video" in ct or ".mp4" in url or "googlevideo" in url or "video" in url.lower():
                print(f"[NETWORK VIDEO DETECTED] Content-Type={ct} URL={url[:120]}...", flush=True)
                captured_video_urls.append(url)
                if ("video/mp4" in ct or ".mp4" in url) and not os.path.exists(target_video_path):
                    try:
                        body = response.body()
                        if len(body) > 100000: # at least 100KB
                            with open(target_video_path, "wb") as f:
                                f.write(body)
                            print(f"[SAVED FROM NETWORK] {target_video_path} ({len(body)} bytes)", flush=True)
                    except Exception as ex:
                        print(f"Error saving network body: {ex}", flush=True)
        except Exception:
            pass

    page.on("response", handle_response)
    
    print("Navigating to project https://flow.google.com/project/2805fba9-cb0b-4216-a690-8fe4c571cc06 ...", flush=True)
    page.goto("https://flow.google.com/project/2805fba9-cb0b-4216-a690-8fe4c571cc06", wait_until="domcontentloaded")
    time.sleep(4)
    
    print("Reloading page once...", flush=True)
    page.reload(wait_until="domcontentloaded")
    time.sleep(4)
    
    # Right-click video card on canvas (x=250, y=280)
    print("Right-clicking video card on canvas...", flush=True)
    page.mouse.click(250, 280, button="right")
    time.sleep(1.5)
    
    # Hover over Download item (at x=250, y=550)
    print("Hovering on Download menu item...", flush=True)
    dl_item = page.locator("div[role='menuitem']:has-text('Download'), [role='menuitem']:has-text('Download')").first
    if dl_item.count() > 0:
        box = dl_item.bounding_box()
        if box:
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            time.sleep(1)
            # Move slightly right into the submenu
            page.mouse.move(box["x"] + box["width"] + 50, box["y"] + box["height"] / 2)
            time.sleep(1)

    page.screenshot(path=os.path.join(debug_dir, "after_hover_sub.png"))
    
    # Click 720p Original size
    print("Clicking '720p Original size'...", flush=True)
    # Option 1: click text '720p'
    opt = page.locator("text='720p'").first
    if opt.count() > 0 and opt.is_visible():
        print("Clicking '720p' text locator...", flush=True)
        try:
            with page.expect_download(timeout=10000) as dl_info:
                opt.click()
            dl = dl_info.value
            dl.save_as(target_video_path)
            print(f"Download completed via Playwright: {target_video_path}", flush=True)
        except Exception as e:
            print(f"Playwright download event note: {e}", flush=True)
    else:
        # Click by exact coordinate x=350, y=615
        print("Clicking at coordinate (350, 615)...", flush=True)
        try:
            with page.expect_download(timeout=10000) as dl_info:
                page.mouse.click(350, 615)
            dl = dl_info.value
            dl.save_as(target_video_path)
            print(f"Download completed via coordinate click: {target_video_path}", flush=True)
        except Exception as e:
            print(f"Coordinate download event note: {e}", flush=True)

    # Give time for network download / save
    time.sleep(5)
    
    # Check if file was saved
    if not os.path.exists(target_video_path) and captured_video_urls:
        print(f"Attempting direct urllib download from captured URLs ({len(captured_video_urls)})...", flush=True)
        for u in reversed(captured_video_urls):
            try:
                print(f"Downloading from {u[:80]}...", flush=True)
                urllib.request.urlretrieve(u, target_video_path)
                if os.path.getsize(target_video_path) > 100000:
                    print("Direct URL retrieval succeeded!", flush=True)
                    break
            except Exception as ex:
                print(f"URL retrieve error: {ex}", flush=True)

    # Check Downloads folder as well
    downloads_dir = os.path.expanduser(r"~\Downloads")
    for fname in os.listdir(downloads_dir):
        if fname.endswith(".mp4") and ("Nissan" in fname or "Unboxing" in fname or "Sep" in fname):
            fpath = os.path.join(downloads_dir, fname)
            if time.time() - os.path.getmtime(fpath) < 120:
                print(f"Found recently downloaded file in Downloads: {fpath}", flush=True)
                import shutil
                shutil.copy2(fpath, target_video_path)
                break

    if os.path.exists(target_video_path):
        size_mb = round(os.path.getsize(target_video_path) / (1024 * 1024), 2)
        print(f"FINAL SUCCESS: {target_video_path} saved ({size_mb} MB)!", flush=True)
    else:
        print("ERROR: Target video could not be saved.", flush=True)

    context.close()
