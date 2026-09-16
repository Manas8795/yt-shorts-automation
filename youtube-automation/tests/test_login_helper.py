from playwright.sync_api import sync_playwright
import os
import time

profile = os.path.abspath('browser_profile')
p = sync_playwright().start()
ctx = p.chromium.launch_persistent_context(
    user_data_dir=profile,
    headless=False,
    channel='chrome',
    args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
)
page = ctx.pages[0] if ctx.pages else ctx.new_page()
page.goto('https://flow.google.com/')
print("Please enter your password and sign in on the open browser window.")
print("Waiting for login to complete (up to 3 minutes)...")

for sec in range(180):
    if "flow.google.com" in page.url and "about" not in page.url and "signin" not in page.url:
        print(f"✓ Login detected! Current URL: {page.url} | Title: {page.title()}")
        print("Saving persistent session in browser_profile...")
        time.sleep(5)
        break
    time.sleep(2)

print("Session refreshed successfully. Closing helper...")
ctx.close()
p.stop()
