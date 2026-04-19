#!/usr/bin/env python3
"""
Start Mechanism for Arrosage System

This module provides start functionality for the watering system.
It starts sequence only if we are in SEMI_AUTO mode.
"""

import sys
import os
import logging
import traceback

# Add parent directory to path to import data modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.mode import get_mode, MODE_SEMI_AUTO

logger = logging.getLogger("arrosage_start")

def start() -> bool:
    """
    Start the system by starting the sequence.
    Only works if the current mode is SEMI_AUTO.
    
    Returns:
        bool: True if sequence started successfully, False otherwise
    """
    try:
        current_mode = get_mode()
        logger.info(f"Start command called. Current mode: {current_mode}")
        
        if current_mode != MODE_SEMI_AUTO:
            logger.warning(f"Cannot start sequence. System is not in SEMI_AUTO mode (current: {current_mode})")
            return False
        
        # Import here to avoid circular dependencies
        from loop.sequence import start_sequence
        
        logger.info("Starting sequence...")
        success = start_sequence()
        
        if success:
            logger.info("✅ Sequence started successfully")
        else:
            logger.error("❌ Failed to start sequence")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Unexpected error in start command: {e}")
        logger.error(traceback.format_exc())
        return False