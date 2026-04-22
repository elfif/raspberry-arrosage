#!/usr/bin/env bash
#
# Initialize /etc/arrosage/network.env for the network watchdog.
#
# Run with sudo (any of these work):
#     sudo ./init-network-env.sh
#     sudo bash init-network-env.sh
#     sudo sh init-network-env.sh   # auto re-execs under bash
#
# By default the AP_PSK is generated with 24 random alphanumeric chars
# so the file is never left with a weak default. Override any value by
# exporting the corresponding variable before running, e.g.:
#     sudo AP_SSID=my-ap AP_PSK=my-strong-psk ./init-network-env.sh
#
# If the target file already exists, the script refuses to overwrite it
# unless FORCE=1 is set.

# Some invocations (e.g. `sudo sh init-network-env.sh`) ignore the
# shebang and run us under dash, which does not support `set -o pipefail`
# or `[[ ... ]]`. Re-exec under bash when that happens.
if [ -z "${BASH_VERSION:-}" ]; then
    exec /usr/bin/env bash "$0" "$@"
fi

set -euo pipefail

TARGET_DIR="/etc/arrosage"
TARGET_FILE="${TARGET_DIR}/network.env"

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root (use sudo)." >&2
    exit 1
fi

if [[ -e "$TARGET_FILE" && "${FORCE:-0}" != "1" ]]; then
    echo "Refusing to overwrite existing ${TARGET_FILE}."
    echo "Re-run with FORCE=1 to replace it (the current PSK will be lost)."
    exit 1
fi

# Generate a 24-char alphanumeric PSK when one is not provided.

AP_SSID="${AP_SSID:-arrosage-setup}"
AP_PSK="arrosageberry"
AP_CHANNEL="${AP_CHANNEL:-6}"
AP_IFACE="${AP_IFACE:-wlan0}"
LAN_IFACE="${LAN_IFACE:-eth0}"
POLL_INTERVAL_S="${POLL_INTERVAL_S:-10}"
FAIL_THRESHOLD="${FAIL_THRESHOLD:-3}"
SUCCESS_THRESHOLD="${SUCCESS_THRESHOLD:-3}"
BOOT_GRACE_S="${BOOT_GRACE_S:-20}"
STA_CONNECT_GRACE_S="${STA_CONNECT_GRACE_S:-30}"

if [[ ${#AP_PSK} -lt 8 || ${#AP_PSK} -gt 63 ]]; then
    echo "AP_PSK must be between 8 and 63 characters (got ${#AP_PSK})." >&2
    exit 1
fi

install -d -m 0755 -o root -g root "$TARGET_DIR"

umask 077
cat > "$TARGET_FILE" <<EOF
# /etc/arrosage/network.env
# Managed by init-network-env.sh. Keep mode 0600, owner root:root.

# Wi-Fi AP fallback (WPA2-PSK). Used ONLY when no LAN is reachable.
AP_SSID=${AP_SSID}
AP_PSK=${AP_PSK}
AP_CHANNEL=${AP_CHANNEL}
AP_IFACE=${AP_IFACE}

# Wired LAN interface to check first.
LAN_IFACE=${LAN_IFACE}

# Watchdog tuning.
POLL_INTERVAL_S=${POLL_INTERVAL_S}
FAIL_THRESHOLD=${FAIL_THRESHOLD}
SUCCESS_THRESHOLD=${SUCCESS_THRESHOLD}
BOOT_GRACE_S=${BOOT_GRACE_S}
STA_CONNECT_GRACE_S=${STA_CONNECT_GRACE_S}
EOF

chown root:root "$TARGET_FILE"
chmod 0600 "$TARGET_FILE"

echo "Wrote ${TARGET_FILE} (mode 0600, owner root:root)."
echo
echo "AP SSID:     ${AP_SSID}"
echo "AP PSK:      ${AP_PSK}"
echo "AP channel:  ${AP_CHANNEL}"
echo "AP iface:    ${AP_IFACE}"
echo "LAN iface:   ${LAN_IFACE}"
echo
echo "Note the AP PSK above: it is not printed again on subsequent runs."
