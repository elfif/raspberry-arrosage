#!/usr/bin/env bash
#
# Install the arrosage systemd units into /etc/systemd/system/,
# reload systemd, and enable them to start on boot.
#
# Run with sudo:
#     sudo ./deploy/install-services.sh
#     sudo bash deploy/install-services.sh
#     sudo sh deploy/install-services.sh   # auto re-execs under bash
#
# This script is idempotent: re-running it overwrites the installed unit
# files with the ones from the repo, reloads systemd, and re-enables the
# services.
#
# The web UI is served by Caddy (see deploy/install-caddy.sh), not a
# separate Node preview service.

# Some invocations (e.g. `sudo sh install-services.sh`) ignore the shebang
# and run us under dash, which does not support `set -o pipefail` or
# `[[ ... ]]`. Re-exec under bash when that happens.
if [ -z "${BASH_VERSION:-}" ]; then
    exec /usr/bin/env bash "$0" "$@"
fi

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root (use sudo)." >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIT_SRC_DIR="${SCRIPT_DIR}/systemd"
UNIT_DST_DIR="/etc/systemd/system"

PYTHON_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${PYTHON_ROOT}/.." && pwd)"
WEB_ROOT="${REPO_ROOT}/arrosage-web"

UNITS=(
    "arrosage-loop.service"
    "arrosage-api.service"
)

VENV_PY="/home/jnfrm/venv/bin/python"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

# --- Retire legacy vite preview unit (replaced by Caddy) ----------------

LEGACY_WEB_UNIT="arrosage-web.service"
if systemctl cat "${LEGACY_WEB_UNIT}" &>/dev/null \
    || [[ -f "${UNIT_DST_DIR}/${LEGACY_WEB_UNIT}" ]]; then
    echo "==> Disabling legacy ${LEGACY_WEB_UNIT} (replaced by Caddy)..."
    systemctl disable --now "${LEGACY_WEB_UNIT}" 2>/dev/null || true
fi
rm -f "${UNIT_DST_DIR}/${LEGACY_WEB_UNIT}"

# --- Prerequisite checks ------------------------------------------------

echo "==> Checking prerequisites..."

for unit in "${UNITS[@]}"; do
    [[ -f "${UNIT_SRC_DIR}/${unit}" ]] \
        || fail "missing unit source: ${UNIT_SRC_DIR}/${unit}"
done

[[ -f "${PYTHON_ROOT}/loop/main.py" ]] \
    || fail "missing ${PYTHON_ROOT}/loop/main.py"
[[ -f "${PYTHON_ROOT}/api.py" ]] \
    || fail "missing ${PYTHON_ROOT}/api.py"
[[ -d "${WEB_ROOT}/dist" ]] \
    || fail "missing ${WEB_ROOT}/dist (run 'cd arrosage-web && npm ci && npm run build' first)"
[[ -x "$VENV_PY" ]] \
    || fail "missing or non-executable venv python: ${VENV_PY}"
[[ -f "/etc/arrosage/network.env" ]] \
    || fail "missing /etc/arrosage/network.env (run 'sudo ./init-network-env.sh' first)"

if ! systemctl is-enabled --quiet redis-server.service; then
    echo "WARNING: redis-server.service is not enabled at boot"
    echo "         Run: sudo systemctl enable --now redis-server.service"
fi
if ! systemctl is-enabled --quiet NetworkManager.service; then
    echo "WARNING: NetworkManager.service is not enabled at boot"
    echo "         Run: sudo systemctl enable --now NetworkManager.service"
fi

# --- Avahi (mDNS: http://arrosage.local) --------------------------------

AVAHI_CONF_SRC="${SCRIPT_DIR}/avahi/avahi-daemon.conf"
AVAHI_CONF_DST="/etc/avahi/avahi-daemon.conf"

echo "==> Ensuring avahi-daemon (mDNS arrosage.local)..."
export DEBIAN_FRONTEND=noninteractive
if ! command -v avahi-daemon >/dev/null 2>&1; then
    apt-get update -qq
    apt-get install -y -qq avahi-daemon \
        || fail "apt-get install avahi-daemon failed"
else
    echo "    avahi-daemon already present"
fi

[[ -f "${AVAHI_CONF_SRC}" ]] || fail "missing ${AVAHI_CONF_SRC}"
install -d -m 0755 -o root -g root /etc/avahi
if [[ -f "${AVAHI_CONF_DST}" ]]; then
    if grep -qE '^[[:space:]]*host-name=' "${AVAHI_CONF_DST}"; then
        sed -i 's/^[[:space:]]*host-name=.*/host-name=arrosage/' "${AVAHI_CONF_DST}"
    else
        sed -i '/^\[server\]/a host-name=arrosage' "${AVAHI_CONF_DST}"
    fi
    echo "    updated host-name=arrosage in ${AVAHI_CONF_DST}"
else
    install -m 0644 -o root -g root "${AVAHI_CONF_SRC}" "${AVAHI_CONF_DST}"
    echo "    installed ${AVAHI_CONF_DST}"
fi

systemctl enable avahi-daemon.service
systemctl restart avahi-daemon.service

# --- Install ------------------------------------------------------------

echo "==> Installing units to ${UNIT_DST_DIR}..."
for unit in "${UNITS[@]}"; do
    install -m 0644 -o root -g root \
        "${UNIT_SRC_DIR}/${unit}" "${UNIT_DST_DIR}/${unit}"
    echo "    ${unit}"
done

echo "==> Reloading systemd..."
systemctl daemon-reload

echo "==> Enabling and starting units..."
systemctl enable --now "${UNITS[@]}"

# --- Report -------------------------------------------------------------

echo
echo "==> Status:"
for unit in "${UNITS[@]}"; do
    echo "--- ${unit} ---"
    systemctl status --no-pager --lines=3 "$unit" || true
    echo
done

echo "Done. Useful follow-ups:"
echo "    journalctl -u arrosage-loop -f"
echo "    journalctl -u arrosage-api  -f"
echo "    journalctl -u caddy         -f"
echo "    journalctl -u avahi-daemon  -f"
