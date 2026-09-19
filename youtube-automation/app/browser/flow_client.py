import time
import os
import json
from typing import Optional, Tuple
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, Download
from app.utils.logger import get_logger

logger = get_logger("flow_client")


class FlowClient:
    """
    Client for interacting directly with the Google Flow web interface.
    Supports both seamless live waiting and instant project resumption.
    """
    def __init__(self, page: Page, flow_url: str = "https://flow.google.com/"):
        self.page = page
        self.flow_url = flow_url

    def open(self) -> None:
        """Navigates to the Google Flow interface."""
        logger.info(f"Navigating to Google Flow URL: {self.flow_url}")
        self.page.bring_to_front()
        self.page.goto(self.flow_url, wait_until="domcontentloaded")
        self.page.wait_for_timeout(3000)
        logger.info(f"Current URL: {self.page.url} | Title: {self.page.title()}")

    def is_authenticated(self) -> bool:
        """Checks if the user is authenticated in Google Flow."""
        current_url = self.page.url
        logger.debug(f"Checking authentication status. Current URL: {current_url}")

        if "accounts.google.com" in current_url or "signin" in current_url:
            return False

        if "flow.google.com" in current_url or "labs.google" in current_url:
            new_proj = self.page.get_by_text("New project")
            if new_proj.count() > 0 and new_proj.first.is_visible():
                return True

            avatar = self.page.locator("img[alt*='Google Account'], img[src*='googleusercontent.com'], button[aria-label*='Account'], [data-testid='user-avatar']")
            if avatar.count() > 0 and avatar.first.is_visible():
                return True

            if "/project/" in current_url:
                return True

            sign_in_locators = [
                "button:has-text('Sign in')",
                "a:has-text('Sign in')",
                "button:has-text('Log in')"
            ]
            for sel in sign_in_locators:
                loc = self.page.locator(sel)
                if loc.count() > 0 and loc.first.is_visible():
                    return False

            return True

        return False

    def wait_for_authentication(self, timeout_seconds: int = 600, poll_interval_seconds: int = 3) -> bool:
        """Polls until the user completes manual authentication."""
        if self.is_authenticated():
            logger.info("Authentication detected — session is active.")
            return True

        logger.warning(
            "\n"
            "=================================================================\n"
            "                  MANUAL ACTION REQUIRED:                        \n"
            "  Please sign into your Google Account in the opened browser!    \n"
            f"  Waiting up to {timeout_seconds}s for you to complete sign-in...         \n"
            "================================================================="
        )

        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            self.page.wait_for_timeout(poll_interval_seconds * 1000)
            if self.is_authenticated():
                logger.info("Authentication successfully detected! Session active.")
                self.page.wait_for_timeout(3000)
                return True

        logger.error("Authentication timed out. User did not complete login.")
        return False

    def dismiss_popups(self) -> None:
        """Dismisses any introductory popups, tooltips, or changelog dialogs."""
        dismiss_selectors = [
            "button:has-text('Get started')",
            "button:has-text('Got it')",
            "button[aria-label='Close']",
            "button[aria-label='Close account panel']",
            "button:has-text('Dismiss')"
        ]
        for sel in dismiss_selectors:
            try:
                btn = self.page.locator(sel)
                if btn.count() > 0 and btn.first.is_visible():
                    logger.debug(f"Dismissing modal/tooltip via selector: {sel}")
                    btn.first.click()
                    self.page.wait_for_timeout(500)
            except Exception:
                pass

    def navigate_to_create(self) -> str:
        """
        Opens a fresh project in Google Flow to ensure isolation for the job.
        Returns the project URL.
        """
        logger.info("Opening a new project canvas for this job...")
        try:
            if "/project/" in self.page.url:
                self.page.goto(self.flow_url, wait_until="domcontentloaded", timeout=45000)
                self.page.wait_for_timeout(3000)
        except Exception:
            try:
                self.page.goto(self.flow_url, wait_until="domcontentloaded", timeout=45000)
                self.page.wait_for_timeout(3000)
            except Exception as e:
                logger.warning(f"Note navigating to flow_url: {e}")

        new_proj_btn = self.page.locator("button:has-text('New project'), [aria-label*='New project'], [aria-label*='Create project'], button:has-text('add')")
        if new_proj_btn.count() > 0:
            new_proj_btn.first.click(force=True)
        else:
            self.page.get_by_text("New project").first.click(force=True)

        self.page.wait_for_url("**/project/**", timeout=25000)
        self.page.wait_for_timeout(3000)
        self.dismiss_popups()
        project_url = self.page.url
        logger.info(f"New project canvas ready! Project URL: {project_url}")
        return project_url

    def resume_project(self, project_url: str) -> None:
        """
        Navigates directly to an existing project URL to check/resume rendering or download.
        Zero credits used.
        """
        logger.info(f"Resuming existing project canvas: {project_url}")
        self.page.goto(project_url, wait_until="domcontentloaded")
        self.page.wait_for_timeout(4000)
        self.dismiss_popups()
        logger.info(f"Project canvas loaded: {self.page.title()}")

    def select_model(self, target_model: str = "Omni") -> None:
        """Explicitly selects the specified model (default: Omni / Gemini Omni / Omni 1.1 Flash) in Google Flow."""
        logger.info(f"Ensuring model is set to '{target_model}'...")
        try:
            # 1. Check if model is already set to target_model
            active_model_btn = self.page.locator(
                f"button:has-text('{target_model}'), [role='button']:has-text('{target_model}')"
            )
            if active_model_btn.count() > 0 and active_model_btn.first.is_visible():
                btn_txt = active_model_btn.first.inner_text().strip().replace('\n', ' ')
                logger.info(f"✓ Model '{target_model}' is already active: '{btn_txt}'")
                return

            # 2. Look for the model selection trigger button (e.g. pill at bottom right of prompt box)
            model_triggers = [
                "button[aria-label*='model' i]",
                "button:has-text('Agent')",
                "button:has-text('Veo')",
                "button:has-text('Nano')",
                "button:has-text('Imagen')",
                "button:has-text('Flash')",
                "div:has(> textarea, > [contenteditable]) ~ div button",
                "button:has(i:has-text('auto_awesome'))",
                "button:has(span:has-text('auto_awesome'))"
            ]

            trigger_clicked = False
            for sel in model_triggers:
                t_btn = self.page.locator(sel)
                if t_btn.count() > 0 and t_btn.first.is_visible():
                    logger.info(f"Opening model selector menu via '{sel}'...")
                    t_btn.first.click()
                    self.page.wait_for_timeout(800)
                    trigger_clicked = True
                    break

            # 3. Select Omni from the dropdown/menu
            omni_option = self.page.locator(
                f"[role='menuitem']:has-text('{target_model}'), "
                f"[role='option']:has-text('{target_model}'), "
                f"button:has-text('{target_model}'), "
                f"div:has-text('Gemini Omni'), "
                f"*:has-text('Omni 1.1 Flash')"
            ).first

            if omni_option.count() > 0 and omni_option.is_visible():
                logger.info(f"✓ Selected '{target_model}' from model menu.")
                omni_option.click(force=True)
                self.page.wait_for_timeout(600)
            elif trigger_clicked:
                # If menu opened but exact match locator wasn't found, check all visible menu items
                for item in self.page.locator("[role='menuitem'], [role='option'], div[class*='menu'] button").all():
                    try:
                        if target_model.lower() in item.inner_text().lower() and item.is_visible():
                            logger.info(f"✓ Selected '{item.inner_text().strip()}' from menu.")
                            item.click(force=True)
                            self.page.wait_for_timeout(600)
                            break
                    except Exception:
                        pass

        except Exception as e:
            logger.warning(f"Could not explicitly switch model to {target_model}: {e}")

    def configure_generation(self, aspect_ratio: str = "9:16", count: int = 1, model: str = "Omni", resolution: str = "720p", duration: str = "8s") -> None:
        """
        Configures generation parameters by locating the settings pill on the right side
        of the input bar (immediately preceding the submit arrow button), regardless of its text.
        Sets 9:16 vertical aspect ratio, x1 output count, 8s duration, and target resolution.
        """
        logger.info(f"Configuring generation settings: Aspect Ratio={aspect_ratio}, Count=x{count}, Model={model}, Resolution={resolution}, Duration={duration}")
        self.dismiss_popups()
        self.page.wait_for_timeout(1000)

        # 1. Select the model first if model pill is visible
        if model:
            self.select_model(model)

        settings_applied = False
        try:
            # 2. Locate the Video Generation Settings Pill by LOCATION inside the prompt input bar:
            # It is the interactive button located right next to the submit button (->)
            submit_btn = self.page.locator(
                "button[aria-label='Start generation'], button:has-text('arrow_forward'), button[type='submit']"
            ).first

            pill_btn = None

            # Strategy A: Find button preceding the submit button in the prompt container
            if submit_btn.count() > 0:
                preceding = submit_btn.locator("xpath=preceding-sibling::button[1]")
                if preceding.count() > 0 and preceding.first.is_visible():
                    pill_btn = preceding.first
                    logger.info(f"Found settings pill by location (preceding submit button): '{pill_btn.inner_text().strip().replace(chr(10), ' ')}'")

            # Strategy B: Find all buttons inside the prompt bar container and pick the rightmost one before submit
            if not pill_btn:
                prompt_container = self.page.locator(
                    "form, div:has(> div.ProseMirror), div:has(> [contenteditable='true']), div[class*='prompt']"
                ).last
                if prompt_container.count() > 0:
                    container_buttons = prompt_container.locator("button, [role='button']").all()
                    for b in reversed(container_buttons):
                        if b.is_visible():
                            aria = b.get_attribute("aria-label") or ""
                            txt = b.inner_text().strip().replace("\n", " ")
                            if "start generation" not in aria.lower() and "agent" not in txt.lower() and "submit" not in aria.lower():
                                pill_btn = b
                                logger.info(f"Found settings pill in prompt container: '{txt}'")
                                break

            # Strategy C: Fallback text/class matching for common pill states
            if not pill_btn:
                pill_selectors = [
                    "button[aria-label='Settings']",
                    "button[aria-label='Settings trigger']",
                    "button:has-text('tune')",
                    "button:has-text('Video')",
                    "button:has-text('360p')",
                    "button:has-text('720p')",
                    "button:has-text('8s')",
                    "button:has-text('x2')",
                    "button:has-text('x1')",
                    "[class*='pill']"
                ]
                for sel in pill_selectors:
                    c = self.page.locator(sel).first
                    if c.count() > 0 and c.is_visible():
                        pill_btn = c
                        logger.info(f"Found settings pill via fallback selector: '{sel}'")
                        break

            if pill_btn:
                logger.info("Clicking video settings pill button...")
                pill_btn.click(force=True)
                self.page.wait_for_timeout(1500)  # extra wait for popover to fully render

                # Take a debug screenshot of the open popover
                try:
                    import os
                    debug_dir = "./debug"
                    os.makedirs(debug_dir, exist_ok=True)
                    self.page.screenshot(path=os.path.join(debug_dir, "settings_popover_open.png"))
                    logger.info("Debug screenshot saved: debug/settings_popover_open.png")
                except Exception:
                    pass

                # Helper: click a setting option using multiple selector strategies
                def click_option(label: str, selectors: list) -> bool:
                    for sel in selectors:
                        try:
                            loc = self.page.locator(sel).first
                            if loc.count() > 0 and loc.is_visible():
                                loc.click(force=True)
                                logger.info(f"✓ Selected {label} via: {sel}")
                                self.page.wait_for_timeout(400)
                                return True
                        except Exception:
                            pass
                    logger.warning(f"✗ Could not find option for {label}")
                    return False

                # 0) Select Video mode (to ensure we are not in Image mode)
                click_option("mode=Video", [
                    "button:has-text('Video')",
                    "[role='tab']:has-text('Video')",
                    "[role='button']:has-text('Video')",
                    "div[role='tab']:has-text('Video')"
                ])
                self.page.wait_for_timeout(600)

                # a) Select aspect ratio (9:16)
                click_option(f"aspect ratio={aspect_ratio}", [
                    f"[role='radio']:has-text('{aspect_ratio}')",
                    f"button:has-text('{aspect_ratio}')",
                    f"[role='button']:has-text('{aspect_ratio}')",
                    f"[aria-label*='{aspect_ratio}']",
                    f"label:has-text('{aspect_ratio}')",
                ])

                # b) Select output count (x1)
                click_option(f"output count=x{count}", [
                    f"[role='radio']:has-text('x{count}')",
                    f"button:has-text('x{count}')",
                    f"[role='button']:has-text('x{count}')",
                    f"[aria-label*='x{count}']",
                    f"label:has-text('x{count}')",
                    f"[role='radio']:has-text('{count} output')",
                ])

                # c) Select resolution (720p)
                click_option(f"resolution={resolution}", [
                    f"[role='radio']:has-text('{resolution}')",
                    f"button:has-text('{resolution}')",
                    f"[role='button']:has-text('{resolution}')",
                    f"[aria-label*='{resolution}']",
                    f"label:has-text('{resolution}')",
                    f"input[value='{resolution}']",
                ])

                # d) Select duration (8s)
                if duration:
                    click_option(f"duration={duration}", [
                        f"[role='radio']:has-text('{duration}')",
                        f"button:has-text('{duration}')",
                        f"[role='button']:has-text('{duration}')",
                        f"[aria-label*='{duration}']",
                        f"label:has-text('{duration}')",
                        f"input[value='{duration}']",
                        f"[role='radio']:has-text('{duration[:-1]} sec')",
                        f"[role='option']:has-text('{duration}')",
                    ])

                # e) Select Model in popover if available
                if model:
                    click_option(f"model={model}", [
                        f"[role='radio']:has-text('{model}')",
                        f"button:has-text('{model}')",
                        f"[role='button']:has-text('{model}')",
                        f"[aria-label*='{model}']",
                    ])

                # f) Select 'Never' for approval prompts if present
                click_option("approval=Never", [
                    "input[type='radio'][value='never']",
                    "[role='radio']:has-text('Never')",
                    "label:has-text('Never')",
                ])

                # g) Save/Close popover
                save_btn = self.page.locator(
                    "button:has-text('Save'), button:has-text('Done'), button:has-text('Apply'), button:has-text('Confirm')"
                ).first
                if save_btn.count() > 0 and save_btn.is_visible():
                    save_btn.click(force=True)
                    logger.info("✓ Closed settings popover via Save/Done.")
                else:
                    self.page.keyboard.press("Escape")
                    self.page.wait_for_timeout(300)
                    # Also click outside the popover onto empty canvas area (x=400, y=200) to ensure popover closes
                    self.page.mouse.click(400, 200)
                    logger.info("✓ Closed settings popover via Escape & background click.")

                self.page.wait_for_timeout(500)
                settings_applied = True
                logger.info(f"Settings configuration complete. Applied: {aspect_ratio} | x{count} | {resolution} | {duration}")

            else:
                logger.warning("Could not find the prompt bar settings pill directly; checking fallback selectors...")
                # Fallback: check direct toolbar buttons
                ratio_direct = self.page.locator(f"button:has-text('{aspect_ratio}')")
                if ratio_direct.count() > 0 and ratio_direct.first.is_visible():
                    ratio_direct.first.click()
                    logger.info(f"✓ Selected aspect ratio directly on toolbar: {aspect_ratio}")

                count_direct = self.page.locator(f"button:has-text('x{count}')")
                if count_direct.count() > 0 and count_direct.first.is_visible():
                    count_direct.first.click()
                    logger.info(f"✓ Selected output count directly on toolbar: x{count}")

        except Exception as e:
            logger.warning(f"Could not adjust settings panel automatically: {e}")


    def enter_prompt(self, prompt: str) -> None:
        """Enters the prompt into the ProseMirror editor box."""
        logger.info(f"Entering prompt into prompt box ({len(prompt)} characters)...")
        self.dismiss_popups()

        # Try to locate the prompt input box using multiple selectors
        prompt_selectors = [
            "div.ProseMirror",
            "[contenteditable='true']",
            "textarea",
            "div[data-placeholder*='create' i]",
            "div[data-placeholder*='prompt' i]",
            "div:has-text('What do you want to create?')"
        ]

        target_box = None
        for sel in prompt_selectors:
            box = self.page.locator(sel).first
            if box.count() > 0 and box.is_visible():
                target_box = box
                logger.info(f"Found prompt input box via selector: '{sel}'")
                break

        if not target_box:
            # Fallback: click directly at the prompt bar coordinates at bottom of canvas (x=400, y=880)
            logger.info("Clicking prompt bar area by coordinates (x=400, y=880)...")
            self.page.mouse.click(400, 880)
            self.page.wait_for_timeout(400)
            target_box = self.page.locator("div.ProseMirror, [contenteditable='true']").first

        if not target_box or target_box.count() == 0:
            raise RuntimeError("Prompt input box not found on page!")

        target_box.click(force=True)
        self.page.wait_for_timeout(500)
        text_to_insert = prompt.strip()
        success = False

        # For large prompts (e.g. > 1000 chars), use fast clipboard / insert_text to avoid 30s fill timeout
        try:
            # Method 1: evaluate clipboard paste directly into ProseMirror
            success = self.page.evaluate("""(text) => {
                const el = document.querySelector('div.ProseMirror') || document.querySelector('[contenteditable="true"]');
                if (!el) return false;
                el.focus();
                document.execCommand('selectAll', false, null);
                document.execCommand('delete', false, null);
                const dt = new DataTransfer();
                dt.setData('text/plain', text);
                const evt = new ClipboardEvent('paste', { bubbles: true, cancelable: true, clipboardData: dt });
                el.dispatchEvent(evt);
                if (!el.textContent.trim()) {
                    document.execCommand('insertText', false, text);
                }
                el.dispatchEvent(new Event('input', { bubbles: true }));
                return el.textContent.trim().length > 0;
            }""", text_to_insert)
            if success:
                logger.info(f"Entered prompt via fast DOM/clipboard insertion ({len(text_to_insert)} chars).")
        except Exception as e:
            logger.warning(f"Fast DOM insertion failed: {e}")

        if not success:
            try:
                # Method 2: keyboard.insert_text (instant paste-level speed in Chromium)
                target_box.click(force=True)
                self.page.keyboard.press("Control+A")
                self.page.keyboard.press("Backspace")
                self.page.keyboard.insert_text(text_to_insert)
                self.page.wait_for_timeout(500)
                logger.info(f"Entered prompt via keyboard.insert_text ({len(text_to_insert)} chars).")
                success = True
            except Exception as e:
                logger.warning(f"keyboard.insert_text failed: {e}")

        if not success:
            # Method 3: standard fill with larger timeout
            target_box.fill(text_to_insert, timeout=60000)
            logger.info("Entered prompt via standard fill.")

        self.page.wait_for_timeout(1000)
        logger.info("Prompt entered successfully.")

    def handle_approval_if_present(self) -> bool:
        """
        Checks if the Flow Agent is asking for approval to spend credits,
        and clicks 'Always approve' or 'Approve'. Returns True if clicked.
        """
        try:
            # If video is already rendered on canvas or generation is active, approval not needed
            play_btn = self.page.locator("span:has-text('play_arrow'), [aria-label*='Play' i]")
            if play_btn.count() > 0 and play_btn.first.is_visible():
                return False

            # Ensure the right-side chat panel is scrolled to the bottom
            try:
                self.page.evaluate("""
                    () => {
                        const panels = document.querySelectorAll("div[class*='session'], div[class*='chat'], aside, div[role='region']");
                        panels.forEach(p => { p.scrollTop = p.scrollHeight; });
                        window.scrollTo(0, document.body.scrollHeight);
                    }
                """)
            except Exception:
                pass

            # Prioritize clicking "Always approve" first, then "Approve"
            for target_text in ["Always approve", "Approve"]:
                candidates = self.page.locator(
                    f"button:has-text('{target_text}'), [role='button']:has-text('{target_text}'), div:has-text('{target_text}')"
                )
                cnt = candidates.count()
                if cnt > 0:
                    for i in reversed(range(cnt)):
                        target = candidates.nth(i)
                        try:
                            if target.is_visible() and target.is_enabled():
                                # Check if it's already selected/confirmed (e.g. grayed out / disabled)
                                is_disabled = target.get_attribute("disabled") is not None
                                aria_pressed = target.get_attribute("aria-pressed")
                                aria_selected = target.get_attribute("aria-selected")
                                if is_disabled or aria_pressed == "true" or aria_selected == "true":
                                    continue

                                txt = target.inner_text().strip().replace("\n", " ")
                                logger.info(f"✓ Found clickable approval button ('{txt}'). Clicking now...")
                                target.scroll_into_view_if_needed(timeout=2000)
                                target.click(force=True, timeout=3000)
                                self.page.wait_for_timeout(1500)
                                logger.info(f"✓ Successfully clicked '{txt}'!")
                                return True
                        except Exception:
                            continue

        except Exception as e:
            logger.debug(f"Approval check bypassed: {e}")
        return False

    def handle_agent_question_or_approval(self) -> bool:
        """
        Handles both:
        1. Clickable approval cards ('Approve', 'Always approve')
        2. Conversational prompt questions ('Should I proceed...?', 'Do you want me to...?')
        """
        # 1. First try standard approval button clicks
        if self.handle_approval_if_present():
            return True

        # 2. Check for conversational questions in chat
        try:
            body_text = self.page.locator("body").inner_text()
            recent_text = body_text[-2000:].lower()

            question_triggers = [
                "should i proceed",
                "proceed with generating",
                "would you like me to",
                "do you want me to",
                "shall i proceed",
                "ready to generate"
            ]

            if any(trigger in recent_text for trigger in question_triggers):
                prompt_box = self.page.locator("div.ProseMirror, [contenteditable='true']")
                if prompt_box.count() > 0 and prompt_box.first.is_visible():
                    current_val = prompt_box.first.inner_text().strip()
                    if not current_val:  # only type if input is ready and empty
                        logger.info("✓ Flow Agent asked a confirmation question. Auto-replying 'Yes, directly generate the complete video now.'...")
                        prompt_box.first.click()
                        self.page.wait_for_timeout(400)
                        prompt_box.first.fill("Yes, directly generate the complete 10-second vertical 9:16 video scene now.")
                        self.page.wait_for_timeout(500)

                        gen_btn = self.page.locator("button[aria-label='Start generation'], button:has-text('arrow_forward'), button[type='submit']").first
                        if gen_btn.count() > 0 and gen_btn.is_visible():
                            gen_btn.click()
                        else:
                            self.page.keyboard.press("Enter")

                        logger.info("✓ Dispatched confirmation response to Flow Agent.")
                        self.page.wait_for_timeout(3000)
                        return True
        except Exception as e:
            logger.debug(f"Conversational question response check bypassed: {e}")

        return False

    def submit_generation(self) -> None:
        """
        Clicks the generate button, waits exactly 20 seconds for the Flow Agent
        to formulate its proposal, and then approves video generation.
        """
        logger.info("Submitting generation request (1 of 1)...")
        self.dismiss_popups()

        # Ensure focus in ProseMirror
        target_box = self.page.locator("div.ProseMirror, [contenteditable='true']").first
        if target_box.count() > 0 and target_box.is_visible():
            try:
                target_box.click(force=True)
                self.page.wait_for_timeout(200)
            except Exception:
                pass

        # 1. Try to find and click the circular submit button inside or adjacent to the prompt container
        clicked = False

        # Strategy A: JavaScript click on the rightmost button in the prompt container or any button containing arrow_forward/submit
        try:
            clicked = self.page.evaluate("""() => {
                const box = document.querySelector('div.ProseMirror') || document.querySelector('[contenteditable="true"]');
                if (!box) return false;
                let p = box.parentElement;
                while (p && p.querySelectorAll('button').length < 2 && p.parentElement && p.tagName !== 'BODY') {
                    p = p.parentElement;
                }
                if (p) {
                    const btns = Array.from(p.querySelectorAll('button')).filter(b => b.offsetWidth > 0 && b.offsetHeight > 0);
                    for (let i = btns.length - 1; i >= 0; i--) {
                        const b = btns[i];
                        const text = (b.innerText || '').toLowerCase();
                        const aria = (b.getAttribute('aria-label') || '').toLowerCase();
                        const html = b.innerHTML.toLowerCase();
                        if (text.includes('arrow_forward') || aria.includes('start') || aria.includes('send') || aria.includes('generate') || html.includes('arrow_forward') || html.includes('svg')) {
                            b.click();
                            return true;
                        }
                    }
                    if (btns.length > 0) {
                        btns[btns.length - 1].click();
                        return true;
                    }
                }
                return false;
            }""")
            if clicked:
                logger.info("✓ Submitted via prompt container submit button (JS evaluation).")
        except Exception as e:
            logger.debug(f"JS submit button click note: {e}")

        # Strategy B: If not clicked, try locator iteration over all visible buttons
        if not clicked:
            gen_btn = self.page.locator(
                "button[aria-label='Start generation'], button[aria-label*='generation' i], button[aria-label*='generate' i], "
                "button:has-text('arrow_forward'), button:has(i:has-text('arrow_forward')), button:has(span:has-text('arrow_forward')), "
                "button[type='submit'], button[aria-label='Create'], button:has-text('Create'), button[aria-label='Send'], button:has-text('Send')"
            )
            for i in range(gen_btn.count()):
                b = gen_btn.nth(i)
                try:
                    if b.is_visible() and b.is_enabled():
                        b.click(force=True)
                        clicked = True
                        logger.info(f"Generate button #{i} clicked via locator.")
                        break
                except Exception:
                    continue

        # Step 2: Wait 2.5 seconds for session panel to open, and click the session panel's submit button!
        self.page.wait_for_timeout(2500)
        session_clicked = False
        try:
            session_clicked = self.page.evaluate("""() => {
                const sidePanels = document.querySelectorAll("div[class*='session'], aside, div[role='region']");
                for (const panel of sidePanels) {
                    if (panel.offsetWidth > 0 && panel.offsetHeight > 0) {
                        const btns = Array.from(panel.querySelectorAll("button")).filter(b => b.offsetWidth > 0 && b.offsetHeight > 0);
                        for (let i = btns.length - 1; i >= 0; i--) {
                            const b = btns[i];
                            const aria = (b.getAttribute('aria-label') || '').toLowerCase();
                            const text = (b.innerText || '').toLowerCase();
                            const html = b.innerHTML.toLowerCase();
                            if (text.includes('arrow_forward') || aria.includes('send') || aria.includes('generate') || aria.includes('start') || html.includes('arrow_forward') || html.includes('svg')) {
                                b.click();
                                return true;
                            }
                        }
                    }
                }
                return false;
            }""")
            if session_clicked:
                logger.info("✓ Clicked submit button inside session side panel (JS evaluation).")
        except Exception as e:
            logger.debug(f"Session panel submit button click note: {e}")

        if not session_clicked:
            try:
                side_btn = self.page.locator("aside button:has(svg), div[class*='session'] button:has(svg), aside button:has-text('arrow_forward')").last
                if side_btn.count() > 0 and side_btn.is_visible():
                    side_btn.click(force=True)
                    logger.info("✓ Clicked session side panel submit button via locator.")
                else:
                    self.page.mouse.click(1240, 855)
                    logger.info("Clicked session submit button at (1240, 855).")
            except Exception:
                pass

        try:
            self.page.screenshot(path="debug/after_session_dispatched.png")
            logger.info("Saved screenshot: debug/after_session_dispatched.png")
        except Exception:
            pass

        # Exactly as specified: Wait 20 seconds after entering prompt before approving
        logger.info("Waiting 20 seconds for Flow Agent to formulate proposal...")
        self.page.wait_for_timeout(20000)

        # Now actively approve the proposal (try up to 15 times over 30s)
        logger.info("Approving video generation...")
        approved = False
        for attempt in range(1, 16):
            if self.handle_agent_question_or_approval():
                approved = True
                logger.info(f"✓ Approval successfully handled on attempt {attempt}.")
                break
            self.page.wait_for_timeout(2000)

        if not approved:
            logger.warning("Approval button not found in initial 30s window. Will continue checking during render monitoring...")

    def is_generation_finished(self, min_wait_elapsed: int, min_wait_required: int = 150) -> bool:
        """
        Determines if video rendering is finished.
        Requires at least min_wait_required (150s) to pass and verifies the playable video card.
        """
        if min_wait_elapsed < min_wait_required:
            return False

        # 1. Check if rendering stop button is still active
        stop_btn = self.page.locator("button:has-text('stop'), [aria-label*='Stop generation']")
        if stop_btn.count() > 0 and stop_btn.first.is_visible():
            return False

        # 2. Check for active spinners / progressbars
        spinners = self.page.locator("[role='progressbar'], .spinner, [aria-label*='Generating' i], [aria-label*='Rendering' i]")
        for i in range(spinners.count()):
            try:
                if spinners.nth(i).is_visible():
                    return False
            except Exception:
                pass

        # 3. Check if playable video card exists on canvas or in session
        play_icons = self.page.locator("span:has-text('play_arrow'), [aria-label*='Play' i], div.video-container, video, [data-testid*='video']")
        if play_icons.count() > 0:
            return True

        return False


    def wait_for_generation(
        self,
        timeout_seconds: int = 900,
        poll_interval_seconds: int = 5,
        min_wait_seconds: int = 150
    ) -> bool:
        """
        Monitors video rendering progress.
        Waits for 150 seconds for the render to complete before proceeding to download.
        """
        logger.info(
            f"Waiting 150 seconds for video rendering to finish (min guard: {min_wait_seconds}s, poll: {poll_interval_seconds}s)..."
        )
        start_time = time.time()
        last_log_time = time.time()

        while time.time() - start_time < timeout_seconds:
            self.page.wait_for_timeout(poll_interval_seconds * 1000)
            elapsed = int(time.time() - start_time)

            # Check for actual active error snackbars/toasts
            error_toasts = self.page.locator("mat-snack-bar-container, .cdk-overlay-container [role='alert'], div.toast-error")
            if error_toasts.count() > 0 and error_toasts.first.is_visible():
                error_text = error_toasts.first.inner_text().strip()
                if "Quota exceeded" in error_text or "blocked by policy" in error_text:
                    raise RuntimeError(f"Google Flow reported generation error: {error_text}")

            # Keep retrying approval if prompt proposal is pending
            self.handle_agent_question_or_approval()

            # Check if generation finished (with 150s elapsed guard)
            if self.is_generation_finished(min_wait_elapsed=elapsed, min_wait_required=min_wait_seconds):
                logger.info(f"✓ Generation completed! Video rendered successfully in {elapsed}s.")
                self.page.wait_for_timeout(2000)
                return True

            # Log progress every 30 seconds
            if time.time() - last_log_time >= 30:
                stop_btn = self.page.locator(
                    "button:has-text('stop'), [aria-label*='Stop generation' i], button:has(i:has-text('stop')), button:has(span:has-text('stop'))"
                )
                is_active = (stop_btn.count() > 0 and stop_btn.first.is_visible())
                logger.info(f"Rendering in Google Flow... ({elapsed}s / {min_wait_seconds}s elapsed | Cloud render active: {is_active})")
                last_log_time = time.time()

        logger.warning(f"Generation reached the {timeout_seconds}s wait limit.")
        return False

    def download_video(self, job_output_dir: str, resolution: str = "720p", max_retries: int = 3) -> str:
        """
        Locates the generated video in the Flow UI, triggers the download in 720p (Original size),
        and saves it to job_output_dir/video.mp4.
        Ensures ONLY the generated video (.mp4) is downloaded and images are ignored.
        """
        logger.info(f"Initiating download for the generated video in {resolution} (max retries: {max_retries})...")
        target_video_path = os.path.join(job_output_dir, "video.mp4")

        # Attempt 1 operates directly on the live canvas without reload
        self.dismiss_popups()

        for attempt in range(1, max_retries + 1):
            try:
                self.dismiss_popups()

                # Step 1: Switch to 'Videos' tab to filter out images
                videos_tab = self.page.locator(
                    "button:has-text('Videos'), [role='tab']:has-text('Videos'), span:has-text('videocam')"
                )
                if videos_tab.count() > 0 and videos_tab.first.is_visible():
                    try:
                        videos_tab.first.click()
                        self.page.wait_for_timeout(1500)
                    except Exception:
                        pass

                # Step 2: Set up response listener to intercept direct MP4 video streams
                captured_body = []
                def on_response(response):
                    try:
                        ct = response.headers.get("content-type", "")
                        url = response.url
                        if ("video/mp4" in ct or "flow-content.google/video" in url) and len(captured_body) == 0:
                            b = response.body()
                            if len(b) > 100000:
                                captured_body.append(b)
                    except Exception:
                        pass

                self.page.on("response", on_response)

                # Step 3: Find video card on canvas and right click to open context menu
                click_x, click_y = 250, 280
                card_loc = self.page.locator("video, [data-testid*='video'], [class*='asset-card'], [class*='card'], [role='article']").first
                if card_loc.count() > 0 and card_loc.is_visible():
                    try:
                        box = card_loc.bounding_box()
                        if box and box["width"] > 20 and box["height"] > 20:
                            click_x = int(box["x"] + box["width"] / 2)
                            click_y = int(box["y"] + box["height"] / 2)
                            logger.info(f"Targeting detected video card at ({click_x}, {click_y})")
                    except Exception:
                        pass

                logger.info(f"[Attempt {attempt}/{max_retries}] Opening context menu at ({click_x}, {click_y})...")
                self.page.mouse.click(click_x, click_y, button="right")
                self.page.wait_for_timeout(1200)

                # Step 4: Hover Download item in context menu to expand submenu
                dl_item = self.page.locator(
                    "div[role='menuitem']:has-text('Download'), [role='menuitem']:has-text('Download'), button:has-text('Download')"
                ).first
                if dl_item.count() > 0 and dl_item.is_visible():
                    dl_box = dl_item.bounding_box()
                    if dl_box:
                        # Move directly to Download menu item
                        self.page.mouse.move(dl_box["x"] + dl_box["width"] / 2, dl_box["y"] + dl_box["height"] / 2)
                        self.page.wait_for_timeout(600)
                        # Hover over the arrow / slide into submenu
                        self.page.mouse.move(dl_box["x"] + dl_box["width"] + 25, dl_box["y"] + dl_box["height"] / 2)
                        self.page.wait_for_timeout(800)

                # Step 5: Click '720p Original size' option in submenu
                target_opt = self.page.locator(
                    "div[role='menuitem']:has-text('720p'), [role='menuitem']:has-text('Original size'), button:has-text('720p'), [role='menuitem']:has-text('720p')"
                ).first
                if target_opt.count() > 0 and target_opt.is_visible():
                    logger.info("Found '720p Original size' in submenu. Clicking to download...")
                    try:
                        with self.page.expect_download(timeout=30000) as dl_info:
                            target_opt.click()
                        dl = dl_info.value
                        dl.save_as(target_video_path)
                        self.page.wait_for_timeout(2000)
                    except Exception as e:
                        logger.debug(f"Direct download trigger caught exception: {e}")
                else:
                    # Target by exact submenu bounding box if submenu is visible
                    sub_item = self.page.locator("text='720p'").first
                    if sub_item.count() > 0 and sub_item.is_visible():
                        logger.info("✓ Clicking 720p text element directly...")
                        try:
                            with self.page.expect_download(timeout=20000) as dl_info:
                                sub_item.click()
                            dl = dl_info.value
                            dl.save_as(target_video_path)
                        except Exception:
                            pass

                # Check if captured via direct network stream
                if not os.path.exists(target_video_path) and len(captured_body) > 0:
                    with open(target_video_path, "wb") as f:
                        f.write(captured_body[0])
                    logger.info("Saved video directly from intercepted Google Flow media stream.")

                # Check if file was downloaded to default Downloads directory (supports .mp4, .tmp, .crdownload with ftyp)
                if not os.path.exists(target_video_path):
                    downloads_dir = os.path.expanduser(r"~\Downloads")
                    if os.path.exists(downloads_dir):
                        for fname in os.listdir(downloads_dir):
                            fpath = os.path.join(downloads_dir, fname)
                            try:
                                if os.path.isfile(fpath) and (time.time() - os.path.getmtime(fpath) < 300) and (os.path.getsize(fpath) > 100000):
                                    is_mp4 = fname.endswith(".mp4")
                                    if not is_mp4:
                                        with open(fpath, "rb") as fp:
                                            magic = fp.read(16)
                                        if b"ftyp" in magic:
                                            is_mp4 = True
                                    if is_mp4:
                                        import shutil
                                        shutil.copy2(fpath, target_video_path)
                                        logger.info(f"✓ Captured recently downloaded video from Downloads folder: {fname} ({round(os.path.getsize(target_video_path)/(1024*1024), 2)} MB)")
                                        break
                            except Exception:
                                pass

                # Step 2b: Try extracting video directly from DOM <video> element blob/src
                try:
                    video_src = self.page.evaluate('''() => {
                        const v = document.querySelector('video');
                        return v ? (v.currentSrc || v.src) : null;
                    }''')
                    if video_src and video_src.startswith('blob:'):
                        logger.info("Found DOM <video> blob source. Extracting directly...")
                        b64_data = self.page.evaluate('''async (blobUrl) => {
                            try {
                                const res = await fetch(blobUrl);
                                const blob = await res.blob();
                                return new Promise((resolve) => {
                                    const reader = new FileReader();
                                    reader.onloadend = () => resolve(reader.result.split(',')[1]);
                                    reader.readAsDataURL(blob);
                                });
                            } catch (e) {
                                return null;
                            }
                        }''', video_src)
                        if b64_data:
                            import base64
                            video_bytes = base64.b64decode(b64_data)
                            if len(video_bytes) > 100000:
                                with open(target_video_path, "wb") as f:
                                    f.write(video_bytes)
                                logger.info("✓ Successfully extracted video directly from DOM <video> blob element.")
                except Exception as e:
                    logger.debug(f"DOM video blob extraction note: {e}")

                def is_valid_mp4(p: str) -> bool:
                    if not os.path.exists(p) or os.path.getsize(p) < 100000:
                        return False
                    try:
                        with open(p, "rb") as fp:
                            return b"ftyp" in fp.read(16)
                    except Exception:
                        return False

                if is_valid_mp4(target_video_path):
                    file_size_mb = round(os.path.getsize(target_video_path) / (1024 * 1024), 2)
                    logger.info(f"✓ Video verified and successfully saved to: {target_video_path} ({file_size_mb} MB)")
                    return target_video_path

                # Fallback: Open modal and click Download button
                logger.info("Falling back to modal toolbar download...")
                self.page.mouse.click(click_x, click_y)
                self.page.wait_for_timeout(2500)

                # Try DOM video extraction in modal
                try:
                    video_src = self.page.evaluate('''() => {
                        const v = document.querySelector('video');
                        return v ? (v.currentSrc || v.src) : null;
                    }''')
                    if video_src and video_src.startswith('blob:'):
                        logger.info("Found DOM <video> blob source in modal. Extracting directly...")
                        b64_data = self.page.evaluate('''async (blobUrl) => {
                            try {
                                const res = await fetch(blobUrl);
                                const blob = await res.blob();
                                return new Promise((resolve) => {
                                    const reader = new FileReader();
                                    reader.onloadend = () => resolve(reader.result.split(',')[1]);
                                    reader.readAsDataURL(blob);
                                });
                            } catch (e) {
                                return null;
                            }
                        }''', video_src)
                        if b64_data:
                            import base64
                            vbytes = base64.b64decode(b64_data)
                            if len(vbytes) > 100000 and b"ftyp" in vbytes[:16]:
                                with open(target_video_path, "wb") as f:
                                    f.write(vbytes)
                                logger.info("✓ Successfully extracted video directly from modal DOM <video> blob.")
                                return target_video_path
                except Exception as e:
                    logger.debug(f"Modal DOM video blob extraction note: {e}")

                dl_btn = self.page.locator("button[aria-label='Download scene'], button[aria-label*='Download'], button:has-text('download'), [aria-label*='Download']").first
                if dl_btn.count() > 0 and dl_btn.is_visible():
                    logger.info("Clicking modal download button...")
                    dl_btn.click(force=True)
                    self.page.wait_for_timeout(1200)

                    pop_opt = self.page.locator("button:has-text('720p'), [role='menuitem']:has-text('720p'), button:has-text('Original size'), [role='menuitem']:has-text('Original size'), *:has-text('Original size'), *:has-text('720p')").first
                    if pop_opt.count() > 0 and pop_opt.is_visible():
                        logger.info("Found resolution popover option. Clicking to download...")
                        with self.page.expect_download(timeout=60000) as dl_info:
                            pop_opt.click(force=True)
                        dl = dl_info.value
                        dl.save_as(target_video_path)
                    else:
                        with self.page.expect_download(timeout=30000) as dl_info:
                            dl_btn.click(force=True)
                        dl = dl_info.value
                        dl.save_as(target_video_path)

                if is_valid_mp4(target_video_path):
                    file_size_mb = round(os.path.getsize(target_video_path) / (1024 * 1024), 2)
                    logger.info(f"✓ Video saved via modal toolbar: {target_video_path} ({file_size_mb} MB)")
                    return target_video_path

                if os.path.exists(target_video_path) and not is_valid_mp4(target_video_path):
                    try:
                        os.remove(target_video_path)
                    except Exception:
                        pass

                raise RuntimeError("Video file was not created or was not a valid MP4.")

            except Exception as e:
                logger.warning(f"Download attempt {attempt}/{max_retries} failed: {e}")
                if attempt < max_retries:
                    logger.info("Reloading Google Flow tab and retrying download...")
                    self.page.reload(wait_until="domcontentloaded")
                    self.page.wait_for_timeout(4000)
                    self.dismiss_popups()
                else:
                    raise RuntimeError(f"Failed to download video after {max_retries} attempts: {e}")

        return target_video_path

