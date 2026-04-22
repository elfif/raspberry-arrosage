#!/usr/bin/env python3
"""
Remove a relay from the currently running sequence.

See plan: transient skipped_relays on Redis status; immediate advance when
removing the active relay; PAUSE-safe status rewrite for resume().
"""

import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.mode import get_mode, MODE_PAUSE
from data.status import (
    get_status,
    clear_status,
    add_skipped_relay,
)
from data.redis import get_json_from_redis, set_json_to_redis
from data.history import log_current_relay_close
from hardware.relay.relays import close_all_relays
from loop.sequence import start_step


def _next_non_skipped(opened: int, skipped: set[int], removed: int) -> int:
    """First relay index > opened that is not in skipped ∪ {removed}, or 8 if none."""
    skip = skipped | {removed}
    n = opened + 1
    while n <= 7 and n in skip:
        n += 1
    return n


def remove_relay(relay_id: int) -> tuple[bool, str]:
    """
    Remove relay_id from the current sequence run.

    Returns:
        (success, reason_code) where reason_code is one of:
        ok, invalid_relay_id, no_active_sequence, already_past, already_skipped,
        sequence_ended
    """
    if not isinstance(relay_id, int) or relay_id < 0 or relay_id > 7:
        return False, "invalid_relay_id"

    status = get_status()
    if status is None:
        return False, "no_active_sequence"

    opened = status.get("opened_relay")
    if not isinstance(opened, int) or opened < 0 or opened > 7:
        return False, "no_active_sequence"

    raw_skipped = status.get("skipped_relays", []) or []
    skipped: set[int] = {
        x for x in raw_skipped
        if isinstance(x, int) and 0 <= x <= 7
    }

    if relay_id < opened:
        return True, "already_past"

    if relay_id in skipped:
        return True, "already_skipped"

    # Future step: only record skip; main loop / remove-active handles hardware.
    if relay_id > opened:
        if add_skipped_relay(relay_id):
            return True, "ok"
        return False, "no_active_sequence"

    # relay_id == opened (active step)
    mode = get_mode()
    next_relay = _next_non_skipped(opened, skipped, relay_id)

    if mode == MODE_PAUSE:
        mode_data = get_json_from_redis("mode")
        paused_at = None
        if isinstance(mode_data, dict):
            pa = mode_data.get("paused_at")
            if isinstance(pa, (int, float)):
                paused_at = int(pa)

        if paused_at is None:
            oa = status.get("opened_at")
            if isinstance(oa, (int, float)) and oa > 0:
                paused_at = int(oa)
            else:
                paused_at = int(time.time())

        new_skipped = sorted(skipped | {relay_id})

        if next_relay > 7:
            clear_status()
            return True, "sequence_ended"

        settings = get_json_from_redis("settings")
        if settings is None or "sequence" not in settings:
            return False, "no_active_sequence"

        sequence = settings["sequence"]
        if not isinstance(sequence, list) or next_relay >= len(sequence):
            return False, "no_active_sequence"

        duration = sequence[next_relay]
        if not isinstance(duration, int) or duration < 0:
            return False, "no_active_sequence"

        new_status: dict = {
            "opened_relay": next_relay,
            "opened_at": paused_at,
            "skipped_relays": new_skipped,
        }
        if duration > 0:
            new_status["should_close_at"] = paused_at + duration

        if not set_json_to_redis("status", new_status):
            return False, "no_active_sequence"

        return True, "ok"

    # Non-PAUSE: start_step logs current relay, closes all, opens next (once).
    if next_relay <= 7:
        if not add_skipped_relay(relay_id):
            return False, "no_active_sequence"
        if start_step(next_relay):
            return True, "ok"
        return False, "no_active_sequence"

    log_current_relay_close()
    try:
        close_all_relays()
    except Exception:
        pass
    clear_status()
    return True, "sequence_ended"
