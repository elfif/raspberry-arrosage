#!/usr/bin/env python3
"""
Redis Settings Writer Script

This script connects to Redis and writes two objects:

1. 'settings' key containing:
   - start_at: time property
   - sequence: array of 8 integers (7 values of 3600, last value of 0)
   - schedule: array of 7 booleans (6 false values, last one true)

2. 'mode' key containing:
   - current: string property (default: "manual")
"""

import json
import sys
from datetime import datetime, time
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from data.redis import set_json_to_redis, get_json_from_redis, print_connection_info

def write_settings_to_redis(host=None, port=None, db=None, password=None):
    """
    Write settings and mode data to Redis.
    
    Args:
        host (str, optional): Redis host address (uses config default if None)
        port (int, optional): Redis port (uses config default if None)
        db (int, optional): Redis database number (uses config default if None)
        password (str, optional): Redis password (uses config default if None)
    """
    try:
        print("✅ Successfully connected to Redis")
        
        # Create the settings object
        settings = {
            "start_at": "20:00",  # Default start time at 20:00
            "sequence": [3600] * 7 + [0],  # 7 values of 3600, 1 value of 0
            "schedule": [False] * 6 + [True]  # 6 false values, 1 true value
        }
        
        # Create the mode object
        mode = {
            "current": "manual"  # Default mode value
        }
        
        # Write settings to Redis using centralized function
        if not set_json_to_redis('settings', settings, host, port, db, password):
            print("❌ Failed to write settings to Redis")
            return False
        
        # Write mode to Redis using centralized function
        if not set_json_to_redis('mode', mode, host, port, db, password):
            print("❌ Failed to write mode to Redis")
            return False
        
        # Verify the settings data was written
        parsed_data = get_json_from_redis('settings', host, port, db, password)
        if parsed_data:
            print(f"✅ Successfully wrote settings to Redis key 'settings'")
            print(f"📊 Data structure:")
            print(f"   🔑 Key: settings")
            print(f"   💾 Value type: {type(parsed_data)}")
            print(f"   🕐 start_at: {parsed_data['start_at']}")
            print(f"   📏 sequence: {parsed_data['sequence']} (length: {len(parsed_data['sequence'])})")
            print(f"   📅 schedule: {parsed_data['schedule']} (length: {len(parsed_data['schedule'])})")
        else:
            print("❌ Failed to verify settings data was written to Redis")
            return False
        
        # Verify the mode data was written
        parsed_mode = get_json_from_redis('mode', host, port, db, password)
        if parsed_mode:
            print(f"✅ Successfully wrote mode to Redis key 'mode'")
            print(f"📊 Mode structure:")
            print(f"   🔑 Key: mode")
            print(f"   💾 Value type: {type(parsed_mode)}")
            print(f"   ⚙️  current: {parsed_mode['current']}")
        else:
            print("❌ Failed to verify mode data was written to Redis")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error occurred: {e}")
        return False

def read_settings_from_redis(host=None, port=None, db=None, password=None):
    """
    Read settings and mode data from Redis for verification.
    
    Args:
        host (str, optional): Redis host address (uses config default if None)
        port (int, optional): Redis port (uses config default if None)
        db (int, optional): Redis database number (uses config default if None)
        password (str, optional): Redis password (uses config default if None)
    """
    try:
        # Read settings data using centralized function
        parsed_data = get_json_from_redis('settings', host, port, db, password)
        if parsed_data:
            print(f"📖 Current settings in Redis:")
            print(f"   🔑 Key: settings")
            print(f"   🕐 start_at: {parsed_data['start_at']}")
            print(f"   📏 sequence: {parsed_data['sequence']}")
            print(f"   📅 schedule: {parsed_data['schedule']}")
        else:
            print("❌ No data found for key 'settings'")
        
        # Read mode data using centralized function
        parsed_mode = get_json_from_redis('mode', host, port, db, password)
        if parsed_mode:
            print(f"📖 Current mode in Redis:")
            print(f"   🔑 Key: mode")
            print(f"   ⚙️  current: {parsed_mode['current']}")
        else:
            print("❌ No data found for key 'mode'")
            
        return {"settings": parsed_data, "mode": parsed_mode}
            
    except Exception as e:
        print(f"❌ Error reading from Redis: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Redis Settings Writer Script")
    print("=" * 40)
    
    # Print connection info from centralized config
    print_connection_info()
    print()
    
    # Write settings to Redis
    success = write_settings_to_redis()
    
    if success:
        print()
        print("🔄 Verifying data...")
        read_settings_from_redis()
        print()
        print("✅ Script completed successfully!")
    else:
        print()
        print("❌ Script failed!")
        sys.exit(1)
