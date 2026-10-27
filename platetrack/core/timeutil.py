"""Small time helpers shared by core and UI."""
from __future__ import annotations

from datetime import datetime, timedelta

ISO_FMT = "%Y-%m-%d %H:%M:%S"


def now_local() -> datetime:
    return datetime.now()


def iso(dt: datetime) -> str:
    return dt.strftime(ISO_FMT)


def parse_iso(text: str) -> datetime:
    return datetime.strptime(text, ISO_FMT)


def fmt_duration(seconds) -> str:
    """Seconds -> ``HH:MM:SS`` (negative/None -> empty string)."""
    if seconds is None:
        return ""
    seconds = int(round(seconds))
    if seconds < 0:
        seconds = 0
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def start_of_today() -> datetime:
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)


def start_of_week() -> datetime:
    """Monday 00:00 of the current week."""
    today = start_of_today()
    return today - timedelta(days=today.weekday())


def start_of_month() -> datetime:
    return datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
