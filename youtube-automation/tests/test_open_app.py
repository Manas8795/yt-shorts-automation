from playwright.sync_api import sync_playwright
import os

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
page.wait_for_timeout(4000)

print("Current URL:", page.url)

create_btn = page.locator("button:has-text('Create with Google Flow'), a:has-text('Create with Google Flow'), button:has-text('Try Google Flow'), a:has-text('Try Google Flow')")
if create_btn.count() > 0 and create_btn.first.is_visible():
    print("Clicking Create with Google Flow...")
    create_btn.first.click()
    page.wait_for_timeout(6000)

print("URL after click:", page.url)
print("Page Title:", page.title())

buttons = page.locator("button, [role='button']").all()
print("--- Buttons on app canvas ---")
for b in buttons:
    try:
        if b.is_visible():
            txt = b.inner_text().replace('\n', ' ').strip()
            aria = b.get_attribute('aria-label') or ''
            if txt or aria:
                print(f"Text: [{txt}] | Aria: [{aria}]")
    except:
        pass

ctx.close()
p.stop()
