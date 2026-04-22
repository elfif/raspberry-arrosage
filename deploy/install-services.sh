#!/usr/bin/env bash
#
# Install the three arrosage systemd units into /etc/systemd/system/,
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
    "arrosage-web.service"
)

VENV_PY="/home/jnfrm/venv/bin/python"
NODE_BIN="/home/jnfrm/.nvm/versions/node/v22.20.0/bin/node"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

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
[[ -x "$NODE_BIN" ]] \
    || fail "missing or non-executable node: ${NODE_BIN} (update arrosage-web.service after nvm upgrades)"
[[ -f "${WEB_ROOT}/node_modules/vite/bin/vite.js" ]] \
    || fail "missing vite: run 'cd arrosage-web && npm ci'"
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
echo "    journalctl -u arrosage-web  -f"
