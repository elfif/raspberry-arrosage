"""
Redis helpers for the `network:*` keys.

The watchdog is the sole writer for ``network:mode``,
``network:lan_last_ok_at``, ``network:ap_active_since`` and
``network:ap_ssid``. The API may write ``network:force`` and
``network:wifi_changed`` as intents that the watchdog consumes.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from data.redis import get_redis_connection


KEY_MODE = "network:mode"
KEY_LAN_LAST_OK_AT = "network:lan_last_ok_at"
KEY_AP_ACTIVE_SINCE = "network:ap_active_since"
KEY_AP_SSID = "network:ap_ssid"
KEY_FORCE = "network:force"
KEY_WIFI_CHANGED = "network:wifi_changed"

MODE_ETHERNET = "ethernet"
MODE_WIFI_STA = "wifi_sta"
MODE_AP = "ap"
MODE_CHECKING = "checking"

VALID_MODES = (MODE_ETHERNET, MODE_WIFI_STA, MODE_AP, MODE_CHECKING)

FORCE_AP = "ap"
FORCE_AUTO = "auto"
VALID_FORCE_TARGETS = (FORCE_AP, FORCE_AUTO)


def _redis():
    return get_redis_connection()


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def get_mode() -> Optional[str]:
    """Return the current network mode string, or None if Redis is unreachable."""
    return _safe(lambda: _redis().get(KEY_MODE))


def set_mode(mode: str) -> bool:
    if mode not in VALID_MODES:
        return False
    return bool(_safe(lambda: _redis().set(KEY_MODE, mode), default=False))


def set_lan_last_ok_at(ts: Optional[int] = None) -> bool:
    ts = int(ts if ts is not None else time.time())
    return bool(_safe(lambda: _redis().set(KEY_LAN_LAST_OK_AT, ts), default=False))


def get_lan_last_ok_at() -> Optional[int]:
    raw = _safe(lambda: _redis().get(KEY_LAN_LAST_OK_AT))
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def set_ap_active(since: Optional[int], ssid: Optional[str]) -> bool:
    """
    Mark the AP as active (``since`` = unix seconds, ``ssid`` = SSID) or
    inactive (both None). Returns True on Redis success.
    """
    def _apply():
        r = _redis()
        if since is None:
            r.delete(KEY_AP_ACTIVE_SINCE)
            r.delete(KEY_AP_SSID)
        else:
            r.set(KEY_AP_ACTIVE_SINCE, int(since))
            if ssid:
                r.set(KEY_AP_SSID, ssid)
        return True

    return bool(_safe(_apply, default=False))


def get_ap_active_since() -> Optional[int]:
    raw = _safe(lambda: _redis().get(KEY_AP_ACTIVE_SINCE))
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def get_ap_ssid() -> Optional[str]:
    return _safe(lambda: _redis().get(KEY_AP_SSID))


def consume_force() -> Optional[str]:
    """Pop ``network:force`` atomically. Returns the target or None."""
    def _apply():
        r = _redis()
        val = r.get(KEY_FORCE)
        if val is not None:
            r.delete(KEY_FORCE)
        return val

    val = _safe(_apply)
    if val in VALID_FORCE_TARGETS:
        return val
    return None


def set_force(target: str) -> bool:
    if target not in VALID_FORCE_TARGETS:
        return False
    return bool(_safe(lambda: _redis().set(KEY_FORCE, target), default=False))


def consume_wifi_changed() -> Optional[int]:
    """Pop ``network:wifi_changed`` atomically. Returns the timestamp or None."""
    def _apply():
        r = _redis()
        val = r.get(KEY_WIFI_CHANGED)
        if val is not None:
            r.delete(KEY_WIFI_CHANGED)
        return val

    raw = _safe(_apply)
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def bump_wifi_changed() -> bool:
    return bool(
        _safe(lambda: _redis().set(KEY_WIFI_CHANGED, int(time.time())), default=False)
    )


def snapshot() -> Dict[str, Any]:
    """Return a dict with all network:* keys, for /network/status."""
    return {
        "mode": get_mode(),
        "lan_last_ok_at": get_lan_last_ok_at(),
        "ap_active_since": get_ap_active_since(),
        "ap_ssid": get_ap_ssid(),
    }
