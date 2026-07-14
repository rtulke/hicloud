#!/usr/bin/env python3
# utils/constants.py - Global constants for hicloud

import os

# Constants
DEFAULT_CONFIG_PATH = os.path.expanduser("~/.hicloud.toml")
HISTORY_DIR = os.path.expanduser("~/.tmp/hicloud")
HISTORY_FILE = os.path.join(HISTORY_DIR, "history")
HISTORY_MAX_LINES = 1000
API_BASE_URL = "https://api.hetzner.cloud/v1"
REQUEST_TIMEOUT = 30  # seconds; the API normally answers in <2s, but never let the REPL hang forever
VERSION = "1.2.0"
