"""
LAN connectivity watchdog.

Runs as a daemon thread inside ``loop/main.py``. Every ``POLL_INTERVAL_S``
it pings ``PING_TARGET`` twice (``PING_PAUSE_S`` apart). On any ping
failure it disconnects Ethernet, brings the Wi-Fi AP up, and exits — AP
mode is sticky until reboot.

The watchdog is the only writer of the ``network:mode``,
``network:lan_last_ok_at``, ``network:ap_active_since`` and
``network:ap_ssid`` Redis keys. It consumes ``network:force`` as a
one-shot intent written by the API (``ap`` only; ``auto`` is rejected
at the HTTP layer).
"""

from __future__ import annotations

import time
from typing import Optional

from . import ap, connectivity, state
from .config import NetworkConfig


def _set_mode_lan() -> None:
    state.set_mode(state.MODE_LAN)
    state.set_lan_last_ok_at()


def _activate_ap(cfg: NetworkConfig) -> bool:
    ok = ap.up(cfg)
    if ok:
        state.set_mode(state.MODE_AP)
        state.set_ap_active(int(time.time()), cfg.ap_ssid)
    return ok


def run(cfg: NetworkConfig) -> None:
    """
    Thread entrypoint. Returns once the Pi is in AP mode (sticky until
    reboot). While in LAN mode, loops until connectivity fails or AP is
    forced via the API.
    """
    print(
        f"[network] watchdog starting: lan_iface={cfg.lan_iface} "
        f"ap_iface={cfg.ap_iface} ssid={cfg.ap_ssid!r} "
        f"poll={cfg.poll_interval_s}s ping={cfg.ping_target}"
    )

    ap.ensure_profile(cfg)
    state.set_mode(state.MODE_CHECKING)

    def _enter_ap(reason: str) -> None:
        print(f"[network] switching to AP mode ({reason})")
        if _activate_ap(cfg):
            print("[network] AP active; watchdog stopping (sticky until reboot)")
        else:
            print("[network] failed to bring AP up; watchdog stopping anyway")

    forced = state.consume_force()
    if forced == state.FORCE_AP:
        _enter_ap("forced via API")
        return
    if forced == state.FORCE_AUTO:
        print("[network] ignoring stale force=auto intent (AP mode is sticky)")

    if not connectivity.lan_reachable(
        target=cfg.ping_target,
        timeout_s=cfg.ping_timeout_s,
        pause_s=cfg.ping_pause_s,
    ):
        _enter_ap("initial ping check failed")
        return

    _set_mode_lan()
    print("[network] initial ping check passed; entering LAN monitoring loop")

    while True:
        try:
            time.sleep(cfg.poll_interval_s)

            forced = state.consume_force()
            if forced == state.FORCE_AP:
                _enter_ap("forced via API")
                return
            if forced == state.FORCE_AUTO:
                print("[network] ignoring force=auto intent (AP mode is sticky)")

            if connectivity.lan_reachable(
                target=cfg.ping_target,
                timeout_s=cfg.ping_timeout_s,
                pause_s=cfg.ping_pause_s,
            ):
                _set_mode_lan()
                continue

            _enter_ap("ping check failed")
            return

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
