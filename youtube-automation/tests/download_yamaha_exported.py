import os
import time
from playwright.sync_api import sync_playwright
from app.storage.file_manager import FileManager
from app.generation.batch_manager import BatchManager

profile = os.path.abspath("browser_profile")
project_url = "https://flow.google.com/project/6d8816b6-0d56-4574-881c-c0385f68026a"
output_dir = os.path.abspath("output/2026-09-04/job_0002_Yamaha_RX100")
os.makedirs(output_dir, exist_ok=True)
target_video_path = os.path.join(output_dir, "video.mp4")

print(f"Opening Yamaha RX100 canvas: {project_url}")
p = sync_playwright().start()
ctx = p.chromium.launch_persistent_context(
    user_data_dir=profile,
    headless=False,
    channel="chrome",
    accept_downloads=True,
    args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
)
page = ctx.pages[0] if ctx.pages else ctx.new_page()
page.goto(project_url, wait_until="domcontentloaded")
time.sleep(5)

# Click on the video card to open timeline modal
print("Opening video editor modal...")
card = page.locator("div:has(> img)").last
if card.count() > 0:
    card.click()
time.sleep(3)

# Locate download button
dl_btn = page.locator("button[aria-label='Download scene']").first
print("Clicking 'Download scene' button...")

with page.expect_download(timeout=120000) as dl_info:
    dl_btn.click()
    print("Waiting for 'Exporting your scene...' cloud render packaging to finish (up to 2 min)...")

download = dl_info.value
download.save_as(target_video_path)
print(f"Downloaded file successfully saved to: {target_video_path}")

file_mgr = FileManager(base_output_dir="./output")
is_valid, size = file_mgr.verify_video_file(target_video_path)

if is_valid:
    size_mb = round(size / (1024 * 1024), 2)
    print("\n" + "=" * 65)
    print(f"✓ SUCCESS! Yamaha RX100 video verified on disk!")
    print(f"File Path: {target_video_path} ({size_mb} MB)")
    print("=" * 65)
    batch_mgr = BatchManager(vehicles_file="data/vehicles.json")
    batch_mgr.mark_completed(vehicle_id=2, output_video_path=target_video_path)
    print("Vehicle #2 (Yamaha RX100) marked as COMPLETED in data/vehicles.json!")

ctx.close()
p.stop()
