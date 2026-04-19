#!/usr/bin/env python3
"""
Manual Relay Control Commands for Arrosage System

This module provides manual relay open/close helpers used by the API.
They only operate when the current mode is MANUAL.
"""

import sys
import os
import logging
import traceback
from typing import List, Dict, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.mode import get_mode, MODE_MANUAL
from data.status import set_open_relay, clear_status
from hardware.relay.relays import close_all_relays, open_relay

logger = logging.getLogger("arrosage_relay")

NUM_RELAYS = 8


def open_relay_manual(relay_id: int) -> bool:
    """
    Open a single relay in MANUAL mode.

    Args:
        relay_id (int): Relay number between 0 and 7.

    Returns:
        bool: True if the relay was opened successfully, False otherwise.
    """
    try:
        if not isinstance(relay_id, int) or relay_id < 0 or relay_id >= NUM_RELAYS:
            logger.warning(f"Invalid relay_id: {relay_id} (expected 0..{NUM_RELAYS - 1})")
            return False

        current_mode = get_mode()
        logger.info(f"open_relay_manual({relay_id}) called. Current mode: {current_mode}")

        if current_mode != MODE_MANUAL:
            logger.warning(
                f"Cannot open relay. System is not in MANUAL mode (current: {current_mode})"
            )
            return False

        close_all_relays()
        open_relay(relay_id)

        if not set_open_relay(relay_id):
            logger.error("Failed to persist opened relay in Redis status")
            return False

        logger.info(f"Relay {relay_id} opened successfully")
        return True

    except Exception as e:
        logger.error(f"Unexpected error in open_relay_manual: {e}")
        logger.error(traceback.format_exc())
        return False


def close_relays_manual() -> bool:
    """
    Close all relays in MANUAL mode and clear the Redis status entry.

    Returns:
        bool: True if relays were closed successfully, False otherwise.
    """
    try:
        current_mode = get_mode()
        logger.info(f"close_relays_manual() called. Current mode: {current_mode}")

        if current_mode != MODE_MANUAL:
            logger.warning(
                f"Cannot close relays. System is not in MANUAL mode (current: {current_mode})"
            )
            return False

        close_all_relays()

        if not clear_status():
            logger.error("Failed to clear Redis status after closing relays")
            return False

        logger.info("All relays closed successfully")
        return True

    except Exception as e:
        logger.error(f"Unexpected error in close_relays_manual: {e}")
        logger.error(traceback.format_exc())
        return False


def build_relay_status(opened_relay: Optional[int]) -> List[Dict[str, object]]:
    """
    Build the per-relay status list using 0-based relay IDs.

    Args:
        opened_relay (Optional[int]): Index (0..7) of the opened relay, or None
            if all relays are closed.

    Returns:
        List[Dict[str, object]]: 8-item list of {"relay_id": 0..7, "is_open": bool}.
    """
    return [
        {
            "relay_id": i,
            "is_open": opened_relay is not None and i == opened_relay,
        }
        for i in range(0, NUM_RELAYS)
    ]
