#!/usr/bin/env python3
"""
Redis Settings Reader Script

This script connects to Redis and reads the settings object containing:
- start_at: time property
- sequence: array of 8 integers (7 values of 3600, last value of 0)
- schedule: array of 7 booleans (6 false values, last one true)
"""

import json
import sys
from typing import Dict, Any, Optional
from data.redis import get_json_from_redis, check_redis_connection, print_connection_info

def read_settings_from_redis(host=None, port=None, db=None, password=None) -> Optional[Dict[str, Any]]:
    """
    Read settings data from Redis.
    
    Args:
        host (str, optional): Redis host address (uses config default if None)
        port (int, optional): Redis port (uses config default if None)
        db (int, optional): Redis database number (uses config default if None)
        password (str, optional): Redis password (uses config default if None)
    
    Returns:
        Dict[str, Any] or None: The settings object if successful, None if failed
    """
    try:
        print("✅ Successfully connected to Redis")
        
        # Read the settings key using centralized function
        parsed_data = get_json_from_redis('settings', host, port, db, password)
        if parsed_data:
            if isinstance(parsed_data, dict) and 'start_at' in parsed_data and 'sequence' in parsed_data and 'schedule' in parsed_data:
                return parsed_data
            else:
                print("⚠️  Warning: Data is not in the expected settings format")
                return parsed_data
        else:
            print("❌ No data found for key 'settings'")
            return None
            
    except Exception as e:
        print(f"❌ Error occurred: {e}")
        return None

def read_mode_from_redis(host=None, port=None, db=None, password=None) -> Optional[Dict[str, Any]]:
    """
    Read mode data from Redis.
    
    Args:
        host (str, optional): Redis host address (uses config default if None)
        port (int, optional): Redis port (uses config default if None)
        db (int, optional): Redis database number (uses config default if None)
        password (str, optional): Redis password (uses config default if None)
    
    Returns:
        Dict[str, Any] or None: The mode object if successful, None if failed
    """
    try:
        # Read the mode key using centralized function
        parsed_mode = get_json_from_redis('mode', host, port, db, password)
        if parsed_mode:
            if isinstance(parsed_mode, dict) and 'current' in parsed_mode:
                return parsed_mode
            else:
                print("⚠️  Warning: Data is not in the expected mode format")
                return parsed_mode
        else:
            print("❌ No data found for key 'mode'")
            return None
    except Exception as e:
        print(f"❌ Error occurred: {e}")
        return None


def display_settings(settings: Dict[str, Any]) -> None:
    """
    Display the settings in a formatted way.
    
    Args:
        settings (Dict[str, Any]): The settings object to display
    """
    if not settings:
        print("❌ No settings to display")
        return
    
    print("\n📊 Settings Data:")
    print("=" * 50)
    print(f"🔑 Key: settings")
    print(f"💾 Data type: {type(settings)}")
    print()
    
    # Display start_at
    print(f"🕐 start_at: {settings.get('start_at', 'N/A')}")
    print()
    
    # Display sequence
    sequence = settings.get('sequence', [])
    print(f"📏 sequence (length: {len(sequence)}):")
    for i, value in enumerate(sequence):
        if i == len(sequence) - 1:
            # Last element (should be 0)
            print(f"   [{i:2d}]: {value:4d} ← Last element")
        else:
            # Other elements (should be 3600)
            print(f"   [{i:2d}]: {value:4d}")
    print()
    
    # Display schedule
    schedule = settings.get('schedule', [])
    print(f"📅 schedule (length: {len(schedule)}):")
    for i, value in enumerate(schedule):
        if i == len(schedule) - 1:
            # Last element (should be True)
            print(f"   [{i:2d}]: {value} ← Last element")
        else:
            # Other elements (should be False)
            print(f"   [{i:2d}]: {value}")
    print()
    
    # Summary statistics
    if 'sequence' in settings and 'schedule' in settings:
        sequence = settings['sequence']
        schedule = settings['schedule']
        
        print("📈 Summary:")
        print(f"   start_at: {settings.get('start_at', 'N/A')}")
        print(f"   sequence - First 7 values: {sequence[:7] if len(sequence) >= 7 else sequence}")
        print(f"   sequence - Last value: {sequence[-1] if sequence else 'N/A'}")
        print(f"   schedule - First 6 values: {schedule[:6] if len(schedule) >= 6 else schedule}")
        print(f"   schedule - Last value: {schedule[-1] if schedule else 'N/A'}")
        
        # Check if data matches expected pattern
        expected_sequence = [3600] * 7 + [0]
        expected_schedule = [False] * 6 + [True]
        
        sequence_correct = sequence == expected_sequence
        schedule_correct = schedule == expected_schedule
        
        print(f"   sequence matches expected pattern: {sequence_correct}")
        print(f"   schedule matches expected pattern: {schedule_correct}")
        
        if sequence_correct and schedule_correct:
            print("✅ All data matches expected patterns!")
        else:
            print("⚠️  Some data does not match expected patterns")

def display_mode(mode: Dict[str, Any]) -> None:
    """
    Display the mode in a formatted way.
    """
    if not mode:
        print("❌ No mode to display")
        return
    
    print("\n📊 Mode Data:")
    print("=" * 50)
    print(f"🔑 current value: {mode['current']}")
    print()

# Note: check_redis_connection is now imported from data.redis module

def main():
    """Main function to run the Redis settings reader."""
    print("📖 Redis Settings Reader Script")
    print("=" * 40)
    
    # Print connection info from centralized config
    print_connection_info()
    print()
    
    # Check connection first
    if not check_redis_connection():
        print("❌ Cannot connect to Redis. Please check your configuration.")
        print("💡 Make sure Redis is running and accessible")
        sys.exit(1)

    # Read mode from Redis
    mode = read_mode_from_redis()
    if mode is not None:
        # Display the mode
        display_mode(mode)
        print("✅ Mode read successfully!")
    else:
        print("❌ Failed to read mode from Redis")
        print("💡 Make sure the 'mode' key exists and contains valid data")

    print()

    # Read settings from Redis
    settings = read_settings_from_redis()
    if settings is not None:
        # Display the settings
        display_settings(settings)
        print("✅ Settings read successfully!")
    else:
        print("❌ Failed to read settings from Redis")
        print("💡 Make sure the 'settings' key exists and contains valid data")
    
    print("✅ Script completed successfully!")

if __name__ == "__main__":
    main()
