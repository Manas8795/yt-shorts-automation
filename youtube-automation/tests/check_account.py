import os
import time
from playwright.sync_api import sync_playwright

profile = os.path.abspath("browser_profile")
print("=======================================================")
print("  Checking Active Google Flow Account in Profile...")
print("=======================================================")

p = sync_playwright().start()
try:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=profile,
        headless=True,
        channel="chrome",
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://flow.google.com/", wait_until="domcontentloaded")
    time.sleep(4)

    # Check for user avatar / account button aria-label
    account_elem = page.locator("[aria-label*='Google Account'], [aria-label*='@'], [data-identifier], img[alt*='Google Account']").first
    
    if account_elem.count() > 0:
        aria = account_elem.get_attribute("aria-label") or ""
        alt = account_elem.get_attribute("alt") or ""
        text = account_elem.inner_text().strip()
        account_info = aria or alt or text
        print(f"\n[ACTIVE ACCOUNT]:\n  {account_info}")
    else:
        # Check current URL
        if "signin" in page.url or "about" in page.url:
            print("\n[NO ACTIVE SESSION]: Currently signed out or on landing page.")
        else:
            print(f"\n[SESSION ACTIVE] on URL: {page.url} (Title: {page.title()})")

    ctx.close()
except Exception as e:
    print(f"Error checking account: {e}")
finally:
    p.stop()
print("=======================================================")
