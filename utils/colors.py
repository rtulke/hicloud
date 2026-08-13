#!/usr/bin/env python3
"""Shared ANSI color helpers for hicloud console output."""

from typing import Tuple

ANSI_RESET = "\033[0m"


def rgb_to_ansi(rgb: Tuple[int, int, int]) -> str:
    """Return a 24-bit ANSI color escape sequence from an RGB tuple."""
    r, g, b = rgb
    return f"\033[38;2;{r};{g};{b}m"


# Core color palette
PROMPT_TEXT_RGB = (80, 80, 120)
PROMPT_ARROW_RGB = (64, 64, 64)
TABLE_HEADER_RGB = (243, 200, 107)
#TABLE_ROW_RGB = (242, 236, 228)
TABLE_ROW_RGB = (232, 220, 196)

# Semantic colors — the single source for all console output styling.
# Highlight matches the table header accent so info views and tables
# share one look; status colors stay in the same warm palette.
HIGHLIGHT_RGB = TABLE_HEADER_RGB
STATUS_OK_RGB = (140, 200, 120)
STATUS_ERROR_RGB = (220, 110, 100)
STATUS_WARN_RGB = (243, 200, 107)
HINT_RGB = (128, 128, 128)

PROMPT_TEXT_COLOR = rgb_to_ansi(PROMPT_TEXT_RGB)
PROMPT_ARROW_COLOR = rgb_to_ansi(PROMPT_ARROW_RGB)
TABLE_HEADER_COLOR = rgb_to_ansi(TABLE_HEADER_RGB)
TABLE_ROW_COLOR = rgb_to_ansi(TABLE_ROW_RGB)
HIGHLIGHT_COLOR = rgb_to_ansi(HIGHLIGHT_RGB)
STATUS_OK_COLOR = rgb_to_ansi(STATUS_OK_RGB)
STATUS_ERROR_COLOR = rgb_to_ansi(STATUS_ERROR_RGB)
STATUS_WARN_COLOR = rgb_to_ansi(STATUS_WARN_RGB)
HINT_COLOR = rgb_to_ansi(HINT_RGB)
