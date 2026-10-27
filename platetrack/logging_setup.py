"""Logging setup: rotating file in the user AppData folder + console output."""
from __future__ import annotations

import logging
import logging.handlers
import sys

from .core import paths

LOG_FORMAT = "%(asctime)s  %(levelname)-8s  %(name)-22s  %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure the root logger. Safe to call more than once."""
    root = logging.getLogger()
    if getattr(root, "_platetrack_configured", False):
        return root

    root.setLevel(logging.DEBUG)
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    file_handler = logging.handlers.RotatingFileHandler(
        paths.logs_dir() / "platetrack.log",
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(formatter)
    root.addHandler(console)

    root._platetrack_configured = True  # type: ignore[attr-defined]

    # Log uncaught exceptions instead of dying silently.
    def _hook(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        root.critical("Uncaught exception", exc_info=(exc_type, exc, tb))

    sys.excepthook = _hook

    logging.getLogger(__name__).info("Logging initialised (data dir: %s)", paths.app_data_dir())
    return root
