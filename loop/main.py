#!/usr/bin/env python3
"""
Main Loop for Arrosage System

This script runs the main control loop that monitors the system mode
and performs automated watering operations when in automatic or semi-automatic mode.
"""

import time
import sys
import os
from datetime import datetime

# Add parent directory to path to import data modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.mode import get_mode, MODE_AUTO, MODE_SEMI_AUTO
from data.status import get_status
from data.redis import get_json_from_redis
from loop.sequence import is_current_step_finished, start_step, start_sequence

def main():
    """Main control loop for the arrosage system."""
    
    try:
        while True:
            # Get current mode
            current_mode = get_mode()
            
            # Check if mode is automatic or semi-automatic
            if current_mode in [MODE_AUTO, MODE_SEMI_AUTO]:
                # Check if status entry exists
                status = get_status()
                if status is not None:
                    # Status exists, check if current step is finished
                    if is_current_step_finished():
                        opened_relay = status.get('opened_relay')
                        if opened_relay is not None and opened_relay < 7:
                            # Move to next step
                            next_relay = opened_relay + 1
                            start_step(next_relay)
                    # If step is not finished, continue waiting
                else:
                    # No status exists - check if we should start based on schedule
                    settings = get_json_from_redis('settings')
                    if settings is not None:
                        schedule = settings.get('schedule', [])
                        start_at = settings.get('start_at', '')
                        
                        if schedule and start_at:
                            # Get current day of week (0=Monday, 6=Sunday)
                            current_day = datetime.now().weekday()
                            # Get current time in HH:MM format
                            current_time = datetime.now().strftime("%H:%M")
                            
                            # Check if current day is scheduled and time matches
                            if (current_day < len(schedule) and 
                                schedule[current_day] and 
                                current_time == start_at):
                                start_sequence()
                
            
            # Sleep for 0.1 seconds
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        pass
    except Exception as e:
        sys.exit(1)




if __name__ == "__main__":
    main()
