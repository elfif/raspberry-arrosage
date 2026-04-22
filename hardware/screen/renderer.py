#!/usr/bin/env python3
"""
OLED renderer.

Builds a 128x128 1-bit PIL image describing the current system state, following
the layout spec (mode bar on top + context-sensitive body).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from .display import WIDTH, HEIGHT, get_font_path

MODE_AUTO = "auto"
MODE_SEMI_AUTO = "semi_auto"
MODE_MANUAL = "manual"
MODE_PAUSE = "pause"

FILL_ON = 15
FILL_OFF = 0

MODE_BAR_HEIGHT = round(HEIGHT * 0.20)
BAND_20 = round(HEIGHT * 0.20)
BAND_40 = round(HEIGHT * 0.40)
BAND_60 = round(HEIGHT * 0.60)
BODY_TOP = MODE_BAR_HEIGHT
BODY_HEIGHT = HEIGHT - MODE_BAR_HEIGHT

STATUS_ZONE_W = 18


@dataclass
class DisplayState:
    mode: Optional[str]
    now: datetime
    running: bool = False
    opened_relay: Optional[int] = None
    should_close_at: Optional[int] = None
    next_sequence: Optional[datetime] = None
    wifi_ap_active: bool = False


_MODE_LABELS = {
    MODE_AUTO: "auto",
    MODE_SEMI_AUTO: "semi-auto",
    MODE_MANUAL: "manuel",
    MODE_PAUSE: "pause",
}


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(get_font_path(), size)


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont):
    """Return (width, height) of rendered text."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _fit_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_w: int,
    max_h: int,
    start_size: int,
    min_size: int = 8,
) -> ImageFont.FreeTypeFont:
    """Return the largest font <= start_size that fits `text` within max_w x max_h."""
    size = start_size
    while size > min_size:
        font = _font(size)
        w, h = _text_size(draw, text, font)
        if w <= max_w and h <= max_h:
            return font
        size -= 1
    return _font(min_size)


def _draw_centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    band_height: int,
    font: ImageFont.FreeTypeFont,
    fill: int = FILL_ON,
) -> None:
    """Draw `text` horizontally centered, vertically centered inside the band."""
    w, h = _text_size(draw, text, font)
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (WIDTH - w) // 2 - bbox[0]
    ty = y + (band_height - h) // 2 - bbox[1]
    draw.text((x, ty), text, font=font, fill=fill)


def _wrap_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_w: int,
) -> list:
    """Naive word wrapping at spaces. Returns a list of lines that fit max_w."""
    words = text.split()
    if not words:
        return [""]
    lines: list = []
    current = words[0]
    for word in words[1:]:
        candidate = current + " " + word
        w, _ = _text_size(draw, candidate, font)
        if w <= max_w:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _draw_wrapped_centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    band_height: int,
    max_w: int,
    start_size: int,
    min_size: int = 10,
) -> None:
    """
    Fit `text` into max_w x band_height, wrapping on spaces and shrinking the
    font until everything fits. Renders centered both axes.
    """
    size = start_size
    while size >= min_size:
        font = _font(size)
        lines = _wrap_lines(draw, text, font, max_w)
        line_heights = [_text_size(draw, line, font)[1] for line in lines]
        widths = [_text_size(draw, line, font)[0] for line in lines]
        total_h = sum(line_heights) + max(0, len(lines) - 1) * 2
        if total_h <= band_height and all(w <= max_w for w in widths):
            cursor_y = y + (band_height - total_h) // 2
            for line, lh in zip(lines, line_heights):
                lw, _ = _text_size(draw, line, font)
                bbox = draw.textbbox((0, 0), line, font=font)
                x = (WIDTH - lw) // 2 - bbox[0]
                draw.text((x, cursor_y - bbox[1]), line, font=font, fill=FILL_ON)
                cursor_y += lh + 2
            return
        size -= 1

    font = _font(min_size)
    _draw_centered(draw, text, y, band_height, font)


def _format_countdown(seconds_left: int) -> str:
    """MM:SS under an hour, otherwise HH:MM."""
    if seconds_left < 0:
        seconds_left = 0
    if seconds_left < 3600:
        minutes = seconds_left // 60
        seconds = seconds_left % 60
        return f"{minutes:02d}:{seconds:02d}"
    hours = seconds_left // 3600
    minutes = (seconds_left % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"


def _draw_wifi_icon(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    size: int = 14,
    fill: int = FILL_ON,
) -> None:
    """Draw a small Wi-Fi icon (three concentric arcs + a dot) at (x, y)."""
    cx = x + size // 2
    cy = y + size - 2
    draw.arc([x, y, x + size, y + size], start=200, end=340, fill=fill)
    draw.arc([x + 3, y + 3, x + size - 3, y + size - 3], start=200, end=340, fill=fill)
    draw.arc([x + 6, y + 6, x + size - 6, y + size - 6], start=200, end=340, fill=fill)
    draw.ellipse([cx - 1, cy - 1, cx + 1, cy + 1], fill=fill)


def _draw_mode_bar(draw: ImageDraw.ImageDraw, state: DisplayState) -> None:
    label = _MODE_LABELS.get(state.mode or "", "?")
    text = f"Mode: {label}"

    text_max_w = WIDTH - 4 - STATUS_ZONE_W
    font = _fit_font(draw, text, text_max_w, MODE_BAR_HEIGHT - 2, start_size=18, min_size=10)

    tw, th = _text_size(draw, text, font)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_area_w = WIDTH - STATUS_ZONE_W
    x = (text_area_w - tw) // 2 - bbox[0]
    ty = (MODE_BAR_HEIGHT - th) // 2 - bbox[1]
    draw.text((x, ty), text, font=font, fill=FILL_ON)

    if state.wifi_ap_active:
        icon_size = min(STATUS_ZONE_W - 2, MODE_BAR_HEIGHT - 4)
        ix = WIDTH - STATUS_ZONE_W + (STATUS_ZONE_W - icon_size) // 2
        iy = (MODE_BAR_HEIGHT - icon_size) // 2
        _draw_wifi_icon(draw, ix, iy, size=icon_size)

    draw.line([(0, MODE_BAR_HEIGHT - 1), (WIDTH - 1, MODE_BAR_HEIGHT - 1)], fill=FILL_ON)


def _render_running(draw: ImageDraw.ImageDraw, state: DisplayState) -> None:
    """Layout shared by auto & semi_auto when a sequence is running."""
    relay_id = (state.opened_relay or 0) + 1
    label = f"Relai: {relay_id}"
    label_font = _fit_font(
        draw, label, WIDTH - 4, BAND_20 - 2, start_size=20, min_size=10
    )
    _draw_centered(draw, label, BODY_TOP, BAND_20, label_font)

    if state.should_close_at is not None:
        seconds_left = int(state.should_close_at - state.now.timestamp())
    else:
        seconds_left = 0
    countdown = _format_countdown(seconds_left)
    cd_top = BODY_TOP + BAND_20
    cd_height = BAND_60
    cd_font = _fit_font(
        draw, countdown, WIDTH - 4, cd_height - 4, start_size=48, min_size=18
    )
    _draw_centered(draw, countdown, cd_top, cd_height, cd_font)


def _render_auto_idle_planned(draw: ImageDraw.ImageDraw, state: DisplayState) -> None:
    next_dt = state.next_sequence
    assert next_dt is not None

    label_font = _fit_font(
        draw, "prochain démarrage", WIDTH - 4, BAND_20 - 2,
        start_size=16, min_size=9,
    )
    _draw_centered(draw, "prochain démarrage", BODY_TOP, BAND_20, label_font)

    date_str = next_dt.strftime("%d/%m/%Y")
    date_top = BODY_TOP + BAND_20
    date_font = _fit_font(
        draw, date_str, WIDTH - 4, BAND_40 - 4, start_size=28, min_size=14
    )
    _draw_centered(draw, date_str, date_top, BAND_40, date_font)

    time_str = next_dt.strftime("%H:%M")
    time_top = date_top + BAND_40
    time_height = HEIGHT - time_top
    time_font = _fit_font(
        draw, time_str, WIDTH - 4, time_height - 2, start_size=20, min_size=12
    )
    _draw_centered(draw, time_str, time_top, time_height, time_font)


def _render_auto_idle_no_plan(draw: ImageDraw.ImageDraw) -> None:
    _draw_wrapped_centered(
        draw,
        "pas de démarrage planifié",
        BODY_TOP,
        BODY_HEIGHT,
        WIDTH - 4,
        start_size=22,
        min_size=10,
    )


def _render_semi_auto_idle(draw: ImageDraw.ImageDraw) -> None:
    _draw_wrapped_centered(
        draw,
        "Séquence non démarrée",
        BODY_TOP,
        BODY_HEIGHT,
        WIDTH - 4,
        start_size=22,
        min_size=10,
    )


def _render_manual(draw: ImageDraw.ImageDraw, state: DisplayState) -> None:
    if state.opened_relay is None:
        return
    label = "Relai actif"
    label_font = _fit_font(
        draw, label, WIDTH - 4, BAND_20 - 2, start_size=18, min_size=10
    )
    _draw_centered(draw, label, BODY_TOP, BAND_20, label_font)

    relay_id = state.opened_relay + 1
    relay_text = str(relay_id)
    relay_top = BODY_TOP + BAND_20
    relay_height = HEIGHT - relay_top
    relay_font = _fit_font(
        draw, relay_text, WIDTH - 4, relay_height - 4, start_size=72, min_size=24
    )
    _draw_centered(draw, relay_text, relay_top, relay_height, relay_font)


def _render_pause(draw: ImageDraw.ImageDraw) -> None:
    _draw_wrapped_centered(
        draw,
        "Pause",
        BODY_TOP,
        BODY_HEIGHT,
        WIDTH - 4,
        start_size=48,
        min_size=16,
    )


def render(state: DisplayState) -> Image.Image:
    """Render a DisplayState into a 128x128 1-bit PIL image."""
    image = Image.new("1", (WIDTH, HEIGHT), FILL_OFF)
    draw = ImageDraw.Draw(image)

    _draw_mode_bar(draw, state)

    mode = state.mode
    if mode == MODE_PAUSE:
        _render_pause(draw)
    elif mode == MODE_AUTO:
        if state.running:
            _render_running(draw, state)
        elif state.next_sequence is not None:
            _render_auto_idle_planned(draw, state)
        else:
            _render_auto_idle_no_plan(draw)
    elif mode == MODE_SEMI_AUTO:
        if state.running:
            _render_running(draw, state)
        else:
            _render_semi_auto_idle(draw)
    elif mode == MODE_MANUAL:
        _render_manual(draw, state)

    return image
