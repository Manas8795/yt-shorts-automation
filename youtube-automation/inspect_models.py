import time
import os
from playwright.sync_api import sync_playwright

profile_dir = r"d:\Temp\yt automation\youtube-automation\browser_profile"
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(user_data_dir=profile_dir, headless=True)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://flow.google.com/project/2805fba9-cb0b-4216-a690-8fe4c571cc06", wait_until="domcontentloaded")
    time.sleep(4)
    
    prev_m = page.locator("[aria-label*='model' i], [class*='model'], button:has-text('Omni'), button:has-text('Flash')").all()
    for el in prev_m:
        print("Element:", el.inner_text().replace("\n", " "), "| aria:", el.get_attribute("aria-label"), "| tag:", el.evaluate("e => e.tagName"))

    # Also inspect parent container of Previous model button
    p_btn = page.locator("button[aria-label='Previous model']").first
    if p_btn.count() > 0:
        parent_text = p_btn.evaluate("e => e.parentElement.innerText")
        print("Model selector container text:", parent_text.replace("\n", " "))
        
        # Click next model or inspect all children in parent
        children = p_btn.locator(".. > *").all()
        for c in children:
            print("Child in model container:", c.inner_text().replace("\n", " "), "| tag:", c.evaluate("e => e.tagName"), "| aria:", c.get_attribute("aria-label"))

    ctx.close()
