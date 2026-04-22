"""
Thin wrapper around the ``nmcli`` command.

Every call uses ``subprocess.run`` with a short timeout so a hang in
NetworkManager cannot block the watering loop. Output is returned as
``(returncode, stdout, stderr)`` tuples; higher layers decide what a
non-zero return code means (often "connection not found" is expected).
"""

from __future__ import annotations

import subprocess
from typing import List, Tuple


DEFAULT_TIMEOUT_S = 5


def run(args: List[str], timeout: int = DEFAULT_TIMEOUT_S) -> Tuple[int, str, str]:
    """Run ``nmcli <args>``, capturing stdout/stderr. Never raises on exit code."""
    try:
        proc = subprocess.run(
            ["nmcli", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except FileNotFoundError:
        return 127, "", "nmcli not found"
    except subprocess.TimeoutExpired:
        return 124, "", f"nmcli timeout after {timeout}s"
    except Exception as e:
        return 1, "", f"nmcli error: {e}"


def terse(args: List[str], timeout: int = DEFAULT_TIMEOUT_S) -> Tuple[int, str, str]:
    """Like :func:`run` but prepends ``-t`` (terse/escaped output)."""
    return run(["-t", *args], timeout=timeout)
