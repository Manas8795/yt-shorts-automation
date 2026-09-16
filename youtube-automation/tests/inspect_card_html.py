import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.browser.browser_manager import BrowserManager

def inspect_card_html():
    mgr = BrowserManager(headless=True)
    page = mgr.launch()
    
    page.goto("https://flow.google.com/project/4c894033-8593-4677-844e-506bc7b67657", wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    
    # Extract outer HTML of all card/grid elements
    cards = page.locator("div:has(> [style*='background']), [role='gridcell'], div[tabindex='0']")
    print(f"Found {cards.count()} matching elements:")
    for i in range(min(cards.count(), 10)):
        el = cards.nth(i)
        html = el.evaluate("e => e.outerHTML")
        print(f"\n--- ELEMENT [{i}] HTML (truncated 500 chars) ---")
        print(html[:500])

    mgr.close()

if __name__ == "__main__":
    inspect_card_html()
