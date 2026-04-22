"""
LAN connectivity watchdog.

Runs as a daemon thread inside ``loop/main.py``. Evaluates LAN
connectivity (eth0 OR wlan0 as STA) every ``POLL_INTERVAL_S`` and, with
hysteresis, brings a Wi-Fi AP fallback up or down on wlan0.

The watchdog is the only writer of the ``network:mode``,
``network:lan_last_ok_at``, ``network:ap_active_since`` and
``network:ap_ssid`` Redis keys. It consumes ``network:force`` and
``network:wifi_changed`` as one-shot intents written by the API.
"""

from __future__ import annotations

import time
from typing import Optional

from . import ap, connectivity, state
from .config import NetworkConfig


def _set_mode_lan(status: dict) -> None:
    medium = connectivity.primary_medium(status) or state.MODE_ETHERNET
    state.set_mode(medium)
    state.set_lan_last_ok_at()


def _activate_ap(cfg: NetworkConfig) -> bool:
    ok = ap.up(cfg)
    if ok:
        state.set_mode(state.MODE_AP)
        state.set_ap_active(int(time.time()), cfg.ap_ssid)
    return ok


def _deactivate_ap(cfg: NetworkConfig) -> None:
    ap.down(cfg)
    state.set_ap_active(None, None)


def run(cfg: NetworkConfig) -> None:
    """
    Thread entrypoint. Never returns (runs until the process dies).

    All external I/O (nmcli, Redis) is wrapped so the loop cannot raise
    out of this function; any unexpected exception is logged and swallowed.
    """
    print(
        f"[network] watchdog starting: lan_iface={cfg.lan_iface} "
        f"ap_iface={cfg.ap_iface} ssid={cfg.ap_ssid!r} "
        f"poll={cfg.poll_interval_s}s grace={cfg.boot_grace_s}s"
    )

    ap.ensure_profile(cfg)

    state.set_mode(state.MODE_CHECKING)

    started_at = time.time()
    fail_count = 0
    success_count = 0
    current: str = state.MODE_CHECKING
    sta_grace_until: float = 0.0

    while True:
        try:
            time.sleep(cfg.poll_interval_s)

            now = time.time()
            in_boot_grace = (now - started_at) < cfg.boot_grace_s
            in_sta_grace = now < sta_grace_until

            forced = state.consume_force()
            if forced == state.FORCE_AP and current != state.MODE_AP:
                if _activate_ap(cfg):
                    current = state.MODE_AP
                    fail_count = 0
                    success_count = 0
                continue
            if forced == state.FORCE_AUTO and current == state.MODE_AP:
                status = connectivity.lan_status(cfg.lan_iface, cfg.ap_iface)
                if connectivity.any_up(status):
                    _deactivate_ap(cfg)
                    _set_mode_lan(status)
                    current = connectivity.primary_medium(status) or state.MODE_ETHERNET
                    fail_count = 0
                    success_count = 0
                continue

            wifi_changed = state.consume_wifi_changed()
            if wifi_changed is not None:
                if current == state.MODE_AP:
                    _deactivate_ap(cfg)
                    current = state.MODE_CHECKING
                    state.set_mode(state.MODE_CHECKING)
                sta_grace_until = now + cfg.sta_connect_grace_s
                fail_count = 0
                success_count = 0
                continue

            status = connectivity.lan_status(cfg.lan_iface, cfg.ap_iface)
            is_up = connectivity.any_up(status)

            if is_up:
                fail_count = 0
                success_count += 1
                if current != state.MODE_AP:
                    _set_mode_lan(status)
                    current = connectivity.primary_medium(status) or current
                elif success_count >= cfg.success_threshold:
                    _deactivate_ap(cfg)
                    _set_mode_lan(status)
                    current = connectivity.primary_medium(status) or state.MODE_ETHERNET
                    success_count = 0
            else:
                success_count = 0
                if in_sta_grace:
                    continue
                fail_count += 1
                if current != state.MODE_AP and fail_count >= cfg.fail_threshold:
                    if in_boot_grace:
                        continue
                    if _activate_ap(cfg):
                        current = state.MODE_AP
                        fail_count = 0

        except Exception as e:
            print(f"[network] watchdog iteration error: {e}")


def make_force_target(value: Optional[str]) -> Optional[str]:
    """Helper for the API layer: normalize a user-provided target string."""
    if not isinstance(value, str):
        return None
    value = value.strip().lower()
    if value in state.VALID_FORCE_TARGETS:
        return value
    return None
