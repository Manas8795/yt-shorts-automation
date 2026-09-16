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
time.sleep(4)
flow.dismiss_popups()

# Locate the project image in the recent projects section
# In Google Flow, projects are under the banner
proj_cards = page.locator("div.project-card, [data-project-id], a[href*='/project/'], div:has(> img)").all()

# Find all images on the page
imgs = page.locator("img").all()
print(f"Found {len(imgs)} images on home page.")

# Find the project thumbnail image
for img in imgs:
    try:
        box = img.bounding_box()
        # Project cards are below the top banner (y > 600)
        if box and box['y'] > 500:
            print(f"Clicking project thumbnail at ({box['x']}, {box['y']})...")
            img.scroll_into_view_if_needed()
            time.sleep(1)
            img.click(force=True)
            time.sleep(6)
            break
    except Exception as e:
        pass

flow.dismiss_popups()
print(f"Opened URL: {page.url} | Title: {page.title()}")

os.makedirs("debug", exist_ok=True)
page.screenshot(path="debug/yamaha_card_opened.png")
print("Saved debug/yamaha_card_opened.png")

# If project is opened, download the video
if "/project/" in page.url:
    try:
        video_path = flow.download_video(output_dir)
        file_mgr = FileManager(base_output_dir="./output")
        is_valid, size = file_mgr.verify_video_file(video_path)

        if is_valid:
            size_mb = round(size / (1024 * 1024), 2)
            print("\n" + "=" * 65)
            print(f"✓ SUCCESS! Yamaha RX100 video downloaded: {video_path} ({size_mb} MB)")
            print("=" * 65)
            batch_mgr = BatchManager(vehicles_file="data/vehicles.json")
            batch_mgr.mark_completed(vehicle_id=2, output_video_path=video_path)
            print("Vehicle #2 (Yamaha RX100) marked COMPLETED in database!")
    except Exception as e:
        print(f"Download check: {e}")

ctx.close()
p.stop()
