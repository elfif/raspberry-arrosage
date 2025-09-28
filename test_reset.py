#!/usr/bin/env python3
"""
Test script for debugging the reset function
"""

import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_reset():
    print("🧪 Testing reset function...")
    print("=" * 40)
    
    try:
        # Test imports
        print("📦 Testing imports...")
        from commands.reset import reset
        print("✅ Reset function imported successfully")
        
        from data.status import get_status
        print("✅ Status functions imported successfully")
        
        from data.mode import get_mode
        print("✅ Mode functions imported successfully")
        
        # Show current state before reset
        print("\n📊 Current state before reset:")
        current_mode = get_mode()
        current_status = get_status()
        print(f"   Mode: {current_mode}")
        print(f"   Status: {current_status}")
        
        # Call reset function
        print("\n🔄 Calling reset function...")
        success = reset()
        print(f"Reset result: {success}")
        
        # Show state after reset
        print("\n📊 Current state after reset:")
        current_mode = get_mode()
        current_status = get_status()
        print(f"   Mode: {current_mode}")
        print(f"   Status: {current_status}")
        
        if success:
            print("\n✅ Reset test completed successfully!")
        else:
            print("\n❌ Reset test failed!")
            
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_reset()
