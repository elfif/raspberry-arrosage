#!/usr/bin/env bash
#
# Install Caddy from the official APT repo, deploy the Arrosage Caddyfile,
# install a systemd drop-in so Caddy runs as jnfrm, validate, and enable the service.
#
# Run with sudo:
#     sudo ./deploy/install-caddy.sh
#
# Prerequisite: built frontend at ../arrosage-web/dist (same as install-services.sh).
# Idempotent: safe to re-run; overwrites /etc/caddy/Caddyfile and the drop-in.

if [ -z "${BASH_VERSION:-}" ]; then
    exec /usr/bin/env bash "$0" "$@"
fi

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root (use sudo)." >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${PYTHON_ROOT}/.." && pwd)"
WEB_ROOT="${REPO_ROOT}/arrosage-web"

CADDYFILE_SRC="${SCRIPT_DIR}/caddy/Caddyfile"
OVERRIDE_SRC="${SCRIPT_DIR}/systemd/caddy.service.d/override.conf"
CADDY_DST="/etc/caddy/Caddyfile"
OVERRIDE_DST_DIR="/etc/systemd/system/caddy.service.d"
OVERRIDE_DST="${OVERRIDE_DST_DIR}/override.conf"
ARROSAGE_USER="jnfrm"
ARROSAGE_GROUP="jnfrm"
ARROSAGE_ETC="/etc/arrosage"
AUTH_ENV="${ARROSAGE_ETC}/caddy-basic-auth.env"
AUTH_EXAMPLE_SRC="${SCRIPT_DIR}/caddy/caddy-basic-auth.env.example"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

# Require a bcrypt hash on disk so `caddy validate` matches what systemd will load.
require_basic_auth_env() {
    [[ -f "${AUTH_ENV}" ]] \
        || fail "missing ${AUTH_ENV} — copy and fill ${AUTH_EXAMPLE_SRC}, then install on the Pi (see README)."

    local hash_line value
    hash_line="$(grep -E '^[[:space:]]*ARROSAGE_BASIC_AUTH_HASH=' "${AUTH_ENV}" \
        | grep -v '^[[:space:]]*#' | tail -n 1 || true)"
    [[ -n "${hash_line}" ]] \
        || fail "no ARROSAGE_BASIC_AUTH_HASH= line in ${AUTH_ENV} (see ${AUTH_EXAMPLE_SRC})."

    value="${hash_line#*=}"
    value="${value//$'\r'/}"
    value="${value%\"}"
    value="${value#\"}"

    [[ "${value}" =~ ^\$2[aby]\$ ]] \
        || fail "ARROSAGE_BASIC_AUTH_HASH must be bcrypt output from: caddy hash-password"
    [[ "${#value}" -ge 50 ]] \
        || fail "ARROSAGE_BASIC_AUTH_HASH looks too short (incomplete copy?)."

    if ! sudo -u "${ARROSAGE_USER}" test -r "${AUTH_ENV}"; then
        fail "${AUTH_ENV} is not readable by ${ARROSAGE_USER}. Try: chown root:${ARROSAGE_GROUP} ${AUTH_ENV} && chmod 640 ${AUTH_ENV}"
    fi

    # Export for `caddy validate` below. Do NOT `source` this file: bcrypt hashes
    # start with $2a$… and bash would treat $2 as the second positional parameter.
    export ARROSAGE_BASIC_AUTH_HASH="${value}"
}

echo "==> Checking prerequisites..."
[[ -f "${CADDYFILE_SRC}" ]] || fail "missing ${CADDYFILE_SRC}"
[[ -f "${OVERRIDE_SRC}" ]] || fail "missing ${OVERRIDE_SRC}"
[[ -d "${WEB_ROOT}/dist" ]] \
    || fail "missing ${WEB_ROOT}/dist (run 'cd arrosage-web && npm ci && npm run build' first)"

echo "==> Ensuring Caddy is installed..."
if ! command -v caddy >/dev/null 2>&1; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https curl \
        || fail "apt-get install prerequisites failed"
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
        | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg \
        || fail "failed to install Caddy apt signing key"
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
        | tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null \
        || fail "failed to add Caddy apt source"
    apt-get update -qq
    apt-get install -y -qq caddy || fail "apt-get install caddy failed"
else
    echo "    caddy already present: $(command -v caddy)"
fi

echo "==> Installing Caddyfile to ${CADDY_DST}..."
install -d -m 0755 -o root -g root /etc/caddy
install -m 0644 -o root -g root "${CADDYFILE_SRC}" "${CADDY_DST}"

echo "==> Installing systemd drop-in..."
install -d -m 0755 -o root -g root "${OVERRIDE_DST_DIR}"
install -m 0644 -o root -g root "${OVERRIDE_SRC}" "${OVERRIDE_DST}"

echo "==> Ensuring ${ARROSAGE_ETC} and Basic Auth env..."
install -d -m 0755 -o root -g root "${ARROSAGE_ETC}"
[[ -f "${AUTH_EXAMPLE_SRC}" ]] \
    && install -m 0644 -o root -g root "${AUTH_EXAMPLE_SRC}" "${ARROSAGE_ETC}/caddy-basic-auth.env.example"

require_basic_auth_env

echo "==> Validating Caddyfile..."
caddy validate --config "${CADDY_DST}" \
    || fail "caddy validate failed"

echo "==> Reloading systemd and restarting Caddy..."
systemctl daemon-reload
systemctl enable caddy.service
systemctl restart caddy.service

echo
echo "==> Status:"
systemctl status --no-pager --lines=8 caddy.service || true

echo
echo "Done. Smoke tests (replace PASS with your Basic Auth password):"
echo "    curl -sfI -u arrosage:PASS http://127.0.0.1/"
echo "    curl -sfI -u arrosage:PASS http://127.0.0.1/api/"
echo "From LAN:"
echo "    curl -sfI -u arrosage:PASS http://arrosage-pi.local/"
echo "    curl -sfI -u arrosage:PASS http://arrosage-pi.local/api/"
echo "    (without -u you should see HTTP/1.1 401 Unauthorized)"
