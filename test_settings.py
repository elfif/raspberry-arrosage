#!/usr/bin/env python3
"""
Test script for debugging the settings functionality
"""

import sys
import os
import json

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_settings_direct():
    print("🧪 Testing settings retrieval directly...")
    print("=" * 40)
    
    try:
        # Test Redis connection and settings retrieval
        print("📦 Testing Redis import...")
        from data.redis import get_json_from_redis
        print("✅ Redis functions imported successfully")
        
        # Get settings from Redis
        print("\n📖 Getting settings from Redis...")
        settings = get_json_from_redis('settings')
        print(f"Settings result: {settings}")
        print(f"Settings type: {type(settings)}")
        
        if settings is None:
            print("❌ No settings found in Redis")
            print("💡 You may need to run the seeder script first:")
            print("   python data/seeder/redis_settings_writer.py")
        else:
            print("✅ Settings retrieved successfully!")
            print(f"Settings content: {json.dumps(settings, indent=2)}")
            
            # Validate settings structure
            print("\n🔍 Validating settings structure...")
            if 'start_at' in settings:
                print(f"✅ start_at: {settings['start_at']}")
            else:
                print("❌ Missing start_at field")
                
            if 'sequence' in settings:
                sequence = settings['sequence']
                print(f"✅ sequence: {sequence} (length: {len(sequence)})")
                if len(sequence) != 8:
                    print("⚠️  Sequence should have exactly 8 values")
            else:
                print("❌ Missing sequence field")
                
            if 'schedule' in settings:
                schedule = settings['schedule']
                print(f"✅ schedule: {schedule} (length: {len(schedule)})")
                if len(schedule) != 7:
                    print("⚠️  Schedule should have exactly 7 values")
            else:
                print("❌ Missing schedule field")
                
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

def test_settings_api():
    print("\n🌐 Testing settings API endpoint...")
    print("=" * 40)
    
    try:
        import requests
        
        # Test API connectivity
        print("🔍 Testing API connectivity...")
        response = requests.get("http://localhost:8000/")
        print(f"✅ API is running - Status: {response.status_code}")
        
        # Test settings endpoint
        print("\n📖 Testing settings endpoint...")
        settings_response = requests.get("http://localhost:8000/settings")
        print(f"Settings endpoint status: {settings_response.status_code}")
        
        if settings_response.status_code == 200:
            settings_data = settings_response.json()
            print(f"✅ Settings API response: {json.dumps(settings_data, indent=2)}")
        else:
            print(f"❌ Settings endpoint failed with status {settings_response.status_code}")
            print(f"Response text: {settings_response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API - is it running?")
        print("💡 Start the API with: python api.py")
    except Exception as e:
        print(f"❌ API test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_settings_direct()
    test_settings_api()
