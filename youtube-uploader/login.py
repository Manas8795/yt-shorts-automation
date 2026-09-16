"""
YouTube Studio Authentication Helper
------------------------------------
Opens a headed Chrome window pointing to YouTube Studio (https://studio.youtube.com).
Logs into your dedicated YouTube channel account: manasagrawal8791@gmail.com.
This is completely isolated in youtube-uploader/browser_profile and will NEVER
interfere with Google Flow or your video generation automation.
"""

import os
import sys
import time
from playwright.sync_api import sync_playwright

REQUIRED_ACCOUNT = "manasagrawal8791@gmail.com"

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def check_account_on_page(page) -> str:
    """Attempts to detect the current logged-in Google email."""
    try:
        avatar = page.locator("#avatar-btn, button#avatar-btn, ytcp-profile-avatar")
        if avatar.count() > 0 and avatar.first.is_visible():
            avatar.first.click()
            page.wait_for_timeout(1000)
            email_elem = page.locator("#email, ytd-active-account-header-renderer #email, [aria-label*='@'], div:has-text('@gmail.com')")
            for i in range(email_elem.count()):
                txt = email_elem.nth(i).inner_text().strip()
                if "@" in txt:
                    page.keyboard.press("Escape")
                    return txt
            page.keyboard.press("Escape")
    except Exception:
        pass
    return ""


def login_interactive():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    profile_dir = os.path.join(script_dir, "browser_profile")
    os.makedirs(profile_dir, exist_ok=True)

    print("=" * 65)
    print("YOUTUBE STUDIO AUTHENTICATION HELPER")
    print(f"REQUIRED ACCOUNT: {REQUIRED_ACCOUNT}")
    print("=" * 65)
    print(f"Browser profile: {profile_dir}")
    print("Launching Chrome browser...")
    print(f"--> Please log into Google with: {REQUIRED_ACCOUNT}")
    print("This profile is completely separate from your Google Flow account.")
    print("=" * 65)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ],
            no_viewport=True
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://studio.youtube.com", wait_until="domcontentloaded")

        print("\nWaiting for you to log in to YouTube Studio...")
        print(f"Please ensure you sign into: {REQUIRED_ACCOUNT}")
        
        try:
            input("\n--> When you are signed into YouTube Studio as manasagrawal8791@gmail.com, press [ENTER] here: ")
        except (KeyboardInterrupt, EOFError):
            pass

        # Check detected account
        detected = check_account_on_page(page)
        if detected:
            print(f"\n[*] Detected account: {detected}")
            if REQUIRED_ACCOUNT.lower() in detected.lower():
                print(f"[+] Verified! Successfully logged in as {REQUIRED_ACCOUNT}")
            else:
                print(f"[!] WARNING: Detected account '{detected}' does not match required '{REQUIRED_ACCOUNT}'!")
        else:
            print(f"[*] Could not automatically read email, session saved to {profile_dir}.")

        print("Saving session and closing browser...")
        context.close()
        print("[+] Session saved! You can now run the uploader automation.")


if __name__ == "__main__":
    login_interactive()
