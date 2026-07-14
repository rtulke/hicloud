#!/usr/bin/env python3
# utils/prompts.py - Shared interactive prompt helpers
#
# Convention (see CLAUDE.md): on invalid input re-prompt in a loop;
# plain Enter selects the default. Never silently substitute a default
# for invalid input.

from typing import List, Optional


def prompt_choice(prompt: str, choices: List[str], default: Optional[str] = None) -> str:
    """Ask until the user enters one of `choices`; Enter returns the default if set."""
    while True:
        value = input(prompt).strip().lower()
        if not value and default is not None:
            return default
        if value in choices:
            return value
        print(f"Invalid input. Choose one of: {', '.join(choices)}")


def prompt_int(prompt: str, default: Optional[int] = None,
               min_value: Optional[int] = None, max_value: Optional[int] = None) -> int:
    """Ask until the user enters a valid integer in range; Enter returns the default if set."""
    while True:
        raw = input(prompt).strip()
        if not raw and default is not None:
            return default
        try:
            value = int(raw)
        except ValueError:
            print("Invalid input. Must be an integer.")
            continue
        if min_value is not None and value < min_value:
            print(f"Value must be at least {min_value}.")
            continue
        if max_value is not None and value > max_value:
            print(f"Value must be at most {max_value}.")
            continue
        return value
