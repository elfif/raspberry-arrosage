import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hardware.relay.relays import close_all_relays
from data.status import clear_status
from data.history import log_current_relay_close

def reset():
    """
    Reset the system to the initial state.
    """
    try:
        print("🔄 Starting system reset...")

        # Record any currently-open relay before closing
        log_current_relay_close()

        # Close all relays
        print("1️⃣ Closing all relays...")
        try:
            close_all_relays()
            print("✅ All relays closed successfully")
        except Exception as e:
            print(f"❌ Failed to close relays: {e}")
            return False
        
        # Clear status
        print("2️⃣ Clearing status...")
        try:
            success = clear_status()
            if success:
                print("✅ Status cleared successfully")
            else:
                print("❌ Failed to clear status")
                return False
        except Exception as e:
            print(f"❌ Error clearing status: {e}")
            return False
        
        print("✅ System reset completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error during reset: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print(reset())