import os
import time
from playwright.sync_api import sync_playwright
from app.storage.file_manager import FileManager
from app.generation.batch_manager import BatchManager
from app.browser.flow_client import FlowClient

profile = os.path.abspath("browser_profile")
output_dir = os.path.abspath("output/2026-09-04/job_0002_Yamaha_RX100")
os.makedirs(output_dir, exist_ok=True)

print("Opening Google Flow to find project 'Sept 04 - 22:22'...")
p = sync_playwright().start()
ctx = p.chromium.launch_persistent_context(
    user_data_dir=profile,
    headless=False,
    channel="chrome",
    args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
)
page = ctx.pages[0] if ctx.pages else ctx.new_page()
flow = FlowClient(page=page)
page.goto("https://flow.google.com/", wait_until="domcontentloaded")
time.sleep(5)
flow.dismiss_popups()

# Search for the card with "22:22" or "Sept 04 - 22:22"
target_card = page.locator("div[role='button']:has-text('22:22'), a:has-text('22:22'), tr:has-text('22:22'), [aria-label*='22:22']")

if target_card.count() == 0:
    print("Direct text '22:22' not found immediately, searching all project items...")
    all_cards = page.locator("div[role='button'], a[href*='/project/']").all()
    for c in all_cards:
        try:
            txt = c.inner_text().replace('\n', ' ')
            if "22:22" in txt:
                target_card = c
                break
        except:
            pass

if target_card and (isinstance(target_card, list) and len(target_card) > 0 or target_card.count() > 0):
    elem = target_card[0] if isinstance(target_card, list) else target_card.first
    print("Found project 'Sept 04 - 22:22'! Opening...")
    elem.click()
    time.sleep(6)
    flow.dismiss_popups()

    print(f"Project URL: {page.url} | Title: {page.title()}")
    os.makedirs("debug", exist_ok=True)
    page.screenshot(path="debug/yamaha_2222_project.png")
    print("Saved screenshot to debug/yamaha_2222_project.png")

    try:
        video_path = flow.download_video(output_dir)
        file_mgr = FileManager(base_output_dir="./output")
        is_valid, size = file_mgr.verify_video_file(video_path)

        if is_valid:
            size_mb = round(size / (1024 * 1024), 2)
            print(f"\n=======================================================")
            print(f"✓ SUCCESS! Yamaha RX100 video downloaded successfully!")
            print(f"File: {video_path} ({size_mb} MB)")
            print(f"=======================================================")
            batch_mgr = BatchManager(vehicles_file="data/vehicles.json")
            batch_mgr.mark_completed(vehicle_id=2, output_video_path=video_path)
            print("Vehicle #2 (Yamaha RX100) marked as COMPLETED in database!")
        else:
            print("Video verification failed or file was 0 bytes.")
    except Exception as e:
        print(f"Error during video download: {e}")
else:
    print("Could not find project tile for 'Sept 04 - 22:22'. Taking screenshot of home...")
    os.makedirs("debug", exist_ok=True)
    page.screenshot(path="debug/flow_home_projects.png")

ctx.close()
p.stop()
