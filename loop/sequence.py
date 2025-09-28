#!/usr/bin/env python3
"""
Sequence Management for Arrosage System

This module provides sequence functions for controlling the watering system,
including starting sequences that manage relay states and status tracking.
"""

import sys
import os
import time

# Add parent directory to path to import data and hardware modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.status import clear_status, set_open_relay, get_status
from data.redis import get_json_from_redis
from hardware.relay.relays import close_all_relays, open_relay

def start_sequence() -> bool:
    """
    Start the watering sequence by initializing the system state.
    
    This function clears the status and then starts with relay 0.
    
    Returns:
        bool: True if sequence completed successfully, False if any step failed
    """
    try:
        print("🚀 Starting watering sequence...")
        
        # Clear status first
        print("1️⃣ Clearing status...")
        if not clear_status():
            print("❌ Failed to clear status")
            return False
        
        # Start with relay 0
        print("2️⃣ Starting step 0...")
        if not start_step(0):
            print("❌ Failed to start step 0")
            return False
        
        print("✅ Start sequence completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error in start sequence: {e}")
        return False

def is_current_step_finished() -> bool:
    """
    Check if the current sequence step is finished based on duration.
    
    This function:
    1. Gets the current status from Redis
    2. Returns False if status is empty (no relay is opened)
    3. Gets the settings from Redis to find the duration for the opened relay
    4. Calculates if the relay has been open for the expected duration
    5. Returns True if the duration has elapsed, False otherwise
    
    Returns:
        bool: True if sequence is finished (duration elapsed), False otherwise
    """
    try:
        # Step 1: Get current status
        status = get_status()
        
        # Step 2: Return False if status is empty
        if status is None:
            return False
        
        # Validate status has required fields
        if 'opened_relay' not in status or 'opened_at' not in status:
            print("⚠️  Status is missing required fields")
            return False
        
        relay_should_close_at = status['should_close_at']
        opened_relay = status['opened_relay']
                
        # Step 3: Get settings from Redis
        settings = get_json_from_redis('settings')
        if settings is None:
            print("❌ Could not retrieve settings from Redis")
            return False
        
        # Validate settings has sequence
        if 'sequence' not in settings:
            print("❌ Settings missing 'sequence' field")
            return False
        
        sequence = settings['sequence']
        
        # Validate relay index is within bounds
        if opened_relay < 0 or opened_relay >= len(sequence):
            print(f"❌ Invalid relay index {opened_relay} for sequence of length {len(sequence)}")
            return False
        
        # Step 4: Get duration for the opened relay
        duration = sequence[opened_relay]
        
        # Step 5: Calculate if duration has elapsed
        current_time = int(time.time())
        expected_finish_time = relay_should_close_at
        
        # Return True if current time is equal or greater than expected finish time
        is_finished = current_time >= expected_finish_time
        
        if is_finished:
            print(f"✅ Current step finished - Relay {opened_relay} has been open for {duration} seconds")
        else:
            remaining_time = expected_finish_time - current_time
            print(f"⏳ Current step in progress - Relay {opened_relay}, {remaining_time}s remaining")
        
        return is_finished
        
    except Exception as e:
        print(f"❌ Unexpected error checking current step status: {e}")
        return False

def start_step(relay: int) -> bool:
    """
    Start a specific relay step in the sequence.
    
    This function:
    1. Validates the relay number (0-7)
    2. Closes all relays to ensure clean state
    3. Opens the specified relay
    4. Updates the status to reflect the opened relay
    
    Args:
        relay (int): Relay number between 0 and 7
    
    Returns:
        bool: True if step started successfully, False otherwise
    """
    # Validate relay number
    if not isinstance(relay, int) or relay < 0 or relay > 7:
        print(f"❌ Invalid relay number: {relay}")
        print("💡 Relay number must be an integer between 0 and 7")
        return False
    
    try:
        print(f"🔄 Starting step for relay {relay}...")
        
        # Step 1: Close all relays
        print("1️⃣ Closing all relays...")
        try:
            close_all_relays()
            print("✅ All relays closed")
        except Exception as e:
            print(f"❌ Failed to close all relays: {e}")
            return False
        
        # Step 2: Open the specified relay
        print(f"2️⃣ Opening relay {relay}...")
        try:
            open_relay(relay)
            print(f"✅ Relay {relay} opened")
        except Exception as e:
            print(f"❌ Failed to open relay {relay}: {e}")
            return False
        
        # Step 3: Update status
        print(f"3️⃣ Updating status for relay {relay}...")

        settings = get_json_from_redis('settings')
        if settings is None:
            print("❌ Could not retrieve settings from Redis")
            return False
        
        sequence = settings['sequence']
        duration = sequence[relay]
        if not set_open_relay(relay, duration):
            print("❌ Failed to update relay status")
            return False
        
        print(f"✅ Step started successfully for relay {relay}!")
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error starting step for relay {relay}: {e}")
        return False

