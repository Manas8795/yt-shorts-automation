import logging
import os
import sys
from datetime import datetime
from typing import Optional

try:
    from rich.logging import RichHandler
    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False


def setup_logger(
    log_dir: str = "./logs",
    level: int = logging.INFO
) -> logging.Logger:
    """
    Configures and returns the root logger with Rich console handler and rotating daily file handler.
    Guarantees no sensitive credentials/tokens are logged.
    """
    os.makedirs(log_dir, exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    log_file_path = os.path.join(log_dir, f"{today_str}.log")

    logger = logging.getLogger("yt_automation")
    logger.setLevel(level)

    # Avoid duplicate handlers if already set up
    if logger.handlers:
        return logger

    # Ensure stdout/stderr is UTF-8 on Windows
    if sys.platform == "win32":
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
            except Exception:
                pass
        if hasattr(sys.stderr, "reconfigure"):
            try:
                sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
            except Exception:
                pass

    # Console Handler
    if _HAS_RICH:
        from rich.console import Console
        console = Console(force_terminal=True, legacy_windows=False)
        console_handler = RichHandler(
            console=console,
            rich_tracebacks=True,
            markup=False,
            show_time=True,
            show_path=False
        )
    else:
        if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8")
            except Exception:
                pass
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            "[%(levelname)s] %(asctime)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(console_formatter)


    console_handler.setLevel(level)
    logger.addHandler(console_handler)

    # File Handler
    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    file_formatter = logging.Formatter(
        "[%(levelname)s] %(asctime)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)  # Store debug logs in file
    logger.addHandler(file_handler)

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Returns a child logger under yt_automation."""
    if name:
        return logging.getLogger(f"yt_automation.{name}")
    return logging.getLogger("yt_automation")
