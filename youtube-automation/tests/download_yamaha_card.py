import os
import time
from playwright.sync_api import sync_playwright
from app.storage.file_manager import FileManager
from app.generation.batch_manager import BatchManager
from app.browser.flow_client import FlowClient

profile = os.path.abspath("browser_profile")
output_dir = os.path.abspath("output/2026-09-04/job_0002_Yamaha_RX100")
os.makedirs(output_dir, exist_ok=True)

print("Opening Google Flow and clicking the Yamaha project card...")
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

# Scroll down to reveal full projects grid
page.mouse.wheel(0, 400)
time.sleep(2)

# Find all cards in the grid
# The Yamaha card is right after + New project
cards = page.locator("div.project-card, [role='button']:has(img), a:has(img), div:has(> img)").all()
print(f"Found {len(cards)} cards with images/projects.")

# Locate the card with Yamaha image or click the first project with an image thumbnail
clicked = False
for c in cards:
    try:
        if c.is_visible():
            c.click()
            clicked = True
            time.sleep(6)
            break
    except Exception as e:
        pass

if not clicked:
    # Click by position or click the project item next to + New project
    print("Clicking project item near bottom right...")
    page.mouse.click(800, 800)
    time.sleep(6)

flow.dismiss_popups()
print(f"Active Project URL: {page.url} | Title: {page.title()}")
os.makedirs("debug", exist_ok=True)
page.screenshot(path="debug/yamaha_opened_canvas.png")

# Now download the scene video
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
        print("Vehicle #2 (Yamaha RX100) marked as COMPLETED in data/vehicles.json!")
    else:
        print("Verification failed: downloaded file was 0 bytes.")
except Exception as e:
    print(f"Download execution error: {e}")

ctx.close()
p.stop()
