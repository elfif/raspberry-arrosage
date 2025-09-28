#!/usr/bin/env python3
"""
Test Script for Semi-Auto Mode

This script tests the semi-automatic mode functionality by:
- Setting mode to SEMI_AUTO
- Configuring fast relay durations (10 seconds each)
- Manually starting the sequence
- Running the main loop to handle automatic progression
"""

import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.redis import set_json_to_redis
from data.mode import set_mode, MODE_SEMI_AUTO
from loop.sequence import start_sequence
from loop.main import main

def setup_semi_auto_settings():
    """
    Set up semi-auto test settings in Redis:
    - Set mode to SEMI_AUTO
    - All relays stay open for 10 seconds
    - Schedule is not used in semi-auto mode
    """
    print("🔧 Setting up semi-auto test conditions...")
    
    # Set mode to SEMI_AUTO
    if not set_mode(MODE_SEMI_AUTO):
        print("❌ Failed to set mode to SEMI_AUTO")
        return False
    print(f"✅ Mode set to: {MODE_SEMI_AUTO}")
    
    # Create test settings with fast relay durations
    test_settings = {
        "start_at": "00:00",  # Not used in semi-auto mode
        "sequence": [10] * 8,  # All 8 relays stay open for 30 seconds
        "schedule": [False] * 7  # Not used in semi-auto mode
    }
    
    # Write settings to Redis
    success = set_json_to_redis('settings', test_settings)
    if success:
        print(f"✅ Test settings configured:")
        print(f"   🤖 Mode: {MODE_SEMI_AUTO}")
        print(f"   ⏱️  Relay duration: 30 seconds each")
        print(f"   🎯 Total test duration: ~240 seconds (8 relays × 30s)")
        return True
    else:
        print("❌ Failed to write test settings to Redis")
        return False

def main_test():
    """Main test function."""
    print("🧪 Semi-Auto Mode Test Script")
    print("=" * 40)
    
    # Setup test conditions
    if not setup_semi_auto_settings():
        print("❌ Test setup failed, exiting...")
        sys.exit(1)
    
    print()
    print("🚀 Starting sequence manually...")
    if not start_sequence():
        print("❌ Failed to start sequence, exiting...")
        sys.exit(1)
    
    print("✅ Sequence started successfully!")
    print()
    print("🔄 Starting main loop...")
    print("💡 The loop will:")
    print("   1. Detect the running sequence")
    print("   2. Automatically progress through all 8 relays")
    print("   3. Each relay will run for 30 seconds")
    print("   4. Complete the full sequence automatically")
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
