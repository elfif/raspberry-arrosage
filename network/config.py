"""
Network configuration loader.

Reads the AP credentials and watchdog tuning from a root-readable env file
at /etc/arrosage/network.env (override path with ARROSAGE_NETWORK_ENV for
development). The file is a plain KEY=VALUE text file; values may be
single- or double-quoted.
"""

from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from typing import Optional


DEFAULT_ENV_PATH = "/etc/arrosage/network.env"

AP_PROFILE_NAME = "arrosage-ap"
STA_PROFILE_NAME = "arrosage-sta"


@dataclass
class NetworkConfig:
    """Runtime configuration for the network watchdog + AP profile."""

    ap_ssid: str = "arrosage-setup"
    ap_psk: str = ""
    ap_channel: int = 6
    ap_iface: str = "wlan0"
    lan_iface: str = "eth0"
    poll_interval_s: int = 10
    fail_threshold: int = 3
    success_threshold: int = 3
    boot_grace_s: int = 20
    sta_connect_grace_s: int = 30

    ap_profile_name: str = AP_PROFILE_NAME
    sta_profile_name: str = STA_PROFILE_NAME


def _parse_env_file(path: str) -> dict:
    """Parse a KEY=VALUE file; tolerant of comments, blanks, and quotes."""
    values: dict = {}
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            if not key:
                continue
            try:
                parts = shlex.split(val)
                val = parts[0] if parts else ""
            except ValueError:
                pass
            values[key] = val
    return values


def load_config(path: Optional[str] = None) -> NetworkConfig:
    """
    Load the network configuration.

    Precedence:
      1. ``path`` argument if provided.
      2. ``ARROSAGE_NETWORK_ENV`` environment variable.
      3. ``/etc/arrosage/network.env``.

    Missing file is not fatal: the watchdog falls back to defaults, but
    without ``AP_PSK`` the AP profile cannot be provisioned safely, so
    ``ap.ensure_profile`` will refuse to run until it is set.
    """
    env_path = path or os.environ.get("ARROSAGE_NETWORK_ENV") or DEFAULT_ENV_PATH

    raw: dict = {}
    if os.path.isfile(env_path):
        try:
            raw = _parse_env_file(env_path)
        except Exception as e:
            print(f"[network] failed to read {env_path}: {e}")

    def _s(key: str, default: str) -> str:
        val = raw.get(key, os.environ.get(key, ""))
        return val if val else default

    def _i(key: str, default: int) -> int:
        val = raw.get(key, os.environ.get(key, ""))
        try:
            return int(val) if val else default
        except ValueError:
            return default

    return NetworkConfig(
        ap_ssid=_s("AP_SSID", "arrosage-setup"),
        ap_psk=_s("AP_PSK", ""),
        ap_channel=_i("AP_CHANNEL", 6),
        ap_iface=_s("AP_IFACE", "wlan0"),
        lan_iface=_s("LAN_IFACE", "eth0"),
        poll_interval_s=_i("POLL_INTERVAL_S", 10),
        fail_threshold=_i("FAIL_THRESHOLD", 3),
        success_threshold=_i("SUCCESS_THRESHOLD", 3),
        boot_grace_s=_i("BOOT_GRACE_S", 20),
        sta_connect_grace_s=_i("STA_CONNECT_GRACE_S", 30),
    )
