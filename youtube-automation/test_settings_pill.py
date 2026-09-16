import time
import os
from playwright.sync_api import sync_playwright

profile_dir = r"d:\Temp\yt automation\youtube-automation\browser_profile"
debug_dir = r"d:\Temp\yt automation\youtube-automation\debug"
os.makedirs(debug_dir, exist_ok=True)

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=profile_dir,
        headless=False,
        channel="chrome",
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--no-first-run",
            "--disable-session-crashed-bubble",
            "--disable-restore-session-state"
        ]
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.set_viewport_size({"width": 1400, "height": 900})
    
    print("Navigating to existing project...")
    page.goto("https://flow.google.com/project/2805fba9-cb0b-4216-a690-8fe4c571cc06", wait_until="domcontentloaded")
    time.sleep(5)

    page.screenshot(path=os.path.join(debug_dir, "project_prompt_area.png"))
    
    # Locate prompt area container (bottom bar)
    prompt_box = page.locator("div.ProseMirror, [contenteditable='true']").first
    print("Prompt box found:", prompt_box.count() > 0)
    
    # Find the prompt container (closest parent form or div)
    prompt_container = page.locator("form, div:has(> div.ProseMirror), div:has(> [contenteditable='true'])").last
    
    print("--- Elements inside prompt container ---")
    buttons = prompt_container.locator("button, [role='button'], div[class*='pill'], div[class*='chip']").all()
    for b in buttons:
        txt = b.inner_text().strip().replace("\n", " ")
        aria = b.get_attribute("aria-label") or ""
        tag = b.evaluate("e => e.tagName")
        cls = b.get_attribute("class") or ""
        print(f"  [{tag}] text='{txt}' | aria='{aria}' | class='{cls[:30]}'")

    # Target the pill button specifically inside prompt container
    pill_btn = prompt_container.locator("button:has-text('Video'), button:has-text('360p'), button:has-text('720p'), button:has-text('x2'), button:has-text('x1'), [role='button']:has-text('Video')").first
    if pill_btn.count() == 0:
        # Check by position near right side of prompt container before submit button
        pill_btn = prompt_container.locator("button:not([type='submit']):not([aria-label*='generation']):not(:has-text('Agent'))").last

    if pill_btn.count() > 0:
        print(f"Clicking settings pill button: '{pill_btn.inner_text().strip()}'...")
        pill_btn.click()
        time.sleep(2)
        page.screenshot(path=os.path.join(debug_dir, "settings_popover_opened.png"))
        print("Screenshot saved to debug/settings_popover_opened.png")
        
        print("--- Options inside Settings Popover ---")
        for opt in page.locator("[role='dialog'] *, [role='menu'] *, div[class*='popover'] *, div[class*='menu'] *, div[class*='modal'] *").all():
            try:
                if opt.is_visible():
                    t = opt.inner_text().strip().replace("\n", " ")
                    if t and len(t) < 60:
                        print(f"  Option: '{t}' | tag={opt.evaluate('e => e.tagName')} | role={opt.get_attribute('role')}")
            except:
                pass

    ctx.close()
