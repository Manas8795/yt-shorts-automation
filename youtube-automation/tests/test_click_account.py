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
time.sleep(3)

if "about" in page.url:
    create_btn = page.locator("button:has-text('Create with Google Flow'), a:has-text('Create with Google Flow')")
    if create_btn.count() > 0 and create_btn.first.is_visible():
        create_btn.first.click()
        time.sleep(3)

print("Current URL:", page.url)
print("Page Title:", page.title())

# If on account chooser, click the account tile
if "accountchooser" in page.url or "signin" in page.url:
    print("Inspecting account chooser items...")
    items = page.locator("div[role='link'], li, [data-email], [data-identifier], div[jsname]").all()
    for i, it in enumerate(items):
        try:
            if it.is_visible():
                txt = it.inner_text().replace('\n', ' ').strip()
                if "manasagrawal" in txt or "@gmail.com" in txt:
                    print(f"Clicking account item {i}: {txt}")
                    it.click()
                    time.sleep(5)
                    break
        except:
            pass

print("URL after click:", page.url)
print("Title after click:", page.title())

os.makedirs('debug', exist_ok=True)
page.screenshot(path='debug/after_account_click.png')
print("Saved debug screenshot to debug/after_account_click.png")

time.sleep(3)
ctx.close()
p.stop()
