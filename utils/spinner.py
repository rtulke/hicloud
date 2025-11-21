#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reusable dots spinner for long-running console operations."""

import itertools
import sys
import threading
import time
from typing import Optional

DOTS_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


class DotsSpinner:
    """Display a non-blocking dots spinner next to a status message."""

    def __init__(self, message: str, interval: float = 0.1):
        self.message = message.rstrip()
        self.interval = interval
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._current_frame = DOTS_FRAMES[0]
        self._last_output_len = 0
        self._stopped = False

    def start(self) -> "DotsSpinner":
        """Start the spinner animation thread."""
        if self._thread is None:
            self._thread = threading.Thread(target=self._spin, daemon=True)
            self._thread.start()
        return self

    def _spin(self) -> None:
        cycle = itertools.cycle(DOTS_FRAMES)
        wrote_once = False
        for frame in cycle:
            if self._stop_event.is_set():
                break
            self._current_frame = frame
            output = f"{self.message} {frame}"
            prefix = "\r" if wrote_once else ""
            self._last_output_len = len(output)
            sys.stdout.write(f"{prefix}{output}")
            sys.stdout.flush()
            wrote_once = True
            if self._stop_event.wait(self.interval):
                break

    def stop(self, success: bool = True) -> None:
        """Stop the spinner and print a final status message."""
        if self._stopped:
            return

        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join()

        status_text = "done." if success else "failed."
        final_output = f"{self.message} {self._current_frame}: {status_text}"
        padding = " " * max(self._last_output_len - len(final_output), 0)
        sys.stdout.write(f"\r{final_output}{padding}\n")
        sys.stdout.flush()
        self._stopped = True

    def __enter__(self) -> "DotsSpinner":
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        success = exc_type is None
        self.stop(success=success)
