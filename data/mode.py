#!/usr/bin/env python3
"""
Mode Management Script

This script provides functions to interact with the Redis 'mode.current' entry.
It supports getting and setting the current mode with validation.
"""

import json
import time
from typing import Optional
from .redis import get_json_from_redis, set_json_to_redis
from loop.sequence import start_sequence
from hardware.relay.relays import close_all_relays

# Mode constants - use these instead of raw strings
MODE_MANUAL = "manual"
MODE_AUTO = "auto"
MODE_SEMI_AUTO = "semi_auto"
MODE_PAUSE = "pause"

# List of valid modes for validation
VALID_MODES = [MODE_MANUAL, MODE_AUTO, MODE_SEMI_AUTO, MODE_PAUSE]

def get_mode() -> Optional[str]:
    """
    Get the current mode from Redis.
    
    Returns:
        str: Current mode value, or None if not found or error occurred
    """
    try:
        # Get the mode data from Redis using centralized function
        parsed_mode = get_json_from_redis('mode')
        if parsed_mode is None:
            print("⚠️  No mode data found in Redis")
            return None
        
        current_mode = parsed_mode.get('current')
        if current_mode not in VALID_MODES:
            print(f"⚠️  Invalid mode value found: {current_mode}")
            return None
        
        return current_mode
            
    except Exception as e:
        print(f"❌ Unexpected error getting mode: {e}")
        return None

def set_mode(new_mode: str) -> bool:
    """
    Set the current mode in Redis.
    
    Args:
        new_mode (str): The new mode value (must be one of the valid modes)
    
    Returns:
        bool: True if mode was set successfully, False otherwise
    """
    # Validate the new mode
    if new_mode not in VALID_MODES:
        print(f"❌ Invalid mode: {new_mode}")
        print(f"💡 Valid modes are: {', '.join(VALID_MODES)}")
        return False

    #Get the current mode
    current_mode = get_mode()   

    if current_mode == new_mode:
        print(f"❌ Mode {new_mode} is already set")
        return True

    try:
        # Create the mode object
        if new_mode == MODE_PAUSE:
            mode_data = {
                "current": new_mode,
                "previous_mode": get_mode(),
                "paused_at": int(time.time())
            }
        else:
            mode_data = {
                "current": new_mode
            }
        
        # Store in Redis using centralized function
        success = set_json_to_redis('mode', mode_data)
        if not success:
            print("❌ Failed to write mode to Redis")
            return False
        
        # Verify the data was written
        verification = get_mode()
        if verification == new_mode:
            print(f"✅ Successfully set mode to: {new_mode}")
        else:
            print(f"❌ Mode verification failed. Expected: {new_mode}, Got: {verification}")
            return False      

        if new_mode == MODE_PAUSE and current_mode != MODE_PAUSE:
            close_all_relays()
            
        return True
            
    except Exception as e:
        print(f"❌ Unexpected error setting mode: {e}")
        return False

def print_valid_modes():
    """Print all valid mode values."""
    print("📋 Valid mode values:")
    for mode in VALID_MODES:
        print(f"   - {mode}")

if __name__ == "__main__":
    from .redis import print_connection_info
    
    print("🔧 Mode Management Script")
    print("=" * 30)
    
    # Print connection info from centralized config
    print_connection_info()
    print()
    
    # Print valid modes
    print_valid_modes()
    print()
    
    # Get current mode
    print("📖 Getting current mode...")
    current = get_mode()
    if current:
        print(f"🔍 Current mode: {current}")
    else:
        print("❌ Could not retrieve current mode")
    
    print()
    print("💡 Usage examples:")
    print("   from data.mode import get_mode, set_mode, MODE_AUTO")
    print("   current_mode = get_mode()")
    print("   success = set_mode(MODE_AUTO)")
