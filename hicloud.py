#!/usr/bin/env python3
# hicloud.py - Hetzner Cloud CLI Tool
# License: GPLv3

import os
import sys
import argparse

from lib.api import HetznerCloudManager
from lib.config import ConfigManager
from lib.console import InteractiveConsole
from utils.constants import DEFAULT_CONFIG_PATH, HISTORY_DIR, VERSION


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Hetzner Cloud CLI Tool")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--gen-config", help="Generate a sample configuration file")
    parser.add_argument("--project", help="Project to use from config file", default="default")
    parser.add_argument("--token", help="API token (overrides config file)")
    parser.add_argument("--version", action="version", version=f"hicloud v{VERSION}")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")

    args = parser.parse_args()

    # Ensure history directory exists
    if not os.path.exists(HISTORY_DIR):
        try:
            os.makedirs(HISTORY_DIR, exist_ok=True)
        except Exception as e:
            print(f"Warning: Could not create history directory: {str(e)}")

    # Handle config generation
    if args.gen_config:
        ConfigManager.generate_config(args.gen_config)
        return 0

    # Load configuration
    config_path = args.config if args.config else DEFAULT_CONFIG_PATH
    config = {}

    if os.path.exists(config_path):
        config = ConfigManager.load_config(config_path)

    # Get API token
    api_token = None
    project_name = "default"

    if args.token:
        api_token = args.token
    elif args.project in config:
        api_token = config[args.project].get("api_token")
        project_name = config[args.project].get("project_name", args.project)
    elif "default" in config:
        api_token = config["default"].get("api_token")
        project_name = config["default"].get("project_name", "default")

    if not api_token:
        if not os.path.exists(config_path):
            print(f"No configuration file found at {config_path}")
            print(f"Generate one with: hicloud.py --gen-config {config_path}")
            print("Or provide an API token: hicloud.py --token YOUR_API_TOKEN")
        else:
            print(f"No API token found for project '{args.project}'")
        return 1

    # Create Hetzner Cloud manager
    hetzner = HetznerCloudManager(api_token, project_name, debug=args.debug)

    # Start interactive console
    console = InteractiveConsole(hetzner, debug=args.debug)
    console.start()

    return 0


if __name__ == "__main__":
    sys.exit(main())
