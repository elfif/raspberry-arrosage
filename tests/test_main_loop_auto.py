#!/usr/bin/env python3
"""
Test Script for Main Loop

This script sets up test conditions and runs the main loop to verify
automatic scheduling and sequence progression functionality.
"""

import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.redis import set_json_to_redis
from data.mode import set_mode, MODE_AUTO
from loop.main import main

def setup_test_settings():
    """
    Set up test settings in Redis:
    - Set mode to AUTO
    - All relays stay open for 30 seconds
    - Schedule enabled only for current day
    - Start time set to now + 2 minutes
    """
    print("🔧 Setting up test conditions...")
    
    # Set mode to AUTO
    if not set_mode(MODE_AUTO):
        print("❌ Failed to set mode to AUTO")
        return False
    print(f"✅ Mode set to: {MODE_AUTO}")
    
    # Get current day of week (0=Monday, 6=Sunday)
    current_day = datetime.now().weekday()
    
    # Calculate start time (now + 2 minutes)
    start_time = datetime.now() + timedelta(minutes=1)
    start_at = start_time.strftime("%H:%M")
    
    # Create schedule array with only current day enabled
    schedule = [False] * 7  # Initialize all days as False
    schedule[current_day] = True  # Enable only current day
    
    # Create test settings
    test_settings = {
        "start_at": start_at,
        "sequence": [10] * 8,  # All 8 relays stay open for 10 seconds
        "schedule": schedule
    }
    
    # Write settings to Redis
    success = set_json_to_redis('settings', test_settings)
    if success:
        print(f"✅ Test settings configured:")
        print(f"   🤖 Mode: {MODE_AUTO}")
        print(f"   📅 Current day: {current_day} ({'Mon Tue Wed Thu Fri Sat Sun'.split()[current_day]})")
        print(f"   🕒 Start time: {start_at}")
        print(f"   ⏱️  Relay duration: 10 seconds each")
        print(f"   📋 Schedule: {schedule}")
        print(f"   🎯 Total test duration: ~4 minutes (8 relays × 30s)")
        return True
    else:
        print("❌ Failed to write test settings to Redis")
        return False

def main_test():
    """Main test function."""
    print("🧪 Main Loop Test Script")
    print("=" * 40)
    
    # Setup test conditions
    if not setup_test_settings():
        print("❌ Test setup failed, exiting...")
        sys.exit(1)
    
    print()
    print("🚀 Starting main loop...")
    print("💡 The loop will:")
    print("   1. Wait for the scheduled start time ( minutes from now)")
    print("   2. Automatically start the sequence")
    print("   3. Progress through all 8 relays (10 seconds each)")
    print("   4. Complete the full sequence")
    print()
    print("⌨️  Press Ctrl+C to stop the test")
    print("=" * 40)
    
    try:
        # Start the main loop
        main()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        print("👋 Test completed!")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main_test()
