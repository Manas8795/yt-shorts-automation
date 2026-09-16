import os
import time
from playwright.sync_api import sync_playwright
from app.storage.file_manager import FileManager
from app.generation.batch_manager import BatchManager
from app.browser.flow_client import FlowClient

profile = os.path.abspath("browser_profile")
output_dir = os.path.abspath("output/2026-09-04/job_0002_Yamaha_RX100")
os.makedirs(output_dir, exist_ok=True)

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

print(f"Flow Home Title: {page.title()} | URL: {page.url}")

# Find all project cards / list items on home
cards = page.locator("a[href*='/project/'], div[role='button']:has-text('Sept'), div[role='button']:has-text('Untitled')").all()
print(f"Found {len(cards)} project cards.")

# Click the most recent project (or first project)
if cards:
    print("Opening most recent project...")
    cards[0].click()
    time.sleep(6)
    flow.dismiss_popups()
    
    print(f"Opened Project URL: {page.url} | Title: {page.title()}")
    page.screenshot(path="debug/found_project.png")
    print("Saved screenshot to debug/found_project.png")

    try:
        video_path = flow.download_video(output_dir)
        file_mgr = FileManager(base_output_dir="./output")
        is_valid, size = file_mgr.verify_video_file(video_path)

        if is_valid:
            size_mb = round(size / (1024 * 1024), 2)
            print(f"\n✓ SUCCESS! Video downloaded: {video_path} ({size_mb} MB)")
            batch_mgr = BatchManager(vehicles_file="data/vehicles.json")
            batch_mgr.mark_completed(vehicle_id=2, output_video_path=video_path)
            print("Vehicle #2 (Yamaha RX100) marked COMPLETED in database.")
    except Exception as e:
        print(f"Download check: {e}")

ctx.close()
p.stop()
