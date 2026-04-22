#!/usr/bin/env python3
"""
Main Loop for Arrosage System

This script runs the main control loop that monitors the system mode
and performs automated watering operations when in automatic or semi-automatic mode.
"""

import time
import sys
import os
import threading
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.mode import get_mode, MODE_AUTO, MODE_SEMI_AUTO
from data.status import get_status
from data.redis import get_json_from_redis
from data.history import init_history_db, log_current_relay_close
from loop.sequence import is_current_step_finished, start_step, start_sequence
from loop.schedule import compute_next_sequence
from hardware.relay.relays import close_all_relays
from data.status import clear_status
from hardware.screen.display import Display
from hardware.screen.renderer import DisplayState, render
from network.config import load_config as load_network_config
from network.state import KEY_MODE as NETWORK_KEY_MODE, MODE_AP as NETWORK_MODE_AP
from network.watchdog import run as run_network_watchdog


RENDER_PERIOD_S = 1.0


def _build_display_state(now: datetime) -> DisplayState:
    """Build a DisplayState snapshot from current Redis state."""
    mode = get_mode()
    status = get_status()
    settings = get_json_from_redis("settings") or {}

    running = status is not None
    opened_relay = status.get("opened_relay") if status else None
    should_close_at = status.get("should_close_at") if status else None

    next_sequence = None
    if mode == MODE_AUTO and not running:
        schedule = settings.get("schedule") if isinstance(settings, dict) else None
        start_at = settings.get("start_at") if isinstance(settings, dict) else None
        next_sequence = compute_next_sequence(now, schedule, start_at)

    wifi_ap_active = get_json_from_redis(NETWORK_KEY_MODE) == NETWORK_MODE_AP

    return DisplayState(
        mode=mode,
        now=now,
        running=running,
        opened_relay=opened_relay,
        should_close_at=should_close_at,
        next_sequence=next_sequence,
        wifi_ap_active=wifi_ap_active,
    )


def _refresh_display(display: Display) -> None:
    if not display.available:
        return
    try:
        state = _build_display_state(datetime.now())
        image = render(state)
        display.show(image)
    except Exception as e:
        print(f"⚠️  Display refresh error: {e}")


def main():
    """Main control loop for the arrosage system."""

    init_history_db()

    try:
        net_cfg = load_network_config()
        threading.Thread(
            target=run_network_watchdog,
            args=(net_cfg,),
            daemon=True,
            name="netwatch",
        ).start()
    except Exception as e:
        print(f"⚠️  Failed to start network watchdog: {e}")

    display = Display()
    display.init()
    last_render = 0.0

    try:
        while True:
            current_mode = get_mode()

            if current_mode in [MODE_AUTO, MODE_SEMI_AUTO]:
                status = get_status()
                if status is not None:
                    if is_current_step_finished():
                        opened_relay = status.get('opened_relay')
                        raw_skipped = status.get("skipped_relays", []) or []
                        skipped = set(
                            x for x in raw_skipped
                            if isinstance(x, int) and 0 <= x <= 7
                        )
                        next_relay = (opened_relay or 0) + 1
                        while next_relay <= 7 and next_relay in skipped:
                            next_relay += 1
                        if opened_relay is not None and next_relay <= 7:
                            start_step(next_relay)
                        else:
                            log_current_relay_close()
                            close_all_relays()
                            clear_status()
                            print("✅ Sequence completed - all steps finished")
                elif current_mode == MODE_AUTO:
                    settings = get_json_from_redis('settings')
                    if settings is not None:
                        schedule = settings.get('schedule', [])
                        start_at = settings.get('start_at', '')

                        if schedule and start_at:
                            current_day = datetime.now().weekday()
                            current_time = datetime.now().strftime("%H:%M")

                            if (current_day < len(schedule) and
                                schedule[current_day] and
                                current_time == start_at):
                                start_sequence()

            now_ts = time.time()
            if now_ts - last_render >= RENDER_PERIOD_S:
                _refresh_display(display)
                last_render = now_ts

            time.sleep(0.2)

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"❌ Main loop error: {e}")
        sys.exit(1)
    finally:
        try:
            display.close()
        except Exception:
            pass




if __name__ == "__main__":
    main()
