

import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.mode import get_mode, set_mode, MODE_MANUAL
from hardware.relay.relays import close_all_relays
from data.status import clear_status

def manual():
    """
    Set the mode to manual.
    """
    close_all_relays()
    clear_status()
    set_mode(MODE_MANUAL)
    return MODE_MANUAL

if __name__ == "__main__":
    print(manual())