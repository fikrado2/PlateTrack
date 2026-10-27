"""Filesystem locations for PlateTrack.

All user-writable data (SQLite database, snapshots, logs, exports, downloaded
models) lives in a per-user application-data folder — on Windows that is
``%APPDATA%\\PlateTrack`` — never in the installation folder, so installing a
new version or uninstalling never touches user data.

The environment variable ``PLATETRACK_DATA_DIR`` overrides the data folder
(used by the automated tests to run against a throwaway directory).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ENV_OVERRIDE = "PLATETRACK_DATA_DIR"

_data_dir: Path | None = None


def base_path() -> Path:
    """Repository / frozen-application base directory."""
    if getattr(sys, "frozen", False):  # running from the PyInstaller bundle
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_path(relative: str) -> Path:
    """Absolute path of a bundled resource such as ``assets/icon.ico``.

    In a PyInstaller build, data files are unpacked to ``sys._MEIPASS``.
    """
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass) / relative
        return Path(sys.executable).resolve().parent / relative
    return base_path() / relative


def app_data_dir() -> Path:
    """Per-user writable data folder (created on first call)."""
    global _data_dir
    if _data_dir is None:
        override = os.environ.get(_ENV_OVERRIDE)
        if override:
            _data_dir = Path(override)
        elif os.name == "nt":
            appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
            _data_dir = Path(appdata) / "PlateTrack"
        else:  # macOS / Linux development
            _data_dir = Path.home() / ".local" / "share" / "PlateTrack"
        _data_dir.mkdir(parents=True, exist_ok=True)
    return _data_dir


def _sub(name: str) -> Path:
    p = app_data_dir() / name
    p.mkdir(parents=True, exist_ok=True)
    return p


def db_dir() -> Path:
    return _sub("database")


def snapshots_dir() -> Path:
    return _sub("snapshots")


def logs_dir() -> Path:
    return _sub("logs")


def exports_dir() -> Path:
    return _sub("exports")


def models_dir() -> Path:
    return _sub("models")


def database_file() -> Path:
    return db_dir() / "platetrack.db"
