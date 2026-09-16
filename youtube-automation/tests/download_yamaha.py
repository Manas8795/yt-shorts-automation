import os
import time
from playwright.sync_api import sync_playwright
from app.storage.file_manager import FileManager
from app.generation.batch_manager import BatchManager
from app.browser.flow_client import FlowClient

profile = os.path.abspath("browser_profile")
project_url = "https://flow.google.com/project/8568fd05-55f5-4be9-a5de-18e337b0c8e9"
output_dir = os.path.abspath("output/2026-09-04/job_0002_Yamaha_RX100")
os.makedirs(output_dir, exist_ok=True)

print(f"Resuming Yamaha RX100 project canvas: {project_url}")
p = sync_playwright().start()
ctx = p.chromium.launch_persistent_context(
    user_data_dir=profile,
    headless=False,
    channel="chrome",
    args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
)
page = ctx.pages[0] if ctx.pages else ctx.new_page()

flow = FlowClient(page=page)
page.goto(project_url, wait_until="domcontentloaded")
time.sleep(5)
flow.dismiss_popups()

print(f"Canvas Title: {page.title()} | URL: {page.url}")

# Take a screenshot of the project canvas
os.makedirs("debug", exist_ok=True)
page.screenshot(path="debug/yamaha_canvas.png")
print("Saved debug screenshot to debug/yamaha_canvas.png")

# Trigger download via FlowClient
try:
    video_path = flow.download_video(output_dir)
    file_mgr = FileManager(base_output_dir="./output")
    is_valid, size = file_mgr.verify_video_file(video_path)

    if is_valid:
        size_mb = round(size / (1024 * 1024), 2)
        print(f"\n✓ SUCCESS! Yamaha RX100 video downloaded: {video_path} ({size_mb} MB)")
        
        batch_mgr = BatchManager(vehicles_file="data/vehicles.json")
        batch_mgr.mark_completed(vehicle_id=2, output_video_path=video_path)
        print("Vehicle #2 (Yamaha RX100) marked as COMPLETED in database.")
    else:
        print("Download verification failed or file was empty.")
except Exception as e:
    print(f"Download error: {e}")

ctx.close()
p.stop()
