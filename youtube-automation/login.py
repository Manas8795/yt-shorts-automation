import os
import time
from playwright.sync_api import sync_playwright

profile = os.path.abspath("browser_profile")
os.makedirs(profile, exist_ok=True)

print("=" * 60)
print("  Opening Chrome for Google Flow Sign-In...")
print("=" * 60)
print(f"Profile directory: {profile}")
print("\n>>> Please sign in with your Google account in the browser window. <<<")
print(">>> When you see the Google Flow project workspace, simply close the browser window. <<<\n")

p = sync_playwright().start()
try:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=profile,
        headless=False,
        channel="chrome",
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--no-first-run",
            "--start-maximized"
        ]
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://flow.google.com/")

    # Keep browser open until the user manually closes it or reaches Flow
    while True:
        try:
            if page.is_closed() or not ctx.pages:
                print("\nBrowser closed by user. Saving profile session...")
                break
            time.sleep(1)
        except Exception:
            break

except Exception as e:
    print(f"Error launching browser: {e}")
finally:
    try:
        p.stop()
    except Exception:
        pass

print("\n✓ Login helper finished. You can now run 'python -m tests.check_account' to verify.")
