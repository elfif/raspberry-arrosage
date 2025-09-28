#!/usr/bin/env python3
"""
Test script for debugging the reset API endpoint
"""

import requests
import json
import sys

def test_api_reset():
    print("🧪 Testing reset API endpoint...")
    print("=" * 40)
    
    base_url = "http://localhost:8000"
    
    try:
        # Test if API is running
        print("🔍 Testing API connectivity...")
        response = requests.get(f"{base_url}/")
        print(f"✅ API is running - Status: {response.status_code}")
        
        # Get current status before reset
        print("\n📊 Getting status before reset...")
        try:
            status_response = requests.get(f"{base_url}/status")
            print(f"Status endpoint response: {status_response.status_code}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"Current status: {json.dumps(status_data, indent=2)}")
        except Exception as e:
            print(f"⚠️  Could not get status: {e}")
        
        # Get current mode before reset
        print("\n📊 Getting mode before reset...")
        try:
            mode_response = requests.get(f"{base_url}/mode")
            print(f"Mode endpoint response: {mode_response.status_code}")
            if mode_response.status_code == 200:
                mode_data = mode_response.json()
                print(f"Current mode: {json.dumps(mode_data, indent=2)}")
        except Exception as e:
            print(f"⚠️  Could not get mode: {e}")
        
        # Call reset endpoint
        print("\n🔄 Calling reset endpoint...")
        reset_response = requests.post(f"{base_url}/reset")
        
        print(f"Reset response status: {reset_response.status_code}")
        print(f"Reset response headers: {dict(reset_response.headers)}")
        
        if reset_response.status_code == 200:
            try:
                reset_data = reset_response.json()
                print(f"✅ Reset response: {json.dumps(reset_data, indent=2)}")
            except json.JSONDecodeError as e:
                print(f"❌ Could not parse JSON response: {e}")
                print(f"Raw response: {reset_response.text}")
        else:
            print(f"❌ Reset failed with status {reset_response.status_code}")
            print(f"Response text: {reset_response.text}")
        
        # Get status after reset
        print("\n📊 Getting status after reset...")
        try:
            status_response = requests.get(f"{base_url}/status")
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"Status after reset: {json.dumps(status_data, indent=2)}")
        except Exception as e:
            print(f"⚠️  Could not get status after reset: {e}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API - is it running?")
        print("💡 Start the API with: python api.py")
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api_reset()
