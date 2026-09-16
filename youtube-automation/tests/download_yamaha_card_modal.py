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
    args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
)
page = ctx.pages[0] if ctx.pages else ctx.new_page()
page.goto(project_url, wait_until="domcontentloaded")
time.sleep(5)

# Click on the video card on the canvas (position roughly x=250, y=280)
print("Clicking video card on canvas...")
# Try clicking element or coordinate
card = page.locator("div:has(> img)").last
if card.count() > 0:
    card.click()
else:
    page.mouse.click(250, 280)

time.sleep(3)

# Save screenshot of opened modal
os.makedirs("debug", exist_ok=True)
page.screenshot(path="debug/yamaha_modal_opened.png")
print("Saved debug/yamaha_modal_opened.png")

# Print all visible buttons
buttons = page.locator("button, [role='button']").all()
print("--- Visible buttons in modal ---")
for b in buttons:
    try:
        if b.is_visible():
            txt = b.inner_text().replace('\n', ' ').strip()
            aria = b.get_attribute('aria-label') or ''
            if txt or aria:
                print(f"Button -> Text: [{txt}] | Aria: [{aria}]")
    except:
        pass

# Intercept download
dl_btn = page.locator("button[aria-label*='Download'], button:has-text('Download'), button:has-text('download'), [aria-label*='download']").first

if dl_btn.count() > 0 and dl_btn.is_visible():
    print(f"Triggering download via button: {dl_btn}...")
    with page.expect_download(timeout=45000) as dl_info:
        dl_btn.click()
    download = dl_info.value
    download.save_as(target_video_path)
    print(f"Downloaded file to: {target_video_path}")
else:
    # Check more_vert menu
    more = page.locator("button[aria-label*='More'], button:has-text('more_vert')").last
    if more.count() > 0 and more.is_visible():
        print("Clicking more_vert menu...")
        more.click()
        time.sleep(1)
        menu_dl = page.locator("[role='menuitem']:has-text('Download'), button:has-text('Download')").first
        with page.expect_download(timeout=45000) as dl_info:
            menu_dl.click()
        download = dl_info.value
        download.save_as(target_video_path)
        print(f"Downloaded file to: {target_video_path}")

file_mgr = FileManager(base_output_dir="./output")
is_valid, size = file_mgr.verify_video_file(target_video_path)

if is_valid:
    size_mb = round(size / (1024 * 1024), 2)
    print("\n" + "=" * 65)
    print(f"✓ SUCCESS! Yamaha RX100 video verified: {target_video_path} ({size_mb} MB)")
    print("=" * 65)
    batch_mgr = BatchManager(vehicles_file="data/vehicles.json")
    batch_mgr.mark_completed(vehicle_id=2, output_video_path=target_video_path)
    print("Vehicle #2 (Yamaha RX100) marked as COMPLETED in database!")

ctx.close()
p.stop()
