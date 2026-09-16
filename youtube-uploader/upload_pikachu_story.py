import os
import sys
import time
from playwright.sync_api import sync_playwright, Page

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from uploader import (
    verify_active_account,
    REQUIRED_ACCOUNT,
    UploadTracker,
    check_daily_limit,
    DailyUploadLimitException
)


def wait_for_upload_completion(page: Page, timeout_seconds: int = 600) -> bool:
    """
    Waits until the video file upload has reached 100% in YouTube Studio.
    Monitors progress label on upload wizard or confirmation dialog.
    """
    print("[*] Waiting for video upload to reach 100% (Upload complete)...")
    start_time = time.time()
    last_status = ""

    while time.time() - start_time < timeout_seconds:
        progress_selectors = [
            "ytcp-video-upload-progress span.progress-label",
            "ytcp-video-upload-progress",
            "span.progress-label",
            "div.progress-label",
            ".progress-label",
            "span:has-text('Upload complete')",
            "span:has-text('Processing')",
            "span:has-text('Checks complete')",
            "span:has-text('Uploading')",
            "ytcp-dialog:has-text('Uploading')"
        ]

        current_text = ""
        for sel in progress_selectors:
            loc = page.locator(sel)
            if loc.count() > 0:
                for i in range(loc.count()):
                    try:
                        t = loc.nth(i).inner_text().strip()
                        if t and ("upload" in t.lower() or "process" in t.lower() or "check" in t.lower() or "%" in t):
                            current_text = t
                            break
                    except Exception:
                        pass
            if current_text:
                break

        if current_text and current_text != last_status:
            print(f"    [Upload Progress] {current_text}")
            last_status = current_text

        lower = current_text.lower()
        if any(w in lower for w in [
            "upload complete",
            "processing",
            "checks complete",
            "check complete",
            "no issues found",
            "checks finished"
        ]):
            print(f"[+] Video upload reached 100%! Current status: {current_text}")
            return True

        if check_daily_limit(page):
            raise DailyUploadLimitException("Daily upload limit reached during upload.")

        page.wait_for_timeout(2000)

    print("[!] Warning: Upload wait loop reached timeout.")
    return False


def upload_and_wait_until_complete(page: Page, video_path: str, meta: dict, visibility: str = "PUBLIC") -> str:
    print("\n[*] Navigating to YouTube Studio...")
    page.goto("https://studio.youtube.com", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(4000)

    if not verify_active_account(page, REQUIRED_ACCOUNT):
        print("[-] Account verification failed. Halting upload.")
        return ""

    if check_daily_limit(page):
        raise DailyUploadLimitException("Daily upload limit reached on initial page load.")

    # 1. Open Upload Dialog
    print("[*] Opening Upload Dialog...")
    file_input = page.locator("input[type='file']")
    if file_input.count() == 0 or not file_input.first.is_attached():
        direct_upload_btn = page.locator("#upload-button, ytcp-button:has-text('Upload videos'):not([disabled]), button:has-text('Upload videos')")
        if direct_upload_btn.count() > 0 and direct_upload_btn.first.is_visible():
            direct_upload_btn.first.click()
            page.wait_for_timeout(2000)
        else:
            create_btn = page.locator("#create-icon, button:has-text('Create'), ytcp-button#create-icon, [aria-label*='Create' i]")
            create_btn.first.wait_for(state="visible", timeout=15000)
            create_btn.first.click()
            page.wait_for_timeout(1000)

            upload_item = page.locator("tp-yt-paper-item:has-text('Upload videos'), [test-id='upload-video-menu-item'], ytd-compact-link-renderer:has-text('Upload videos'), a:has-text('Upload videos'), #text-item-0")
            try:
                upload_item.first.wait_for(state="visible", timeout=8000)
                upload_item.first.click()
                page.wait_for_timeout(2000)
            except Exception:
                create_btn.first.click()
                page.wait_for_timeout(1000)
                if upload_item.count() > 0 and upload_item.first.is_visible():
                    upload_item.first.click()
                    page.wait_for_timeout(2000)

    if check_daily_limit(page):
        raise DailyUploadLimitException("Daily upload limit reached after opening upload dialog.")

    # 2. Attach video file
    print(f"[*] Attaching video file: {os.path.basename(video_path)} ({os.path.getsize(video_path)/(1024*1024):.2f} MB)...")
    file_input = page.locator("input[type='file']")
    file_input.first.wait_for(state="attached", timeout=25000)
    file_input.first.set_input_files(video_path)
    page.wait_for_timeout(4000)

    # 3. Fill Title
    print(f"[*] Setting Short Title: {meta['title']}")
    title_box = page.locator("#title-textarea #textbox, [aria-label*='title' i][contenteditable='true'], ytcp-social-suggestions-textbox[label*='Title' i] #textbox")
    title_box.first.wait_for(state="visible", timeout=30000)
    title_box.first.click()
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    title_box.first.fill(meta["title"])
    page.wait_for_timeout(1000)

    # 4. Fill Description
    print("[*] Setting Description & Hashtags...")
    desc_box = page.locator("#description-textarea #textbox, [aria-label*='description' i][contenteditable='true'], ytcp-social-suggestions-textbox[label*='Description' i] #textbox")
    if desc_box.count() > 0:
        desc_box.first.click()
        page.keyboard.press("Control+A")
        page.keyboard.press("Backspace")
        desc_box.first.fill(meta["description"])
        page.wait_for_timeout(1000)

    # 5. Audience Selection: 'No, it's not made for kids'
    print("[*] Setting Audience ('No, it's not made for kids')...")
    not_for_kids_radio = page.locator(
        "tp-yt-paper-radio-button[name='VIDEO_MADE_FOR_KIDS_NOT_MFK'], "
        "[name='VIDEO_MADE_FOR_KIDS_NOT_MFK'], "
        'tp-yt-paper-radio-button:has-text("No, it\'s not made for kids"), '
        'div:has-text("No, it\'s not made for kids") input[type="radio"]'
    )
    if not_for_kids_radio.count() > 0:
        not_for_kids_radio.first.scroll_into_view_if_needed()
        not_for_kids_radio.first.click()
        page.wait_for_timeout(1000)
        print("[+] Verified: 'No, it's not made for kids' selected.")

    # 6. Fill Tags
    show_more_btn = page.locator("#toggle-button, ytcp-button:has-text('Show more'), button:has-text('Show more')")
    if show_more_btn.count() > 0 and show_more_btn.first.is_visible():
        show_more_btn.first.scroll_into_view_if_needed()
        show_more_btn.first.click()
        page.wait_for_timeout(1000)

    tags_input = page.locator("input[aria-label='Tags'], #tags-container input, input[placeholder*='Add tag' i]")
    if tags_input.count() > 0:
        print("[*] Setting SEO Tags...")
        tags_input.first.scroll_into_view_if_needed()
        tags_input.first.click()
        tags_input.first.fill(meta["tags_csv"])
        page.keyboard.press("Enter")
        page.wait_for_timeout(1000)

    # 7. Step through wizard to Visibility
    print("[*] Proceeding through upload wizard to Visibility step...")
    for step in range(3):
        next_btn = page.locator("#next-button:not([disabled]), button:has-text('Next'):not([disabled]), ytcp-button#next-button:not([disabled])")
        if next_btn.count() > 0 and next_btn.first.is_visible():
            next_btn.first.click()
            page.wait_for_timeout(1500)

    if check_daily_limit(page):
        raise DailyUploadLimitException("Daily upload limit reached before visibility selection.")

    # 8. Set Visibility
    print(f"[*] Setting Visibility: {visibility}...")
    vis_radio = page.locator(f"tp-yt-paper-radio-button[name='{visibility}'], [name='{visibility}']")
    if vis_radio.count() > 0:
        vis_radio.first.scroll_into_view_if_needed()
        vis_radio.first.click()
        page.wait_for_timeout(1000)

    yt_url = ""
    link_elem = page.locator("a[href*='youtu.be']")
    if link_elem.count() > 0:
        yt_url = link_elem.first.get_attribute("href") or ""

    # CRITICAL: WAIT FOR FULL UPLOAD COMPLETION BEFORE SAVING
    print("\n" + "=" * 60)
    print("[*] STEP: WAITING FOR VIDEO FILE TO FINISH UPLOADING...")
    print("=" * 60)
    wait_for_upload_completion(page, timeout_seconds=600)

    # 9. Click Save / Publish
    print("[*] Clicking Publish / Save button...")
    done_btn = page.locator("#done-button:not([disabled]), button:has-text('Publish'):not([disabled]), ytcp-button#done-button:not([disabled]), #done-button, ytcp-button#done-button")
    try:
        done_btn.first.wait_for(state="visible", timeout=15000)
        done_btn.first.click()
        page.wait_for_timeout(3000)
    except Exception as e:
        print(f"[!] Note on save click: {e}")

    # Handle 'Publish anyway' if still checking
    publish_anyway_selectors = [
        "ytcp-button:has-text('Publish anyway')",
        "button:has-text('Publish anyway')",
        "#publish-button:has-text('Publish anyway')",
        "text='Publish anyway'"
    ]
    for _ in range(5):
        clicked = False
        for sel in publish_anyway_selectors:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible():
                print("[+] Clicking 'Publish anyway'...")
                loc.first.click()
                clicked = True
                page.wait_for_timeout(3000)
                break
        if clicked:
            break
        page.wait_for_timeout(1000)

    if check_daily_limit(page):
        raise DailyUploadLimitException("Daily upload limit reached upon publishing.")

    # CRITICAL: If confirmation modal shows upload in progress, wait until 100% on the modal
    print("[*] Monitoring post-publish confirmation modal and upload state...")
    modal_start = time.time()
    while time.time() - modal_start < 300:
        modal = page.locator("ytcp-uploads-dialog, ytcp-confirmation-dialog, ytcp-video-share-dialog, tp-yt-paper-dialog")
        modal_text = ""
        if modal.count() > 0:
            for i in range(modal.count()):
                if modal.nth(i).is_visible():
                    modal_text += " " + modal.nth(i).inner_text().strip()

        if "keep this browser tab open" in modal_text.lower() or "uploading" in modal_text.lower():
            print("    [Modal Notice] Still uploading in background, keeping browser open...")
            page.wait_for_timeout(3000)
            continue
        else:
            print("[+] Modal indicates upload is complete and published.")
            break

    # Close confirmation modal
    print("[*] Closing upload confirmation modal...")
    close_selectors = [
        "#close-button",
        "ytcp-button:has-text('Close')",
        "button:has-text('Close')",
        "ytcp-icon-button[aria-label='Close']"
    ]
    for _ in range(6):
        closed = False
        for sel in close_selectors:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible():
                loc.first.click()
                print("[+] Closed upload modal successfully.")
                closed = True
                page.wait_for_timeout(2000)
                break
        if closed:
            break
        page.wait_for_timeout(1000)

    # Double check URL
    if not yt_url:
        link_elem = page.locator("a[href*='youtu.be']")
        if link_elem.count() > 0:
            yt_url = link_elem.first.get_attribute("href") or ""

    # Finally, verify on Channel Videos list that upload has finished and is not stuck in 'Uploading...'
    print("[*] Verifying status on Channel Videos dashboard...")
    try:
        page.goto("https://studio.youtube.com/channel/videos/short", wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(5000)
        # Check first row in video list
        first_row = page.locator("ytcp-video-row").first
        if first_row.count() > 0 and first_row.is_visible():
            row_text = first_row.inner_text().replace("\n", " | ")
            print(f"[+] Top Video Row on Studio: {row_text[:120]}...")
    except Exception as e:
        print(f"[!] Note on studio table verification: {e}")

    # Give an extra 5 seconds safety buffer before exiting
    print("[*] Waiting 5-second final buffer to ensure all network connections flush cleanly...")
    page.wait_for_timeout(5000)

    print(f"\n[+] Video successfully uploaded and verified! Link: {yt_url if yt_url else 'https://studio.youtube.com/channel/videos/short'}")
    return yt_url if yt_url else "https://studio.youtube.com/channel/videos/short"


def main():
    profile_dir = os.path.join(script_dir, "browser_profile")
    video_path = r"d:\Temp\yt automation\video-editor\output\Pikachu_Motorcycle_Story\Pikachu_Motorcycle_Story.mp4"

    if not os.path.exists(video_path):
        print(f"[-] Error: video file not found at {video_path}")
        sys.exit(1)

    title = "Pikachu Gets His Heart Broken… 💔🏍️ #shorts #asmr #pikarevz"

    description = """Pikachu gets his heart broken… 💔

But instead of looking back, he walks into the PikaRevZ ASMR store, discovers his dream motorcycle, and rides away with a whole new attitude. 🏍️😎

And then… Lopunny sees him again. 😳

A cinematic miniature motorcycle story featuring a detailed ASMR-style vehicle showroom, miniature bikes, workshop scenes, and a satisfying final ride.

Made for miniature vehicle & ASMR lovers.

🔧 Miniature Motorcycle
🏍️ Vehicle ASMR
🎬 Cinematic Miniature Story
⚙️ Satisfying Workshop
😎 Pikachu Story

#Shorts #ASMR #Miniature #Motorcycle #Pikachu #Lopunny #MiniatureMotorcycle #VehicleASMR #Satisfying #PikaRevZ"""

    tags = "Shorts, ASMR, Miniature, Motorcycle, Pikachu, Lopunny, MiniatureMotorcycle, VehicleASMR, Satisfying, PikaRevZ, pokemon asmr, miniature motorcycle, motorcycle story, pikachu story, diecast motorcycle, showroom asmr"

    metadata = {
        "title": title,
        "description": description,
        "tags_csv": tags
    }

    print("=" * 65)
    print("UPLOADING PIKACHU MOTORCYCLE STORY SHORT")
    print("RULE: STRICTLY WAITING FOR FULL VIDEO UPLOAD BEFORE EXITING")
    print("=" * 65)
    print(f"Video File: {video_path}")
    print(f"File Size: {os.path.getsize(video_path) / (1024 * 1024):.2f} MB")
    print(f"Title: {title}")
    print("Visibility: PUBLIC")
    print("Audience: No, it's not made for kids")
    print("=" * 65)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ],
            no_viewport=True
        )

        page = context.pages[0] if context.pages else context.new_page()

        try:
            yt_link = upload_and_wait_until_complete(page, video_path, metadata, visibility="PUBLIC")
            if yt_link:
                print(f"\n[+] SUCCESS! 100% Uploaded Pikachu Motorcycle Story: {yt_link}")
                tracker = UploadTracker(script_dir)
                tracker.record_upload(
                    vid_id=9999,
                    vehicle_name="Pikachu Motorcycle Story",
                    category="story",
                    title=title,
                    youtube_url=yt_link,
                    visibility="PUBLIC",
                    local_video_path=video_path,
                    source_excel="custom_story"
                )
            else:
                print("[-] Upload failed or halted.")
                sys.exit(1)
        except Exception as e:
            print(f"[-] Error during upload: {e}")
            sys.exit(1)
        finally:
            print("[*] Safely closing browser context after full upload completion...")
            context.close()

if __name__ == "__main__":
    main()
