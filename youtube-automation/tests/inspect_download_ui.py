import os
import time
from playwright.sync_api import sync_playwright

profile = os.path.abspath("browser_profile")
project_url = "https://flow.google.com/project/6d8816b6-0d56-4574-881c-c0385f68026a"

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

# Click the video card
card = page.locator("div:has(> img)").last
if card.count() > 0:
    card.click()
time.sleep(3)

# Click Download scene button
dl_btn = page.locator("button[aria-label='Download scene'], button[aria-label*='Download']").first
print("Clicking Download scene button...")
dl_btn.click()
time.sleep(3)

os.makedirs("debug", exist_ok=True)
page.screenshot(path="debug/after_download_click.png")
print("Saved screenshot to debug/after_download_click.png")

# List all dialogs, popups, and buttons
buttons = page.locator("button, [role='button'], [role='menuitem'], [role='dialog']").all()
print("--- Elements on screen after download click ---")
for b in buttons:
    try:
        if b.is_visible():
            txt = b.inner_text().replace('\n', ' ').strip()
            aria = b.get_attribute('aria-label') or ''
            role = b.get_attribute('role') or ''
            if txt or aria:
                print(f"Role: [{role}] | Text: [{txt}] | Aria: [{aria}]")
    except:
        pass

time.sleep(5)
ctx.close()
p.stop()
