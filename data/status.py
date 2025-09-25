#!/usr/bin/env python3
"""
Status Management Script

This script provides functions to interact with the Redis 'status' entry.
It supports managing relay status information including which relay is opened
and when it was opened.
"""

import time
from typing import Optional, Dict, Any
from .redis import get_json_from_redis, set_json_to_redis, get_redis_connection

def clear_status() -> bool:
    """
    Clear the status entry in Redis (leave it empty).
    
    Returns:
        bool: True if status was cleared successfully, False otherwise
    """
    try:
        r = get_redis_connection()
        r.delete('status')
        print("✅ Status cleared successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error clearing status: {e}")
        return False

def set_open_relay(relay_number: int, duration: int = 0) -> bool:
    """
    Set the opened relay status with current timestamp.
    
    Args:
        relay_number (int): Relay number between 0 and 7
    
    Returns:
        bool: True if status was set successfully, False otherwise
    """
    # Validate relay number
    if not isinstance(relay_number, int) or relay_number < 0 or relay_number > 7:
        print(f"❌ Invalid relay number: {relay_number}")
        print("💡 Relay number must be an integer between 0 and 7")
        return False
    
    try:
        # Create status data with current timestamp
        status_data = {
            "opened_relay": relay_number,
            "opened_at": int(time.time())
        }

        if duration > 0:
            status_data["should_close_at"] = int(time.time()) + duration
        
        # Store in Redis using centralized function
        success = set_json_to_redis('status', status_data)
        if not success:
            print("❌ Failed to write status to Redis")
            return False
        
        print(f"✅ Successfully set opened relay to: {relay_number}")
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error setting relay status: {e}")
        return False

def get_status() -> Optional[Dict[str, Any]]:
    """
    Get the current status from Redis.
    
    Returns:
        Dict[str, Any] or None: Status data containing 'opened_relay' and 'opened_at', 
                               or None if no status found or error occurred
    """
    try:
        # Get the status data from Redis using centralized function
        status_data = get_json_from_redis('status')
        
        if status_data is None:
            # Status is empty/cleared - this is valid
            return None
        
        # Validate status data structure
        if not isinstance(status_data, dict):
            print(f"⚠️  Invalid status data format: {type(status_data)}")
            return None
        
        # Check for required fields if data exists
        if 'opened_relay' in status_data or 'opened_at' in status_data:
            # Validate opened_relay if present
            if 'opened_relay' in status_data:
                relay_num = status_data.get('opened_relay')
                if not isinstance(relay_num, int) or relay_num < 0 or relay_num > 7:
                    print(f"⚠️  Invalid opened_relay value: {relay_num}")
                    return None
            
            # Validate opened_at if present
            if 'opened_at' in status_data:
                timestamp = status_data.get('opened_at')
                if not isinstance(timestamp, (int, float)) or timestamp < 0:
                    print(f"⚠️  Invalid opened_at timestamp: {timestamp}")
                    return None
        
        return status_data
        
    except Exception as e:
        print(f"❌ Unexpected error getting status: {e}")
        return None

if __name__ == "__main__":
    from .redis import print_connection_info
    
    print("🔧 Status Management Script")
    print("=" * 32)
    
    # Print connection info from centralized config
    print_connection_info()
    print()
    
    # Get current status
    print("📖 Getting current status...")
    current_status = get_status()
    if current_status:
        print(f"🔍 Current status: {current_status}")
        if 'opened_relay' in current_status:
            print(f"   📡 Opened relay: {current_status['opened_relay']}")
        if 'opened_at' in current_status:
            opened_time = time.ctime(current_status['opened_at'])
            print(f"   ⏰ Opened at: {opened_time}")
    else:
        print("📭 Status is empty (cleared)")
    
    print()
    print("💡 Usage examples:")
    print("   from data.status import get_status, set_open_relay, clear_status")
    print("   status = get_status()")
    print("   success = set_open_relay(3)  # Open relay 3")
    print("   success = clear_status()     # Clear status")
