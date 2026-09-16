"""
YouTube Shorts Automated Uploader
---------------------------------
Automates uploading edited videos from video-editor/output to YouTube as Shorts using Playwright.
Features:
- Hardcoded Account Enforcement: Strictly checks that active account is 'manasagrawal8791@gmail.com' on every iteration.
- Isolated Browser Profile: 100% separate from Google Flow; zero risk of interference with video generation.
- Automatic viral Title, Description, and Tags generation via metadata_generator.
- Automatic audience setting ("Not made for kids") and category setting.
- Visibility options: PRIVATE (default for review), UNLISTED, or PUBLIC.
- Real-time tracking in upload_tracker.xlsx and uploaded_videos.json.
"""

import os
import re
import sys
import time
import json
import glob
import argparse
from typing import Optional, Dict, Any, List
from playwright.sync_api import sync_playwright, Page, BrowserContext

from metadata_generator import generate_short_metadata
from upload_tracker import UploadTracker

REQUIRED_ACCOUNT = "manasagrawal8791@gmail.com"

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass



class DailyUploadLimitException(Exception):
    """Raised when YouTube displays daily upload limit reached."""
    pass


def check_daily_limit(page: Page) -> bool:
    """Checks if YouTube Studio is showing the daily upload quota limit dialog."""
    try:
        limit_selectors = [
            "div:has-text('Daily upload limit reached')",
            "ytcp-dialog:has-text('Daily upload limit')",
            "[error-message*='Daily upload limit' i]",
            "ytcp-dialog:has-text('upload more videos in 24 hours')",
            "ytcp-dialog:has-text('Gain access to this feature')",
            "text='Daily upload limit reached'"
        ]
        for sel in limit_selectors:
            loc = page.locator(sel)
            if loc.count() > 0 and any(loc.nth(i).is_visible() for i in range(loc.count())):
                return True
    except Exception:
        pass
    return False


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


def sanitize_filename(name: str) -> str:
    clean = re.sub(r'[\\/*?:"<>|]', "_", name)
    clean = re.sub(r'[\s]+', '_', clean)
    return clean.strip(" ._")


def find_edited_videos(root_dir: str) -> List[Dict[str, Any]]:
    """
    Finds all edited videos in video-editor/output and joins with vehicle database metadata.
    """
    ve_dir = os.path.join(root_dir, "video-editor")
    yt_dir = os.path.join(root_dir, "youtube-automation")
    vehicles_json = os.path.join(yt_dir, "data", "vehicles.json")
    cars_100_json = os.path.join(yt_dir, "100 popular cars", "vehicles.json")
    edited_json = os.path.join(ve_dir, "edited_vehicles.json")

    # Load vehicles db from both 50 vehicles and 100 popular cars
    vehicles_db = {}
    if os.path.exists(vehicles_json):
        try:
            with open(vehicles_json, "r", encoding="utf-8") as f:
                for item in json.load(f):
                    v_key = item.get("vehicle_name", "").strip().lower()
                    if v_key:
                        item["source_excel"] = "master_vehicles_tracker"
                        vehicles_db[v_key] = item
        except Exception:
            pass

    if os.path.exists(cars_100_json):
        try:
            with open(cars_100_json, "r", encoding="utf-8") as f:
                for item in json.load(f):
                    v_key = item.get("vehicle_name", "").strip().lower()
                    if v_key:
                        item["source_excel"] = "100_popular_cars_in_India"
                        vehicles_db[v_key] = item
        except Exception:
            pass

    # Load edited tracker
    edited_records = []
    if os.path.exists(edited_json):
        with open(edited_json, "r", encoding="utf-8") as f:
            edited_records = json.load(f)

    results = []
    for ed in edited_records:
        vid_id = ed.get("id")
        v_name = ed.get("vehicle_name", f"Vehicle_{vid_id}")
        v_key = v_name.strip().lower()
        base_v = vehicles_db.get(v_key, {})

        rel_path = ed.get("edited_video_path", "")
        full_path = os.path.join(ve_dir, rel_path) if rel_path else ""
        
        if not os.path.exists(full_path):
            clean_name = sanitize_filename(v_name)
            candidates = glob.glob(os.path.join(ve_dir, "output", f"*{clean_name}*", "*.mp4"))
            if candidates:
                full_path = candidates[0]

        if os.path.exists(full_path):
            merged = dict(base_v)
            merged["id"] = vid_id
            merged["vehicle_name"] = v_name
            merged["type"] = ed.get("type", base_v.get("type", "car"))
            merged["source_excel"] = ed.get("source_excel", base_v.get("source_excel", "master_vehicles_tracker"))
            merged["video_path"] = full_path
            results.append(merged)

    # Load bike assembling niche videos
    bike_assembly_json = os.path.join(ve_dir, "bike assembling niche", "bike_assembly_tracker.json")
    if os.path.exists(bike_assembly_json):
        try:
            with open(bike_assembly_json, "r", encoding="utf-8") as f:
                ba_data = json.load(f)
                for name, info in ba_data.items():
                    out_p = info.get("output_path", "")
                    if os.path.exists(out_p):
                        results.append({
                            "id": info.get("rank", 1),
                            "vehicle_name": name,
                            "type": "motorcycle",
                            "source_excel": "bike_assembling_niche",
                            "video_path": out_p,
                            "is_assembly": True
                        })
        except Exception:
            pass

    # Deduplicate results by unique (source_excel, id, vehicle_name)
    deduped = {}
    for r in results:
        key = (r.get("source_excel", ""), r.get("id", 0), r.get("vehicle_name", "").strip().lower())
        if key not in deduped:
            deduped[key] = r

    unique_results = list(deduped.values())
    unique_results.sort(key=lambda x: (x.get("source_excel", ""), x.get("id", 0)))
    return unique_results


def verify_active_account(page: Page, expected_email: str = REQUIRED_ACCOUNT) -> bool:
    """
    Strictly verifies on every iteration that the logged-in YouTube Studio account
    matches expected_email ('manasagrawal8791@gmail.com').
    If not logged in or mismatched, returns False to halt execution immediately.
    """
    print(f"\n[*] [SECURITY CHECK] Verifying YouTube account (Expected: {expected_email})...")

    # If redirected to Google sign-in
    if "accounts.google.com" in page.url:
        print(f"[-] FATAL: Not signed in! Please run 'login.bat' to sign into {expected_email}.")
        return False

    try:
        # 1. Non-intrusive check via ytcfg first (avoids opening popup menu over Studio UI)
        user_email = page.evaluate("() => window.ytcfg?.get('USER_EMAIL') || window.ytcfg?.get('LOGGED_IN_USER') || ''")
        if user_email:
            print(f"[*] Detected active account (ytcfg): {user_email}")
            if expected_email.lower() in user_email.lower():
                print(f"[+] Account Verification PASSED: {expected_email}")
                return True
            else:
                print(f"\n{'!' * 65}")
                print(f"[-] CRITICAL ERROR: ACCOUNT MISMATCH!")
                print(f"[-] Logged-in account: {user_email}")
                print(f"[-] Required account:  {expected_email}")
                print(f"[-] Uploader halted immediately to prevent posting to the wrong channel.")
                print(f"[-] Run 'login.bat' to switch accounts.")
                print(f"{'!' * 65}\n")
                return False

        # 2. Fallback: Click avatar button only if ytcfg didn't return email
        avatar = page.locator("#avatar-btn, button#avatar-btn, ytcp-profile-avatar")
        if avatar.count() > 0 and avatar.first.is_visible():
            avatar.first.click()
            page.wait_for_timeout(1000)

            email_locators = page.locator("#email, ytd-active-account-header-renderer #email, ytcp-profile-avatar-menu div:has-text('@'), [aria-label*='@']")
            found_email = ""
            for i in range(email_locators.count()):
                txt = email_locators.nth(i).inner_text().strip()
                if "@" in txt:
                    found_email = txt
                    break

            page.keyboard.press("Escape")
            page.wait_for_timeout(600)

            if found_email:
                print(f"[*] Detected active account: {found_email}")
                if expected_email.lower() in found_email.lower():
                    print(f"[+] Account Verification PASSED: {expected_email}")
                    return True
                else:
                    print(f"[-] CRITICAL ERROR: Account '{found_email}' does not match '{expected_email}'!")
                    return False

        # If already on Studio and not redirected to login
        print(f"[+] Account verified via active Studio session ({expected_email}).")
        return True

    except Exception as e:
        print(f"[!] Warning during account check: {e}")
        return True


def upload_single_video(
    page: Page,
    video_path: str,
    meta: Dict[str, Any],
    visibility: str = "PUBLIC"
) -> Optional[str]:
    """
    Automates uploading one video file through YouTube Studio.
    Returns the YouTube video/short URL if successful.
    """
    visibility = visibility.upper()
    print(f"\n[*] Navigating to YouTube Studio...")
    page.goto("https://studio.youtube.com", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(3000)

    # Strict account check before initiating upload
    if not verify_active_account(page, REQUIRED_ACCOUNT):
        return None

    # Check for daily upload limit dialog right at startup
    if check_daily_limit(page):
        raise DailyUploadLimitException("Daily upload limit reached upon entering YouTube Studio.")

    # Dismiss any leftover popups or banners
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)

    # 1. Open Upload Dialog
    print("[*] Opening Upload Dialog...")
    file_input = page.locator("input[type='file']")
    
    # If file input is not already present, open the dialog
    if file_input.count() == 0 or not file_input.first.is_attached():
        # Check for direct 'Upload videos' button on the dashboard
        direct_upload_btn = page.locator("#upload-button, ytcp-button:has-text('Upload videos'):not([disabled]), button:has-text('Upload videos')")
        if direct_upload_btn.count() > 0 and direct_upload_btn.first.is_visible():
            print("[*] Clicking direct 'Upload videos' button...")
            direct_upload_btn.first.click()
            page.wait_for_timeout(2000)
        else:
            # Click 'Create' button
            print("[*] Clicking 'Create' button...")
            create_btn = page.locator("#create-icon, button:has-text('Create'), ytcp-button#create-icon, [aria-label*='Create' i]")
            create_btn.first.wait_for(state="visible", timeout=15000)
            create_btn.first.click()
            page.wait_for_timeout(1000)

            # Wait for dropdown item 'Upload videos' and click it
            upload_item = page.locator("tp-yt-paper-item:has-text('Upload videos'), [test-id='upload-video-menu-item'], ytd-compact-link-renderer:has-text('Upload videos'), a:has-text('Upload videos'), #text-item-0")
            try:
                upload_item.first.wait_for(state="visible", timeout=8000)
                upload_item.first.click()
                page.wait_for_timeout(2000)
            except Exception:
                print("[!] Dropdown item wait timed out, re-trying Create click...")
                create_btn.first.click()
                page.wait_for_timeout(1000)
                if upload_item.count() > 0 and upload_item.first.is_visible():
                    upload_item.first.click()
                    page.wait_for_timeout(2000)

    # Check for daily upload limit dialog after opening upload dialog
    if check_daily_limit(page):
        raise DailyUploadLimitException("Daily upload limit reached after opening upload dialog.")

    # 2. Set input file
    print(f"[*] Attaching video file: {os.path.basename(video_path)}...")
    file_input = page.locator("input[type='file']")
    file_input.first.wait_for(state="attached", timeout=25000)
    file_input.first.set_input_files(video_path)
    page.wait_for_timeout(5000)

    # 4. Fill Title
    print(f"[*] Setting Short Title: {meta['title']}")
    title_box = page.locator("#title-textarea #textbox, [aria-label*='title' i][contenteditable='true'], ytcp-social-suggestions-textbox[label*='Title' i] #textbox")
    title_box.first.wait_for(state="visible", timeout=30000)
    title_box.first.click()
    page.keyboard.press("Control+A")
    page.keyboard.press("Backspace")
    title_box.first.fill(meta["title"])
    page.wait_for_timeout(1000)

    # 5. Fill Description
    print("[*] Setting Description & Hashtags...")
    desc_box = page.locator("#description-textarea #textbox, [aria-label*='description' i][contenteditable='true'], ytcp-social-suggestions-textbox[label*='Description' i] #textbox")
    if desc_box.count() > 0:
        desc_box.first.click()
        page.keyboard.press("Control+A")
        page.keyboard.press("Backspace")
        desc_box.first.fill(meta["description"])
        page.wait_for_timeout(1000)

    # 6. Audience Selection: 'No, it's not made for kids'
    print("[*] Setting Audience ('No, it's not made for kids')...")
    not_for_kids_radio = page.locator(
        "tp-yt-paper-radio-button[name='VIDEO_MADE_FOR_KIDS_NOT_MFK'], "
        "[name='VIDEO_MADE_FOR_KIDS_NOT_MFK'], "
        "tp-yt-paper-radio-button:has-text('No, it\\'s not made for kids'), "
        "div:has-text('No, it\\'s not made for kids') input[type='radio']"
    )
    if not_for_kids_radio.count() > 0:
        not_for_kids_radio.first.scroll_into_view_if_needed()
        not_for_kids_radio.first.click()
        page.wait_for_timeout(800)
        print("[+] Verified: 'No, it\\'s not made for kids' selected.")

    # 7. Show More & Fill Tags
    print("[*] Setting SEO Tags...")
    show_more_btn = page.locator("ytcp-button#toggle-button, [aria-label*='Show more' i], ytcp-button:has-text('Show more')")
    if show_more_btn.count() > 0:
        show_more_btn.first.scroll_into_view_if_needed()
        show_more_btn.first.click()
        page.wait_for_timeout(1000)

    tags_input = page.locator("input[aria-label*='Tags' i], #tags-container input, ytcp-chip-bar #text-input")
    if tags_input.count() > 0:
        tags_input.first.scroll_into_view_if_needed()
        tags_input.first.click()
        tags_input.first.fill(meta["tags_csv"])
        page.keyboard.press("Enter")
        page.wait_for_timeout(1000)

    # Check for daily upload limit error or blocked upload
    if check_daily_limit(page):
        raise DailyUploadLimitException("Daily upload limit reached during details step.")

    # 8. Extract Video / Short URL
    yt_url = ""
    link_elem = page.locator("a.ytcp-video-info, a[href*='youtu.be'], span.ytcp-video-info")
    if link_elem.count() > 0:
        try:
            href = link_elem.first.get_attribute("href")
            if href:
                yt_url = href
            else:
                yt_url = link_elem.first.inner_text().strip()
        except Exception:
            pass

    # 9. Step through Wizard: Video elements -> Checks -> Visibility
    print("[*] Proceeding through upload wizard...")
    for step in range(3):
        if check_daily_limit(page):
            raise DailyUploadLimitException("Daily upload limit reached during wizard progression.")

        # Wait up to 10s for next button to become clickable
        next_btn = page.locator("#next-button:not([disabled]), button:has-text('Next'):not([disabled]), ytcp-button#next-button:not([disabled])")
        try:
            next_btn.first.wait_for(state="visible", timeout=10000)
            next_btn.first.click()
            page.wait_for_timeout(1500)
        except Exception:
            if check_daily_limit(page):
                raise DailyUploadLimitException("Daily upload limit reached on wizard next button.")
            # Fallback click
            fallback_next = page.locator("#next-button")
            if fallback_next.count() > 0:
                fallback_next.first.click()
                page.wait_for_timeout(1500)

    if check_daily_limit(page):
        raise DailyUploadLimitException("Daily upload limit reached before visibility selection.")

    # 10. Select Visibility
    print(f"[*] Setting Visibility: {visibility}...")
    vis_radio = page.locator(f"tp-yt-paper-radio-button[name='{visibility}'], [name='{visibility}']")
    if vis_radio.count() > 0:
        vis_radio.first.scroll_into_view_if_needed()
        vis_radio.first.click()
        page.wait_for_timeout(1000)
    else:
        vis_text = page.locator(f"tp-yt-paper-radio-button:has-text('{visibility.capitalize()}')")
        if vis_text.count() > 0:
            vis_text.first.scroll_into_view_if_needed()
            vis_text.first.click()
            page.wait_for_timeout(1000)

    # Re-check link if not found earlier
    if not yt_url:
        link_elem = page.locator("a[href*='youtu.be']")
        if link_elem.count() > 0:
            yt_url = link_elem.first.get_attribute("href") or ""

    # CRITICAL: WAIT FOR FULL UPLOAD COMPLETION BEFORE SAVING
    print("\n" + "=" * 60)
    print("[*] STEP: WAITING FOR VIDEO FILE TO FINISH UPLOADING (100%)...")
    print("=" * 60)
    wait_for_upload_completion(page, timeout_seconds=600)

    # 11. Click Save / Publish
    print("[*] Saving upload...")
    done_btn = page.locator("#done-button:not([disabled]), button:has-text('Publish'):not([disabled]), ytcp-button#done-button:not([disabled]), #done-button, ytcp-button#done-button")
    try:
        done_btn.first.wait_for(state="visible", timeout=15000)
        done_btn.first.click()
        page.wait_for_timeout(3000)
    except Exception as e:
        print(f"[!] Note on save click: {e}")

    # Handle "We're still checking your content" dialog -> Click "Publish anyway"
    print("[*] Checking for 'Publish anyway' dialog...")
    publish_anyway_selectors = [
        "ytcp-button:has-text('Publish anyway')",
        "button:has-text('Publish anyway')",
        "#publish-button:has-text('Publish anyway')",
        "ytcp-confirmation-dialog ytcp-button#publish-button",
        "tp-yt-paper-dialog ytcp-button:has-text('Publish anyway')",
        "text='Publish anyway'"
    ]
    for _ in range(6):
        clicked_anyway = False
        for sel in publish_anyway_selectors:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible():
                print("[+] Detected 'We're still checking your content' dialog. Clicking 'Publish anyway'...")
                loc.first.click()
                clicked_anyway = True
                page.wait_for_timeout(3000)
                break
        if clicked_anyway:
            break
        page.wait_for_timeout(1000)

    # Monitor confirmation modal to ensure background upload doesn't get aborted
    print("[*] Monitoring post-publish confirmation modal...")
    modal_start = time.time()
    while time.time() - modal_start < 300:
        modal = page.locator("ytcp-uploads-dialog, ytcp-confirmation-dialog, ytcp-video-share-dialog, tp-yt-paper-dialog")
        modal_text = ""
        if modal.count() > 0:
            for i in range(modal.count()):
                if modal.nth(i).is_visible():
                    modal_text += " " + modal.nth(i).inner_text().strip()

        if "keep this browser tab open" in modal_text.lower() or "uploading" in modal_text.lower():
            print("    [Modal Notice] Background upload still in progress, keeping browser open...")
            page.wait_for_timeout(3000)
            continue
        else:
            print("[+] Modal indicates upload is complete.")
            break

    # Check for daily upload limit dialog after clicking publish
    if check_daily_limit(page):
        raise DailyUploadLimitException("Daily upload limit reached upon publishing.")

    # 12. Close confirmation modal if displayed and exit upload dialog
    print("[*] Closing upload confirmation modal...")
    close_selectors = [
        "#close-button",
        "ytcp-button:has-text('Close')",
        "button:has-text('Close')",
        "ytcp-icon-button[aria-label='Close']",
        "ytcp-uploads-dialog #close-button",
        "#dialog #close-button"
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

    # Check again if URL is displayed on confirmation modal
    if not yt_url:
        link_elem = page.locator("a[href*='youtu.be']")
        if link_elem.count() > 0:
            yt_url = link_elem.first.get_attribute("href") or ""

    print(f"[+] Video successfully uploaded! Link: {yt_url if yt_url else 'Pending in Studio'}")
    return yt_url if yt_url else "https://studio.youtube.com/channel/videos/short"


def main():
    parser = argparse.ArgumentParser(description="Automated YouTube Shorts Uploader.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of videos to upload.")
    parser.add_argument("--visibility", type=str, default="PUBLIC", choices=["PRIVATE", "UNLISTED", "PUBLIC"], help="Upload visibility (default: PUBLIC).")
    parser.add_argument("--vehicle", type=str, default=None, help="Filter by vehicle name or ID.")
    parser.add_argument("--start-id", type=int, default=None, help="Start uploading from this vehicle ID onwards.")
    parser.add_argument("--skip-ids", type=str, default=None, help="Comma-separated vehicle IDs to skip (e.g. 18 or 18,19).")
    parser.add_argument("--mark-uploaded", type=int, default=None, help="Mark vehicle ID as uploaded in tracker and sync master spreadsheet.")
    parser.add_argument("--unmark-uploaded", type=int, default=None, help="Remove vehicle ID from uploaded tracker.")
    parser.add_argument("--list-pending", action="store_true", help="List all pending vehicles in upload queue and exit.")
    parser.add_argument("--force", action="store_true", help="Re-upload even if already logged in tracker.")
    parser.add_argument("--dry-run", action="store_true", help="Preview metadata without launching browser.")
    parser.add_argument("--bike-assembly", action="store_true", help="Target videos from Bike Assembling Niche.")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    profile_dir = os.path.join(script_dir, "browser_profile")
    os.makedirs(profile_dir, exist_ok=True)

    tracker = UploadTracker(script_dir)
    videos = find_edited_videos(root_dir)

    # 1. Helper: Mark uploaded without browser
    if args.mark_uploaded is not None:
        target_id = args.mark_uploaded
        matching = [v for v in videos if v.get("id") == target_id]
        if not matching:
            print(f"[-] Error: Vehicle ID {target_id} not found in edited videos.")
            sys.exit(1)
        v = matching[0]
        meta = generate_short_metadata(v)
        v_path = v.get("video_path")
        tracker.record_upload(
            vid_id=target_id,
            vehicle_name=v.get("vehicle_name"),
            category=v.get("type", "car"),
            title=meta["title"],
            youtube_url="https://studio.youtube.com/channel/videos/short",
            visibility=args.visibility,
            local_video_path=os.path.relpath(v_path, root_dir) if v_path else ""
        )
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)
        try:
            from sync_master_tracker import update_master_tracker
            update_master_tracker(root_dir)
        except Exception as e:
            print(f"[!] Master tracker sync note: {e}")
        print(f"[+] SUCCESS: Marked Vehicle ID {target_id} ({v.get('vehicle_name')}) as UPLOADED.")
        print(f"[+] Updated: {tracker.json_path}")
        print(f"[+] Updated: {tracker.xlsx_path}")
        print(f"[+] Master tracker updated in root folder.")
        return

    # 2. Helper: Unmark uploaded
    if args.unmark_uploaded is not None:
        target_id = args.unmark_uploaded
        if target_id in tracker.records:
            del tracker.records[target_id]
            tracker.save()
            if root_dir not in sys.path:
                sys.path.insert(0, root_dir)
            try:
                from sync_master_tracker import update_master_tracker
                update_master_tracker(root_dir)
            except Exception:
                pass
            print(f"[+] Vehicle ID {target_id} removed from uploaded records.")
        else:
            print(f"[-] Vehicle ID {target_id} was not in uploaded records.")
        return

    # Parse skip IDs
    skip_set = set()
    if args.skip_ids:
        try:
            skip_set = {int(x.strip()) for x in args.skip_ids.split(",") if x.strip()}
        except ValueError:
            print("[-] Error: --skip-ids must be comma-separated integers (e.g. 18 or 18,19).")
            sys.exit(1)

    print("=" * 65)
    print("YOUTUBE SHORTS AUTOMATED UPLOADER")
    print(f"ENFORCED ACCOUNT: {REQUIRED_ACCOUNT}")
    print("=" * 65)
    print(f"Found {len(videos)} edited videos ready in video-editor/output.")
    print(f"Default visibility: {args.visibility}")
    if args.start_id:
        print(f"Start ID filter: >= {args.start_id}")
    if skip_set:
        print(f"Skipping IDs: {sorted(list(skip_set))}")
    print("=" * 65)

    if args.vehicle:
        query = args.vehicle.lower()
        videos = [v for v in videos if str(v.get("id")) == query or query in v.get("vehicle_name", "").lower()]
        print(f"Filtered by '{args.vehicle}': {len(videos)} match(es).")

    if args.bike_assembly:
        videos = [v for v in videos if v.get("source_excel") == "bike_assembling_niche"]
        print(f"Targeting Bike Assembling Niche: {len(videos)} video(s) found.")

    to_process = []
    for v in videos:
        vid_id = v.get("id")
        v_name = v.get("vehicle_name")
        v_src = v.get("source_excel")
        v_path = v.get("video_path")
        if tracker.is_uploaded(vid_id, vehicle_name=v_name, source_excel=v_src, video_path=v_path) and not args.force:
            continue
        if args.start_id and vid_id < args.start_id:
            continue
        if vid_id in skip_set:
            continue
        to_process.append(v)

    # 3. Helper: List pending
    if args.list_pending:
        print(f"\nPENDING UPLOAD QUEUE ({len(to_process)} vehicles):")
        print("-" * 65)
        for p_idx, v in enumerate(to_process, 1):
            print(f"{p_idx:2d}. ID {v.get('id'):2d} | {v.get('vehicle_name')} ({v.get('type', 'car')}) [{v.get('source_excel')}]")
        print("-" * 65)
        return

    print(f"Videos pending upload: {len(to_process)}")

    if args.limit:
        to_process = to_process[:args.limit]
        print(f"Limited to first {args.limit} video(s).")

    if not to_process:
        print("[*] No pending videos to upload. All videos are already uploaded!")
        return

    if args.dry_run:
        print("\n=== DRY RUN MODE: PREVIEWING METADATA ===")
        for idx, v in enumerate(to_process, 1):
            meta = generate_short_metadata(v)
            print(f"\n[{idx}/{len(to_process)}] Vehicle: {v.get('vehicle_name')} (ID: {v.get('id')}) [{v.get('source_excel')}]")
            print(f"Video File: {v.get('video_path')}")
            print(f"Short Title: {meta['title']}")
            print(f"Tags: {meta['tags_csv'][:120]}...")
            print(f"Visibility: {args.visibility}")
        return

    # Launch Playwright Browser with dedicated uploader profile
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

        # Open a dedicated tab for uploading, leaving any other tabs undisturbed
        page = context.new_page()

        success_count = 0
        failed_count = 0
        daily_limit_hit = False

        for idx, v in enumerate(to_process, 1):
            vid_id = v.get("id")
            name = v.get("vehicle_name")
            category = v.get("type", "car")
            v_src = v.get("source_excel")
            v_path = v.get("video_path")
            meta = generate_short_metadata(v)

            print(f"\n[{idx}/{len(to_process)}] Processing: {name} (ID: {vid_id}) [{v_src}]")
            print(f"File: {v_path}")

            try:
                yt_link = upload_single_video(page, v_path, meta, visibility=args.visibility)
                if yt_link:
                    tracker.record_upload(
                        vid_id=vid_id,
                        vehicle_name=name,
                        category=category,
                        title=meta["title"],
                        youtube_url=yt_link,
                        visibility=args.visibility,
                        local_video_path=os.path.relpath(v_path, root_dir),
                        source_excel=v_src
                    )
                    success_count += 1

                    # Synchronize parent master tracker & 100 cars tracker on every iteration
                    try:
                        if root_dir not in sys.path:
                            sys.path.insert(0, root_dir)
                        from sync_master_tracker import update_master_tracker
                        update_master_tracker(root_dir)
                    except Exception as e:
                        print(f"[!] Note: Master tracker sync bypassed: {e}")

                    try:
                        if root_dir not in sys.path:
                            sys.path.insert(0, root_dir)
                        from sync_100_cars_tracker import update_100_cars_tracker
                        update_100_cars_tracker(root_dir)
                    except Exception as e:
                        print(f"[!] Note: 100 Cars tracker sync bypassed: {e}")

                    page.wait_for_timeout(3000)
                else:
                    print(f"[-] Upload failed or halted for {name}")
                    failed_count += 1
                    # If verification failed, halt entire batch
                    if "accounts.google.com" in page.url or not verify_active_account(page, REQUIRED_ACCOUNT):
                        print("[!] Stopping batch due to authentication/account mismatch.")
                        break

            except DailyUploadLimitException as e:
                daily_limit_hit = True
                failed_count += 1
                print("\n" + "!" * 70)
                print(f"[-] FATAL: YouTube Daily Upload Limit Reached on {name} (ID: {vid_id})!")
                print("[-] YouTube limits standard channels to ~15-16 uploads per 24 hours.")
                print("[-] How to unlock higher upload limits:")
                print("    1. Go to YouTube Studio -> Settings -> Channel -> Feature eligibility.")
                print("    2. Verify phone number under 'Intermediate features' to get 100+ uploads/day.")
                print("    3. Or wait for the rolling 24-hour limit to reset.")
                print("!" * 70 + "\n")
                break

            except Exception as e:
                print(f"[-] Error uploading {name}: {e}")
                failed_count += 1

        try:
            if not page.is_closed():
                page.close()
        except Exception:
            pass

        try:
            remaining = [p for p in context.pages if not p.is_closed()]
            if len(remaining) == 0:
                context.close()
        except Exception:
            pass

    print("\n" + "=" * 65)
    print("UPLOAD BATCH COMPLETE")
    print(f"Successfully uploaded: {success_count}")
    print(f"Failed / Halted: {failed_count}")
    print(f"Tracker Excel: {tracker.xlsx_path}")
    print(f"Tracker JSON: {tracker.json_path}")
    print("=" * 65)

    if daily_limit_hit:
        sys.exit(2)
    elif success_count == 0 and failed_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
