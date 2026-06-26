"""
NetworkManager wrapper for the single Wi-Fi client profile
(``arrosage-sta``).

Only WPA2-PSK is accepted today; the API layer validates the payload and
this module is deliberately narrow to keep the attack surface small.

The PSK is never read back from NetworkManager: the API can report the
SSID and whether a profile is configured, but not the password.
"""

from __future__ import annotations

from typing import Optional

from . import nmcli, state
from .config import STA_PROFILE_NAME


SECURITY_WPA2_PSK = "wpa2-psk"
SUPPORTED_SECURITIES = (SECURITY_WPA2_PSK,)


class WifiProfileError(ValueError):
    """Raised when a profile payload is invalid or NM rejects the change."""


def _parse_terse(output: str) -> dict:
    result: dict = {}
    for line in output.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        result[key.strip()] = val.strip()
    return result


def profile_exists(name: str = STA_PROFILE_NAME) -> bool:
    rc, _, _ = nmcli.terse(["connection", "show", name])
    return rc == 0


def get(name: str = STA_PROFILE_NAME) -> Optional[dict]:
    """
    Return ``{configured, ssid, security}`` for the STA profile, or None
    if it does not exist. Never returns the PSK.
    """
    if not profile_exists(name):
        return None

    rc, out, _ = nmcli.terse(
        [
            "-f",
            "802-11-wireless.ssid,802-11-wireless-security.key-mgmt",
            "connection",
            "show",
            name,
        ]
    )
    if rc != 0:
        return None

    parsed = _parse_terse(out)
    ssid = parsed.get("802-11-wireless.ssid", "") or ""
    key_mgmt = parsed.get("802-11-wireless-security.key-mgmt", "") or ""

    security = SECURITY_WPA2_PSK if key_mgmt == "wpa-psk" else key_mgmt or "unknown"

    return {
        "configured": True,
        "ssid": ssid,
        "security": security,
    }


def _validate(ssid: str, security: str, psk: str) -> None:
    if not isinstance(ssid, str) or not ssid.strip():
        raise WifiProfileError("ssid must be a non-empty string")
    if len(ssid) > 32:
        raise WifiProfileError("ssid must be 32 bytes or fewer")
    if security not in SUPPORTED_SECURITIES:
        raise WifiProfileError(
            f"unsupported security '{security}'; supported: {SUPPORTED_SECURITIES}"
        )
    if not isinstance(psk, str):
        raise WifiProfileError("psk must be a string")
    if not (8 <= len(psk) <= 63):
        raise WifiProfileError("psk length must be between 8 and 63 characters")


def set(
    ssid: str,
    psk: str,
    security: str = SECURITY_WPA2_PSK,
    iface: str = "wlan0",
    name: str = STA_PROFILE_NAME,
) -> dict:
    """
    Create or update the STA profile.

    Raises :class:`WifiProfileError` on validation or nmcli failure.
    Returns the :func:`get` snapshot on success.
    """
    _validate(ssid, security, psk)

    if profile_exists(name):
        rc, _, err = nmcli.run(
            [
                "connection", "modify", name,
                "802-11-wireless.ssid", ssid,
                "802-11-wireless.mode", "infrastructure",
                "802-11-wireless-security.key-mgmt", "wpa-psk",
                "802-11-wireless-security.proto", "rsn",
                "802-11-wireless-security.pairwise", "ccmp",
                "802-11-wireless-security.group", "ccmp",
                "802-11-wireless-security.psk", psk,
                "connection.autoconnect", "yes",
                "ipv4.method", "auto",
                "ipv6.method", "auto",
            ],
            timeout=10,
        )
        if rc != 0:
            raise WifiProfileError(f"nmcli modify failed: {err.strip()}")
    else:
        rc, _, err = nmcli.run(
            [
                "connection", "add",
                "type", "wifi",
                "ifname", iface,
                "con-name", name,
                "autoconnect", "yes",
                "ssid", ssid,
                "mode", "infrastructure",
                "802-11-wireless-security.key-mgmt", "wpa-psk",
                "802-11-wireless-security.proto", "rsn",
                "802-11-wireless-security.pairwise", "ccmp",
                "802-11-wireless-security.group", "ccmp",
                "802-11-wireless-security.psk", psk,
                "ipv4.method", "auto",
                "ipv6.method", "auto",
            ],
            timeout=10,
        )
        if rc != 0:
            raise WifiProfileError(f"nmcli add failed: {err.strip()}")

    state.bump_wifi_changed()

    snapshot = get(name)
    if snapshot is None:
        raise WifiProfileError("profile disappeared right after write")
    return snapshot


def delete(name: str = STA_PROFILE_NAME) -> bool:
    """Remove the STA profile; returns True if it is gone (including already-absent)."""
    if not profile_exists(name):
        state.bump_wifi_changed()
        return True

    rc, _, err = nmcli.run(["connection", "delete", name], timeout=5)
    if rc != 0:
        msg = err.strip().lower()
        if "unknown" in msg or "not found" in msg:
            state.bump_wifi_changed()
            return True
        print(f"[network] failed to delete STA profile: {err.strip()}")
        return False

    state.bump_wifi_changed()
    return True


def down(name: str = STA_PROFILE_NAME) -> None:
    """Best-effort deactivation of the STA profile (used before AP up)."""
    nmcli.run(["connection", "down", name], timeout=5)
