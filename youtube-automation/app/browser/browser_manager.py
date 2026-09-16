import os
from datetime import datetime
from typing import Optional, Any
from playwright.sync_api import sync_playwright, Playwright, BrowserContext, Page
from app.utils.logger import get_logger

logger = get_logger("browser_manager")


class BrowserManager:
    def __init__(
        self,
        profile_directory: str = "./browser_profile",
        headless: bool = False,
        slow_mo_ms: int = 0,
        viewport_width: int = 1280,
        viewport_height: int = 900,
        default_timeout_ms: int = 30000,
        debug_directory: str = "./debug"
    ):
        self.profile_directory = os.path.abspath(profile_directory)
        self.headless = headless
        self.slow_mo_ms = slow_mo_ms
        self.viewport = {"width": viewport_width, "height": viewport_height}
        self.default_timeout_ms = default_timeout_ms
        self.debug_directory = os.path.abspath(debug_directory)

        self._playwright: Optional[Playwright] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def _cleanup_stale_locks(self) -> None:
        """Removes stale Chromium lock files safely without terminating user Chrome processes."""
        lock_files = ["lockfile", "SingletonLock", "SingletonCookie", "SingletonSocket"]
        for lock_name in lock_files:
            lock_path = os.path.join(self.profile_directory, lock_name)
            if os.path.exists(lock_path):
                try:
                    os.remove(lock_path)
                    logger.debug(f"Removed stale browser lock: {lock_path}")
                except Exception:
                    # Target ONLY orphaned chrome processes using this exact automation profile directory
                    try:
                        import subprocess
                        import time
                        norm_profile = os.path.normpath(self.profile_directory).replace('\\', '\\\\')
                        cmd = f"Get-CimInstance Win32_Process -Filter \"Name = 'chrome.exe'\" | Where-Object {{ $_.CommandLine -like '*{norm_profile}*' }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}"
                        subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True)
                        time.sleep(1.0)
                        if os.path.exists(lock_path):
                            os.remove(lock_path)
                            logger.debug(f"Removed browser lock after stopping orphaned automation process: {lock_path}")
                    except Exception as e:
                        logger.debug(f"Could not remove lock file {lock_path}: {e}")

    def launch(self) -> Page:
        """
        Launches Chromium with persistent context to preserve auth.
        Opens a dedicated tab for automation and preserves all existing user tabs.
        """
        os.makedirs(self.profile_directory, exist_ok=True)
        os.makedirs(self.debug_directory, exist_ok=True)
        self._cleanup_stale_locks()

        logger.info(f"Launching Chromium browser with persistent profile at: {self.profile_directory}")
        self._playwright = sync_playwright().start()

        self.context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=self.profile_directory,
            headless=self.headless,
            channel="chrome",
            accept_downloads=True,
            slow_mo=self.slow_mo_ms,
            viewport=self.viewport,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--no-first-run",
                "--disable-session-crashed-bubble",
                "--disable-restore-session-state"
            ]
        )
        self.context.set_default_timeout(self.default_timeout_ms)

        # Do NOT close existing user tabs. Open a dedicated new tab for automation.
        self.page = self.context.new_page()
        self.page.bring_to_front()
        logger.info("Automation page opened successfully (preserving existing tabs).")
        return self.page

    def capture_debug_screenshot(self, tag: str = "debug") -> str:
        """Captures a screenshot to the debug folder on error or inspection."""
        os.makedirs(self.debug_directory, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{timestamp}_{tag}.png"
        filepath = os.path.join(self.debug_directory, filename)
        if self.page:
            try:
                self.page.screenshot(path=filepath, full_page=True)
                logger.info(f"Saved debug screenshot: {filepath}")
            except Exception as e:
                logger.warning(f"Could not capture debug screenshot: {e}")
        return filepath

    def close(self) -> None:
        """Closes ONLY the tab opened by this automation, preserving user's other tabs and windows."""
        logger.info("Closing automation tab...")
        if self.page:
            try:
                if not self.page.is_closed():
                    self.page.close()
            except Exception as e:
                logger.debug(f"Error closing automation page: {e}")
            self.page = None

        # Only close the context if there are no other user tabs/windows remaining
        if self.context:
            try:
                open_pages = [p for p in self.context.pages if not p.is_closed()]
                if len(open_pages) == 0:
                    self.context.close()
            except Exception as e:
                logger.debug(f"Error closing context: {e}")
            self.context = None

        if self._playwright:
            try:
                self._playwright.stop()
            except Exception as e:
                logger.debug(f"Error stopping playwright: {e}")
            self._playwright = None
        logger.info("Automation session finished without affecting other tabs.")
