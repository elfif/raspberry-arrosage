"""
LAN connectivity checks.

The watchdog uses :func:`lan_reachable` (ICMP ping to a public target).
The HTTP API still exposes per-interface state via NetworkManager for
informational ``/network/status`` responses.
"""

from __future__ import annotations

import subprocess
import time
from typing import Dict, Optional, Tuple

from . import nmcli
from .config import AP_PROFILE_NAME


LINK_LOCAL_PREFIX = "169.254."


def _parse_terse(output: str) -> Dict[str, str]:
    """
    Parse ``nmcli -t -f KEY1,KEY2,... device show <iface>`` output.

    Each line looks like ``KEY[index]:value``; we only keep the last
    occurrence per key, which is fine for the fields we read.
    """
    result: Dict[str, str] = {}
    for line in output.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        result[key.strip()] = val.strip()
    return result


def _iface_active_connection(iface: str) -> Optional[str]:
    """Return the name of the active NM connection on ``iface``, or None."""
    rc, out, _ = nmcli.terse(
        ["-f", "GENERAL.CONNECTION", "device", "show", iface]
    )
    if rc != 0:
        return None
    parsed = _parse_terse(out)
    conn = parsed.get("GENERAL.CONNECTION")
    if not conn or conn == "--":
        return None
    return conn


def iface_up(iface: str) -> Tuple[bool, Optional[str]]:
    """
    Return ``(is_up, ipv4)`` for ``iface``.

    Only a non-link-local IPv4 obtained via the active connection counts
    as "up". Returns ``(False, None)`` on any nmcli failure.
    """
    rc, out, _ = nmcli.terse(
        ["-f", "GENERAL.STATE,IP4.ADDRESS", "device", "show", iface]
    )
    if rc != 0:
        return False, None

    parsed = _parse_terse(out)
    state = parsed.get("GENERAL.STATE", "")
    if not state.startswith("100"):
        return False, None

    raw_addr = parsed.get("IP4.ADDRESS[1]") or parsed.get("IP4.ADDRESS")
    if not raw_addr:
        return False, None

    ip = raw_addr.split("/", 1)[0].strip()
    if not ip or ip.startswith(LINK_LOCAL_PREFIX):
        return False, None

    return True, ip


def lan_status(lan_iface: str = "eth0", wlan_iface: str = "wlan0") -> Dict[str, Dict]:
    """
    Return a dict describing both LAN-capable interfaces.

    wlan0 only counts when its active connection is NOT the AP profile,
    i.e. when it is acting as a Wi-Fi client.
    """
    eth_up, eth_ip = iface_up(lan_iface)

    wifi_up, wifi_ip = False, None
    wifi_active_conn = _iface_active_connection(wlan_iface)
    if wifi_active_conn and wifi_active_conn != AP_PROFILE_NAME:
        wifi_up, wifi_ip = iface_up(wlan_iface)

    return {
        "ethernet": {"up": eth_up, "ip": eth_ip},
        "wifi_sta": {"up": wifi_up, "ip": wifi_ip},
    }


def any_up(status: Dict[str, Dict]) -> bool:
    return bool(status.get("ethernet", {}).get("up") or status.get("wifi_sta", {}).get("up"))


def primary_medium(status: Dict[str, Dict]) -> Optional[str]:
    """Return ``'ethernet'`` when eth0 is up, else ``'wifi_sta'`` when wlan0 is up, else None."""
    if status.get("ethernet", {}).get("up"):
        return "ethernet"
    if status.get("wifi_sta", {}).get("up"):
        return "wifi_sta"
    return None


def lan_reachable(
    target: str = "8.8.8.8",
    timeout_s: int = 3,
    pause_s: int = 5,
) -> bool:
    """
    Return True when two ICMP pings to ``target`` succeed.

    Sends ping #1, waits ``pause_s`` seconds, then ping #2. Any failure
    returns False (strict semantics). Uses the OS default route, so any
    working uplink (Ethernet or Wi-Fi STA) satisfies the check.
    """
    for i in range(2):
        if i > 0:
            time.sleep(pause_s)
        try:
            proc = subprocess.run(
                ["ping", "-c", "1", "-W", str(timeout_s), target],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if proc.returncode != 0:
                return False
        except (FileNotFoundError, OSError):
            return False
    return True
