#!/usr/bin/env python3
"""
Resume Mechanism for Arrosage System

This module provides resume functionality for the watering system.
When resumed, the system calculates pause duration, updates the status timing,
reopens the relay, and restores the previous mode.
"""

import sys
import os
import time

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.mode import get_mode, set_mode
from data.status import get_status, set_open_relay
from data.redis import set_json_to_redis
from hardware.relay.relays import open_relay

def resume() -> bool:
    """
    Resume the system from PAUSE mode.
    
    This function:
    1. Gets the current mode and checks for paused_at value
    2. Calculates the delta in seconds between now and paused_at
    3. Gets the current status
    4. Adds the calculated delta to should_close_at
    5. Updates the status with the new values
    6. Opens the relay with opened_relay
    7. Sets the mode back to previous_mode value
    
    Returns:
        bool: True if resume was successful, False otherwise
    """
    try:
        print("🔄 Starting resume process...")
        
        # Get mode data to check for paused_at and previous_mode
        from data.redis import get_json_from_redis
        mode_data = get_json_from_redis('mode')
        print(f"📖 Mode data: {mode_data}")
        
        if mode_data is None:
            print("❌ No mode data found")
            return False
        
        paused_at = mode_data.get('paused_at')
        print(f"⏰ Paused at: {paused_at}")
        if paused_at is None:
            print("❌ No paused_at value found in mode data")
            return False
        
        previous_mode = mode_data.get('previous_mode')
        print(f"🔄 Previous mode: {previous_mode}")
        if previous_mode is None:
            print("❌ No previous_mode value found in mode data")
            return False
        
        # Calculate delta in seconds between now and paused_at
        current_time = int(time.time())
        delta_seconds = current_time - paused_at
        print(f"⏱️  Current time: {current_time}, Delta: {delta_seconds} seconds")
        
        # Get current status
        status = get_status()
        print(f"📊 Status: {status}")
        if status is None:
            print("❌ No status found")
            return False
        
        opened_relay = status.get('opened_relay')
        print(f"🔌 Opened relay: {opened_relay}")
        if opened_relay is None or opened_relay < 0 or opened_relay > 7:
            print(f"❌ Invalid relay number: {opened_relay}")
            return False
        
        # Add the calculated delta to should_close_at if it exists
        should_close_at = status.get('should_close_at')
        print(f"⏰ Original should_close_at: {should_close_at}")
        if should_close_at is not None:
            new_should_close_at = should_close_at + delta_seconds
            status['should_close_at'] = new_should_close_at
            print(f"⏰ New should_close_at: {new_should_close_at}")
        else:
            print("⚠️  No should_close_at found in status")
        
        # Update the status with the new values
        print("💾 Updating status...")
        success = set_json_to_redis('status', status)
        if not success:
            print("❌ Failed to update status in Redis")
            return False
        print("✅ Status updated successfully")
        
        # Open the relay with opened_relay
        print(f"🔌 Opening relay {opened_relay}...")
        try:
            open_relay(opened_relay)
            print(f"✅ Relay {opened_relay} opened successfully")
        except Exception as e:
            print(f"❌ Failed to open relay {opened_relay}: {e}")
            return False
        
        # Set the mode back to previous_mode value
        print(f"🔄 Setting mode back to: {previous_mode}")
        if not set_mode(previous_mode):
            print(f"❌ Failed to set mode to {previous_mode}")
            return False
        print(f"✅ Mode set to {previous_mode} successfully")
        
        print("✅ Resume completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error during resume: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    from data.mode import get_mode
    
    print("🔧 Resume Mechanism Test")
    print("=" * 30)
    
    print("Current mode:", get_mode())
    print("Calling resume()...")
    
    success = resume()
    if success:
        print("✅ Resume successful")
    else:
        print("❌ Resume failed")
    
    print("New mode:", get_mode())
