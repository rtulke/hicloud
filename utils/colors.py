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

PROMPT_TEXT_COLOR = rgb_to_ansi(PROMPT_TEXT_RGB)
PROMPT_ARROW_COLOR = rgb_to_ansi(PROMPT_ARROW_RGB)
TABLE_HEADER_COLOR = rgb_to_ansi(TABLE_HEADER_RGB)
TABLE_ROW_COLOR = rgb_to_ansi(TABLE_ROW_RGB)
