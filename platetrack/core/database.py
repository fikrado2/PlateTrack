"""SQLite schema and basic DAO for PlateTrack.

All paths live under ``platetrack/paths.py``.  The database holds:

* visits: one row per vehicle visit (entry+exit times, plate, etc.)
* settings: key-value store for the running configuration
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

from . import paths

VISIT_SCHEMA = """
CREATE TABLE IF NOT EXISTS visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plate TEXT NOT NULL,
    entry_time TEXT NOT NULL,
    exit_time TEXT,
    duration_seconds INTEGER,
    confidence REAL,
    snapshot_path TEXT,
    camera_source TEXT
);
"""

SETTINGS_SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

# default settings (overridden by values in the DB)
DEFAULT_SETTINGS = {
    "camera_source": "",           # last used source string
    "confidence_threshold": "0.5",
    "exit_timeout_seconds": "30",
    "detection_zone": "[]",        # JSON list of [[x1,y1],[x2,y2],...] in pixel coords
    "plate_format_preset": "generic",
    "plate_format_custom_regex": "",
    "dark_mode": "0",
    "watchlist": "[]",             # JSON list of plate strings
    "watchlist_sound": "",         # path to .wav file
    "save_snapshots": "1",
}


@dataclass
class Visit:
    id: int
    plate: str
    entry_time: datetime
    exit_time: Optional[datetime]
    duration_seconds: Optional[int]
    confidence: float
    snapshot_path: Optional[Path]
    camera_source: str

    @staticmethod
    def from_row(row: sqlite3.Row) -> "Visit":
        return Visit(
            id=row["id"],
            plate=row["plate"],
            entry_time=datetime.strptime(row["entry_time"], "%Y-%m-%d %H:%M:%S"),
            exit_time=(
                datetime.strptime(row["exit_time"], "%Y-%m-%d %H:%M:%S")
                if row["exit_time"]
                else None
            ),
            duration_seconds=row["duration_seconds"],
            confidence=row["confidence"],
            snapshot_path=Path(row["snapshot_path"]) if row["snapshot_path"] else None,
            camera_source=row["camera_source"] or "",
        )


def _connect() -> sqlite3.Connection:
    db_file = paths.database_file()
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_file, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    # enable foreign keys (not used yet but good practice)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Yield a connection and commit/rollback on exit."""
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if missing and insert default settings."""
    with get_db() as conn:
        conn.executescript(VISIT_SCHEMA + SETTINGS_SCHEMA)
        # upsert defaults
        for k, v in DEFAULT_SETTINGS.items():
            conn.execute(
                """
                INSERT INTO settings(key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (k, v),
            )


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    with get_db() as conn:
        cur = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        )
        row = cur.fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO settings(key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )


def add_visit(
    plate: str,
    entry_time: datetime,
    confidence: float,
    snapshot_path: Optional[Path] = None,
    camera_source: str = "",
) -> int:
    """Insert a new visit (entry only) and return its ID."""
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO visits
                (plate, entry_time, confidence, snapshot_path, camera_source)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                plate,
                entry_time.strftime("%Y-%m-%d %H:%M:%S"),
                confidence,
                str(snapshot_path) if snapshot_path else None,
                camera_source,
            ),
        )
        return cur.lastrowid


def update_exit(visit_id: int, exit_time: datetime) -> None:
    """Set exit time and duration for an existing visit."""
    with get_db() as conn:
        conn.execute(
            """
            UPDATE visits
            SET exit_time = ?,
                duration_seconds = CAST((julianday(?) - julianday(entry_time)) * 86400 AS INTEGER)
            WHERE id = ?
            """,
            (
                exit_time.strftime("%Y-%m-%d %H:%M:%S"),
                exit_time.strftime("%Y-%m-%d %H:%M:%S"),
                visit_id,
            ),
        )


def get_visit(visit_id: int) -> Optional[Visit]:
    with get_db() as conn:
        cur = conn.execute("SELECT * FROM visits WHERE id = ?", (visit_id,))
        row = cur.fetchone()
        return Visit.from_row(row) if row else None


def get_visits(
    limit: int = 100,
    offset: int = 0,
    plate_like: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> list[Visit]:
    """Return visits ordered by entry_time DESC with optional filters."""
    where = []
    params: list = []
    if plate_like:
        where.append("plate LIKE ?")
        params.append(f"%{plate_like}%")
    if start_date:
        where.append("entry_time >= ?")
        params.append(start_date.strftime("%Y-%m-%d %H:%M:%S"))
    if end_date:
        where.append("entry_time < ?")
        params.append(end_date.strftime("%Y-%m-%d %H:%M:%S"))
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    sql = f"""
        SELECT * FROM visits
        {where_sql}
        ORDER BY entry_time DESC
        LIMIT ? OFFSET ?
    """
    with get_db() as conn:
        cur = conn.execute(sql, (*params, limit, offset))
        return [Visit.from_row(row) for row in cur.fetchall()]


def delete_visit(visit_id: int) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM visits WHERE id = ?", (visit_id,))


def visits_today() -> int:
    with get_db() as conn:
        cur = conn.execute(
            """
            SELECT COUNT(*) FROM visits
            WHERE entry_time >= date('now')
            """
        )
        return cur.fetchone()[0]


def visits_week() -> int:
    with get_db() as conn:
        cur = conn.execute(
            """
            SELECT COUNT(*) FROM visits
            WHERE entry_time >= date('now', 'weekday 0', '-7 days')
            """
        )
        return cur.fetchone()[0]


def visits_month() -> int:
    with get_db() as conn:
        cur = conn.execute(
            """
            SELECT COUNT(*) FROM visits
            WHERE entry_time >= date('now', 'start of month')
            """
        )
        return cur.fetchone()[0]


def visits_total() -> int:
    with get_db() as conn:
        cur = conn.execute("SELECT COUNT(*) FROM visits")
        return cur.fetchone()[0]


def visits_inside_now(exit_timeout_seconds: int = 30) -> int:
    """Count visits that have an entry time but no exit time yet, and whose
    last seen time is within the exit timeout (we approximate: if exit_time is
    NULL, the car is still inside)."""
    with get_db() as conn:
        cur = conn.execute(
            """
            SELECT COUNT(*) FROM visits
            WHERE exit_time IS NULL
            """
        )
        return cur.fetchone()[0]
