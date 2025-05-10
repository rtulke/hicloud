#!/usr/bin/env python3
# utils/constants.py - Global constants for hicloud

import os

# Constants
DEFAULT_CONFIG_PATH = os.path.expanduser("~/.hicloud.toml")
HISTORY_DIR = os.path.expanduser("~/.tmp/hicloud")
HISTORY_FILE = os.path.join(HISTORY_DIR, "history")
HISTORY_MAX_LINES = 1000
API_BASE_URL = "https://api.hetzner.cloud/v1"
VERSION = "1.0.0"
