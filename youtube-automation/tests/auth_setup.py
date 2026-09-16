from playwright.sync_api import sync_playwright
import os
import time

profile = os.path.abspath('browser_profile')
print("=" * 60)
print("GOOGLE FLOW AUTHENTICATION SETUP")
print("=" * 60)
print(f"Using persistent browser profile: {profile}")
print("Opening browser...")

p = sync_playwright().start()
ctx = p.chromium.launch_persistent_context(
    user_data_dir=profile,
    headless=False,
    channel='chrome',
    args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
)
page = ctx.pages[0] if ctx.pages else ctx.new_page()
page.goto('https://flow.google.com/')

print("\n>>> PLEASE SIGN IN TO YOUR GOOGLE ACCOUNT IN THE OPEN BROWSER WINDOW <<<")
print("Waiting for you to complete sign in and reach the Google Flow canvas...")

# Keep checking until user finishes login and reaches the app
while True:
    current_url = page.url
    # If on about page, auto click create
    if "flow.google.com/about" in current_url:
        create_btn = page.locator("button:has-text('Create with Google Flow'), a:has-text('Create with Google Flow')")
        if create_btn.count() > 0 and create_btn.first.is_visible():
            try:
                create_btn.first.click()
            except:
                pass
    elif "flow.google.com" in current_url and "signin" not in current_url and "accounts.google.com" not in current_url:
        print("\n" + "=" * 60)
        print("✓ SUCCESS: Logged in to Google Flow successfully!")
        print(f"Final URL: {current_url}")
        print("=" * 60)
        time.sleep(5)
        break

    time.sleep(2)

ctx.close()
p.stop()
print("Browser closed. Persistent session is saved and ready for automation!")
