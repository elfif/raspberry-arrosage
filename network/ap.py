"""
NetworkManager wrapper for the Wi-Fi AP profile (``arrosage-ap``).

The profile is persistent and idempotent: we reconcile its properties
with the loaded :class:`NetworkConfig` on every startup, so rotating the
AP PSK or SSID is a matter of editing the env file and restarting the
process.
"""

from __future__ import annotations

from typing import Optional

from . import nmcli
from .config import AP_PROFILE_NAME, STA_PROFILE_NAME, NetworkConfig


def profile_exists(name: str = AP_PROFILE_NAME) -> bool:
    rc, _, _ = nmcli.terse(["connection", "show", name])
    return rc == 0


def ensure_profile(cfg: NetworkConfig) -> bool:
    """
    Create or update the AP profile so it matches ``cfg``.

    Refuses to provision a profile without a PSK to avoid accidentally
    broadcasting an open AP. Returns True on success.
    """
    if not cfg.ap_psk or len(cfg.ap_psk) < 8:
        print(
            "[network] AP_PSK missing or too short (<8 chars); "
            "refusing to provision AP profile"
        )
        return False

    if not profile_exists(cfg.ap_profile_name):
        rc, _, err = nmcli.run(
            [
                "connection", "add",
                "type", "wifi",
                "ifname", cfg.ap_iface,
                "con-name", cfg.ap_profile_name,
                "autoconnect", "no",
                "ssid", cfg.ap_ssid,
                "mode", "ap",
                "802-11-wireless.band", "bg",
                "802-11-wireless.channel", str(cfg.ap_channel),
                "802-11-wireless-security.key-mgmt", "wpa-psk",
                "802-11-wireless-security.proto", "rsn",
                "802-11-wireless-security.pairwise", "ccmp",
                "802-11-wireless-security.group", "ccmp",
                "802-11-wireless-security.psk", cfg.ap_psk,
                "ipv4.method", "shared",
                "ipv6.method", "ignore",
            ],
            timeout=10,
        )
        if rc != 0:
            print(f"[network] failed to add AP profile: {err.strip()}")
            return False
        return True

    rc, _, err = nmcli.run(
        [
            "connection", "modify", cfg.ap_profile_name,
            "autoconnect", "no",
            "802-11-wireless.ssid", cfg.ap_ssid,
            "802-11-wireless.mode", "ap",
            "802-11-wireless.band", "bg",
            "802-11-wireless.channel", str(cfg.ap_channel),
            "802-11-wireless-security.key-mgmt", "wpa-psk",
            "802-11-wireless-security.proto", "rsn",
            "802-11-wireless-security.pairwise", "ccmp",
            "802-11-wireless-security.group", "ccmp",
            "802-11-wireless-security.psk", cfg.ap_psk,
            "ipv4.method", "shared",
            "ipv6.method", "ignore",
        ],
        timeout=10,
    )
    if rc != 0:
        print(f"[network] failed to update AP profile: {err.strip()}")
        return False
    return True


def is_active(name: str = AP_PROFILE_NAME) -> bool:
    rc, out, _ = nmcli.terse(["-f", "NAME", "connection", "show", "--active"])
    if rc != 0:
        return False
    return any(line.strip() == name for line in out.splitlines())


def up(cfg: Optional[NetworkConfig] = None) -> bool:
    """Activate the AP profile. Brings the STA profile down first, if active."""
    name = cfg.ap_profile_name if cfg else AP_PROFILE_NAME
    sta_name = cfg.sta_profile_name if cfg else STA_PROFILE_NAME

    nmcli.run(["connection", "down", sta_name], timeout=5)

    rc, _, err = nmcli.run(["connection", "up", name], timeout=15)
    if rc != 0:
        print(f"[network] failed to bring AP up: {err.strip()}")
        return False
    return True


def down(cfg: Optional[NetworkConfig] = None) -> bool:
    name = cfg.ap_profile_name if cfg else AP_PROFILE_NAME
    rc, _, err = nmcli.run(["connection", "down", name], timeout=10)
    if rc != 0:
        msg = err.strip().lower()
        if "not an active" in msg or "unknown" in msg or not msg:
            return True
        print(f"[network] failed to bring AP down: {err.strip()}")
        return False
    return True
