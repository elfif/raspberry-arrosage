#!/usr/bin/env python3
"""
Redis Settings Reader Script

This script connects to Redis and reads the settings object containing:
- start_at: time property
- sequence: array of 8 integers (7 values of 3600, last value of 0)
- schedule: array of 7 booleans (6 false values, last one true)
"""

import redis
import json
import sys
from typing import Dict, Any, Optional

def read_settings_from_redis(host='localhost', port=6379, db=0, password=None) -> Optional[Dict[str, Any]]:
    """
    Read settings data from Redis.
    
    Args:
        host (str): Redis host address (default: localhost)
        port (int): Redis port (default: 6379)
        db (int): Redis database number (default: 0)
        password (str): Redis password if authentication is required (default: None)
    
    Returns:
        Dict[str, Any] or None: The settings object if successful, None if failed
    """
    try:
        # Create Redis connection
        r = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True
        )
        
        # Test connection
        r.ping()
        print("✅ Successfully connected to Redis")
        
        # Read the settings key
        stored_data = r.get('settings')
        if stored_data:
            try:
                parsed_data = json.loads(stored_data)
                if isinstance(parsed_data, dict) and 'start_at' in parsed_data and 'sequence' in parsed_data and 'schedule' in parsed_data:
                    return parsed_data
                else:
                    print("⚠️  Warning: Data is not in the expected settings format")
                    return parsed_data
            except json.JSONDecodeError:
                print("⚠️  Warning: Data is not valid JSON")
                return stored_data
        else:
            print("❌ No data found for key 'settings'")
            return None
            
    except redis.ConnectionError as e:
        print(f"❌ Failed to connect to Redis: {e}")
        print("💡 Make sure Redis is running and accessible")
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

def check_redis_connection(host='localhost', port=6379, db=0, password=None) -> bool:
    """
    Check if Redis connection is available.
    
    Args:
        host (str): Redis host address
        port (int): Redis port
        db (int): Redis database number
        password (str): Redis password if authentication is required
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        r = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True
        )
        r.ping()
        return True
    except:
        return False

def main():
    """Main function to run the Redis settings reader."""
    print("📖 Redis Settings Reader Script")
    print("=" * 40)
    
    # Configuration - modify these values if needed
    REDIS_HOST = 'localhost'
    REDIS_PORT = 6379
    REDIS_DB = 0
    REDIS_PASSWORD = None  # Set this if your Redis requires authentication
    
    print(f"🔧 Configuration:")
    print(f"   Host: {REDIS_HOST}")
    print(f"   Port: {REDIS_PORT}")
    print(f"   Database: {REDIS_DB}")
    print(f"   Password: {'Set' if REDIS_PASSWORD else 'None'}")
    print()
    
    # Check connection first
    if not check_redis_connection(REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD):
        print("❌ Cannot connect to Redis. Please check your configuration.")
        print("💡 Make sure Redis is running and accessible")
        sys.exit(1)
    
    # Read settings from Redis
    settings = read_settings_from_redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD
    )
    
    if settings is not None:
        # Display the settings
        display_settings(settings)
        print("✅ Script completed successfully!")
    else:
        print("❌ Failed to read settings from Redis")
        print("💡 Make sure the 'settings' key exists and contains valid data")
        sys.exit(1)

if __name__ == "__main__":
    main()
