#!/usr/bin/env python3
"""
Pause Mechanism for Arrosage System

This module provides pause functionality for the watering system.
When paused, the system sets mode to PAUSE and closes all relays.
"""

import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.mode import set_mode, MODE_PAUSE
from hardware.relay.relays import close_all_relays

def pause() -> bool:
    """
    Pause the system by setting mode to PAUSE and closing all relays.
    
    This function:
    1. Sets mode.current to PAUSE using set_mode function
    2. Closes all relays for safety
    
    Returns:
        bool: True if pause was successful, False otherwise
    """
    try:
        from data.mode import get_mode
        if get_mode() == MODE_PAUSE:
            return True
        # Set mode to PAUSE
        if not set_mode(MODE_PAUSE):
            return False
        
        # Close all relays
        try:
            close_all_relays()
            return True
        except Exception as e:
            return False
        
    except Exception as e:
        return False

if __name__ == "__main__":
    from data.mode import get_mode
    
    print("🔧 Pause Mechanism Test")
    print("=" * 30)
    
    print("Current mode:", get_mode())
    print("Calling pause()...")
    
    success = pause()
    if success:
        print("✅ Pause successful")
    else:
        print("❌ Pause failed")
    
    print("New mode:", get_mode())