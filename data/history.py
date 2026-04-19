#!/usr/bin/env python3
"""
Relay Activity History (SQLite)

Persists a record of every relay activity (opened_at, duration_s, mode)
using a single-write-on-close strategy. Designed to be Raspberry Pi /
SD-card friendly (WAL journal, synchronous=NORMAL, short-lived
connections).

Public API:
    - init_history_db()
    - log_relay_close(relay_id, opened_at, mode)
    - log_current_relay_close(mode=None)
    - list_history(page, page_size, relay_id, start, end)
    - get_stats(period, year, month)
"""

import os
import sqlite3
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("arrosage_history")

VALID_MODES = ("auto", "semi_auto", "manual")

_DB_FILENAME = "history.db"
_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), _DB_FILENAME)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS relay_activity (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    relay_id    INTEGER NOT NULL CHECK (relay_id BETWEEN 0 AND 7),
    opened_at   INTEGER NOT NULL,
    duration_s  INTEGER NOT NULL CHECK (duration_s >= 0),
    mode        TEXT NOT NULL CHECK (mode IN ('auto','semi_auto','manual'))
);
CREATE INDEX IF NOT EXISTS idx_relay_activity_opened_at ON relay_activity(opened_at);
CREATE INDEX IF NOT EXISTS idx_relay_activity_relay_id  ON relay_activity(relay_id);
"""


def _connect() -> sqlite3.Connection:
    """Open a short-lived SQLite connection with Pi-friendly pragmas."""
    conn = sqlite3.connect(_DB_PATH, timeout=5.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_history_db() -> None:
    """Create the history DB file and schema if missing. Idempotent."""
    try:
        os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
        with _connect() as conn:
            conn.executescript(_SCHEMA_SQL)
        logger.info(f"History DB ready at {_DB_PATH}")
    except Exception as e:
        logger.error(f"Failed to initialize history DB: {e}")


def log_relay_close(relay_id: int, opened_at: int, mode: str) -> bool:
    """
    Insert a single row recording that `relay_id` was open from `opened_at`
    until now, in `mode`. Never raises.
    """
    try:
        if not isinstance(relay_id, int) or relay_id < 0 or relay_id > 7:
            logger.warning(f"log_relay_close: invalid relay_id {relay_id}")
            return False
        if not isinstance(opened_at, (int, float)) or opened_at <= 0:
            logger.warning(f"log_relay_close: invalid opened_at {opened_at}")
            return False
        if mode not in VALID_MODES:
            logger.warning(f"log_relay_close: invalid mode {mode!r}")
            return False

        duration_s = max(0, int(time.time()) - int(opened_at))

        with _connect() as conn:
            conn.execute("BEGIN IMMEDIATE;")
            conn.execute(
                "INSERT INTO relay_activity (relay_id, opened_at, duration_s, mode) "
                "VALUES (?, ?, ?, ?);",
                (int(relay_id), int(opened_at), duration_s, mode),
            )
            conn.execute("COMMIT;")

        logger.info(
            f"History row inserted: relay={relay_id} opened_at={opened_at} "
            f"duration_s={duration_s} mode={mode}"
        )
        return True

    except Exception as e:
        logger.error(f"log_relay_close failed: {e}")
        return False


def _normalize_mode(mode: Optional[str]) -> Optional[str]:
    """Map Redis mode strings onto history mode values."""
    if mode is None:
        return None
    if mode in VALID_MODES:
        return mode
    # Redis mode constants happen to match; 'pause' is not a valid activity
    # mode (no relay should be open while paused). Fall back to None.
    if mode == "pause":
        return None
    return None


def log_current_relay_close(mode: Optional[str] = None) -> bool:
    """
    Read the current Redis status and, if a relay is open, insert a
    corresponding history row. If `mode` is omitted, it is derived from
    Redis. No-op if no relay is currently open.
    """
    try:
        # Local imports avoid circulars at module-load time.
        from data.status import get_status

        status = get_status()
        if status is None:
            return False

        opened_relay = status.get("opened_relay")
        opened_at = status.get("opened_at")
        if not isinstance(opened_relay, int) or not isinstance(opened_at, (int, float)):
            return False

        resolved_mode = _normalize_mode(mode)
        if resolved_mode is None:
            try:
                from data.mode import get_mode
                resolved_mode = _normalize_mode(get_mode())
            except Exception:
                resolved_mode = None

        if resolved_mode is None:
            logger.warning(
                "log_current_relay_close: could not resolve a valid mode; skipping"
            )
            return False

        return log_relay_close(int(opened_relay), int(opened_at), resolved_mode)

    except Exception as e:
        logger.error(f"log_current_relay_close failed: {e}")
        return False


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "relay_id": row["relay_id"],
        "opened_at": row["opened_at"],
        "duration_s": row["duration_s"],
        "mode": row["mode"],
    }


def list_history(
    page: int = 1,
    page_size: int = 100,
    relay_id: Optional[int] = None,
    start: Optional[int] = None,
    end: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Return a paginated list of activity rows (newest first).

    Returns: {items, page, page_size, total, total_pages}
    """
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > 500:
        page_size = 500

    where: List[str] = []
    params: List[Any] = []
    if relay_id is not None:
        where.append("relay_id = ?")
        params.append(int(relay_id))
    if start is not None:
        where.append("opened_at >= ?")
        params.append(int(start))
    if end is not None:
        where.append("opened_at < ?")
        params.append(int(end))

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    try:
        with _connect() as conn:
            total_row = conn.execute(
                f"SELECT COUNT(*) AS n FROM relay_activity{where_sql};",
                tuple(params),
            ).fetchone()
            total = int(total_row["n"]) if total_row else 0

            offset = (page - 1) * page_size
            rows = conn.execute(
                f"SELECT id, relay_id, opened_at, duration_s, mode "
                f"FROM relay_activity{where_sql} "
                f"ORDER BY opened_at DESC, id DESC "
                f"LIMIT ? OFFSET ?;",
                tuple(params) + (page_size, offset),
            ).fetchall()

        items = [_row_to_dict(r) for r in rows]
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        }

    except Exception as e:
        logger.error(f"list_history failed: {e}")
        return {
            "items": [],
            "page": page,
            "page_size": page_size,
            "total": 0,
            "total_pages": 0,
        }


def _period_bounds(period: str, year: int, month: Optional[int]) -> (int, int):
    """
    Compute [start_epoch, end_epoch) in the Pi's local timezone for the
    requested period. Raises ValueError on bad input.
    """
    if period not in ("month", "year"):
        raise ValueError(f"Invalid period {period!r}; expected 'month' or 'year'")
    if not isinstance(year, int) or year < 2000 or year > 2100:
        raise ValueError(f"Invalid year {year!r}")

    if period == "month":
        if not isinstance(month, int) or month < 1 or month > 12:
            raise ValueError(f"Invalid month {month!r}")
        start_dt = datetime(year, month, 1)
        if month == 12:
            end_dt = datetime(year + 1, 1, 1)
        else:
            end_dt = datetime(year, month + 1, 1)
    else:
        start_dt = datetime(year, 1, 1)
        end_dt = datetime(year + 1, 1, 1)

    return int(start_dt.timestamp()), int(end_dt.timestamp())


def get_stats(
    period: str,
    year: int,
    month: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Return aggregate statistics for a month or year.

    Period boundaries are resolved in the Pi's LOCAL timezone (so "April"
    means the whole local calendar month). Timestamps in the DB are unix
    seconds (UTC epoch).

    Returns:
        {
          "period": str, "year": int, "month": int|None,
          "start_at": int, "end_at": int,
          "total_duration_s": int, "total_count": int,
          "per_relay": [ {relay_id, total_duration_s, count}, ... 8 entries ]
        }
    """
    start_epoch, end_epoch = _period_bounds(period, year, month)

    per_relay: List[Dict[str, int]] = [
        {"relay_id": i, "total_duration_s": 0, "count": 0} for i in range(8)
    ]
    total_duration_s = 0
    total_count = 0

    try:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT relay_id, "
                "       COALESCE(SUM(duration_s), 0) AS total_duration_s, "
                "       COUNT(*) AS count "
                "FROM relay_activity "
                "WHERE opened_at >= ? AND opened_at < ? "
                "GROUP BY relay_id;",
                (start_epoch, end_epoch),
            ).fetchall()

        for row in rows:
            rid = int(row["relay_id"])
            if 0 <= rid <= 7:
                per_relay[rid]["total_duration_s"] = int(row["total_duration_s"])
                per_relay[rid]["count"] = int(row["count"])
                total_duration_s += int(row["total_duration_s"])
                total_count += int(row["count"])

    except Exception as e:
        logger.error(f"get_stats failed: {e}")

    return {
        "period": period,
        "year": year,
        "month": month if period == "month" else None,
        "start_at": start_epoch,
        "end_at": end_epoch,
        "total_duration_s": total_duration_s,
        "total_count": total_count,
        "per_relay": per_relay,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_history_db()
    print(f"History DB at: {_DB_PATH}")
    print("Last 5 entries:")
    for item in list_history(page=1, page_size=5)["items"]:
        print(f"  {item}")
