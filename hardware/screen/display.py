#!/usr/bin/env python3
"""
OLED Display wrapper.

Thin wrapper around the vendored Waveshare driver that tolerates missing
hardware (SPI/GPIO) by degrading to a no-op. This allows the watering loop
to keep running even if the screen is disconnected or unsupported.
"""

import os
import sys
from typing import Optional

from PIL import Image

WIDTH = 128
HEIGHT = 128

_screen_dir = os.path.dirname(os.path.abspath(__file__))
if _screen_dir not in sys.path:
    sys.path.append(_screen_dir)


class Display:
    """Small facade over the Waveshare OLED_1in5_b driver."""

    def __init__(self, spi_freq: int = 1000000):
        self._spi_freq = spi_freq
        self._disp = None
        self._available = False

    def init(self) -> bool:
        """
        Initialize the OLED. Returns True on success, False if the hardware is
        not available (e.g. running off-Pi or the screen is disconnected).
        """
        try:
            from waveshare_OLED import OLED_1in5_b  # type: ignore
        except Exception as e:
            print(f"⚠️  OLED driver not importable ({e}); display disabled.")
            self._available = False
            return False

        try:
            self._disp = OLED_1in5_b.OLED_1in5_b(spi_freq=self._spi_freq)
            self._disp.Init()
            self._disp.clear()
            self._available = True
            print("✅ OLED initialized (128x128)")
            return True
        except Exception as e:
            print(f"⚠️  OLED init failed ({e}); display disabled.")
            self._disp = None
            self._available = False
            return False

    @property
    def available(self) -> bool:
        return self._available and self._disp is not None

    def show(self, image: Image.Image) -> bool:
        """Push a PIL image to the screen. Returns True on success."""
        if not self.available:
            return False
        try:
            img = image
            if img.size != (WIDTH, HEIGHT):
                img = img.resize((WIDTH, HEIGHT))
            self._disp.ShowImage(self._disp.getbuffer(img))
            return True
        except Exception as e:
            print(f"⚠️  OLED show failed: {e}")
            return False

    def clear(self) -> None:
        if not self.available:
            return
        try:
            self._disp.clear()
        except Exception as e:
            print(f"⚠️  OLED clear failed: {e}")

    def close(self) -> None:
        """Clear the screen and release hardware resources."""
        if not self.available:
            return
        try:
            self._disp.clear()
        except Exception:
            pass
        try:
            self._disp.module_exit()
        except Exception:
            pass
        self._disp = None
        self._available = False


_font_path: Optional[str] = None


def get_font_path() -> str:
    """Return the absolute path to the vendored TrueType font."""
    global _font_path
    if _font_path is None:
        _font_path = os.path.join(_screen_dir, "fonts", "Font.ttc")
    return _font_path
