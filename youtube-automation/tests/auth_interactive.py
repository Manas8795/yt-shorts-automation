from playwright.sync_api import sync_playwright
import os
import time

profile = os.path.abspath('browser_profile')
print("=" * 65)
print("GOOGLE FLOW AUTHENTICATION SETUP")
print("=" * 65)
print(f"Opening Chrome with persistent profile: {profile}")

p = sync_playwright().start()
ctx = p.chromium.launch_persistent_context(
    user_data_dir=profile,
    headless=False,
    channel='chrome',
    args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
)
page = ctx.pages[0] if ctx.pages else ctx.new_page()
page.goto('https://flow.google.com/')
time.sleep(3)

# If on landing page, click Create with Google Flow
if "about" in page.url:
    create_btn = page.locator("button:has-text('Create with Google Flow'), a:has-text('Create with Google Flow')")
    if create_btn.count() > 0 and create_btn.first.is_visible():
        create_btn.first.click()
        time.sleep(3)

# If on account chooser, click the account tile
if "accountchooser" in page.url:
    acc = page.locator("li:has-text('manasagrawal8790'), [data-email*='manasagrawal8790'], div:has-text('manasagrawal8790@gmail.com')").last
    if acc.count() > 0:
        print("Clicking 'Manas Agrawal' account tile to open password field...")
        acc.click()
        time.sleep(3)

print("\n>>> BROWSER IS READY! PLEASE ENTER YOUR PASSWORD IN THE OPEN WINDOW <<<")
print("Waiting for you to finish logging in (window will stay open)...")

# Keep waiting until user completes login and reaches Google Flow app
while True:
    cur = page.url
    if "flow.google.com" in cur and "about" not in cur and "signin" not in cur and "accounts.google.com" not in cur:
        print("\n" + "=" * 65)
        print("✓ SUCCESS! Successfully authenticated into Google Flow!")
        print(f"Active Canvas URL: {cur}")
        print("Saving persistent session and closing setup window in 5 seconds...")
        print("=" * 65)
        time.sleep(5)
        break
    time.sleep(2)

ctx.close()
p.stop()
print("Setup complete! You can now run batch video generation seamlessly.")
