#!/usr/bin/env bash
#
# Dev launcher: runs loop + api in the same terminal using the project
# venv. For production, use the systemd units under deploy/systemd/
# (install via deploy/install-services.sh).
set -e

cd "$(dirname "$0")"

PYTHON="/home/jnfrm/venv/bin/python"

"$PYTHON" loop/main.py &
LOOP_PID=$!
trap "kill $LOOP_PID 2>/dev/null || true" EXIT

"$PYTHON" api.py
