#!/usr/bin/env python3
"""
Redis Settings Writer Script

This script connects to Redis and writes a settings object containing:
- start_at: time property
- sequence: array of 8 integers (7 values of 3600, last value of 0)
- schedule: array of 7 booleans (6 false values, last one true)
"""

import redis
import json
import sys
from datetime import datetime, time

def write_settings_to_redis(host='localhost', port=6379, db=0, password=None):
    """
    Write settings data to Redis.
    
    Args:
        host (str): Redis host address (default: localhost)
        port (int): Redis port (default: 6379)
        db (int): Redis database number (default: 0)
        password (str): Redis password if authentication is required (default: None)
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
        
        # Create the settings object with the new structure
        settings = {
            "start_at": "08:00",  # Default start time at 8:00 AM
            "sequence": [3600] * 7 + [0],  # 7 values of 3600, 1 value of 0
            "schedule": [False] * 6 + [True]  # 6 false values, 1 true value
        }
        
        # Convert to JSON string for storage
        settings_json = json.dumps(settings, indent=2)
        
        # Write to Redis with key 'settings'
        r.set('settings', settings_json)
        
        # Verify the data was written
        stored_data = r.get('settings')
        if stored_data:
            parsed_data = json.loads(stored_data)
            print(f"✅ Successfully wrote settings to Redis key 'settings'")
            print(f"📊 Data structure:")
            print(f"   🔑 Key: settings")
            print(f"   💾 Value type: {type(parsed_data)}")
            print(f"   🕐 start_at: {parsed_data['start_at']}")
            print(f"   📏 sequence: {parsed_data['sequence']} (length: {len(parsed_data['sequence'])})")
            print(f"   📅 schedule: {parsed_data['schedule']} (length: {len(parsed_data['schedule'])})")
        else:
            print("❌ Failed to verify data was written to Redis")
            return False
            
        return True
        
    except redis.ConnectionError as e:
        print(f"❌ Failed to connect to Redis: {e}")
        print("💡 Make sure Redis is running and accessible")
        return False
    except Exception as e:
        print(f"❌ Error occurred: {e}")
        return False

def read_settings_from_redis(host='localhost', port=6379, db=0, password=None):
    """
    Read settings data from Redis for verification.
    
    Args:
        host (str): Redis host address (default: localhost)
        port (int): Redis port (default: 6379)
        db (int): Redis database number (default: 0)
        password (str): Redis password if authentication is required (default: None)
    """
    try:
        r = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True
        )
        
        stored_data = r.get('settings')
        if stored_data:
            parsed_data = json.loads(stored_data)
            print(f"📖 Current settings in Redis:")
            print(f"   🔑 Key: settings")
            print(f"   🕐 start_at: {parsed_data['start_at']}")
            print(f"   📏 sequence: {parsed_data['sequence']}")
            print(f"   📅 schedule: {parsed_data['schedule']}")
            return parsed_data
        else:
            print("❌ No data found for key 'settings'")
            return None
            
    except Exception as e:
        print(f"❌ Error reading from Redis: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Redis Settings Writer Script")
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
    
    # Write settings to Redis
    success = write_settings_to_redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD
    )
    
    if success:
        print()
        print("🔄 Verifying data...")
        read_settings_from_redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD
        )
        print()
        print("✅ Script completed successfully!")
    else:
        print()
        print("❌ Script failed!")
        sys.exit(1)
