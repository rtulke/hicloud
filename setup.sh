#!/bin/bash
# Bootstrap and activation script for the hicloud virtual environment.
#
# Usage: source setup.sh
#
# Creates the virtual environment if missing, installs dependencies,
# generates the configuration file on first run, and activates the
# environment. Safe to run repeatedly.

# When executed instead of sourced, the activation would not persist in the
# calling shell. (BASH_SOURCE is unset in zsh, where sourcing is the only
# way this file runs with this guard intact.)
if [ -n "$BASH_SOURCE" ] && [ "${BASH_SOURCE[0]}" = "$0" ]; then
    echo "ERROR: This script must be sourced so the activation persists:"
    echo "   source setup.sh"
    exit 1
fi

echo "================================================="
echo "  hicloud Environment Setup"
echo "================================================="
echo ""

# Find an existing virtual environment (.venv preferred, venv/ supported)
VENV_DIR=""
if [ -d ".venv" ]; then
    VENV_DIR=".venv"
elif [ -d "venv" ]; then
    VENV_DIR="venv"
fi

# Create one if none exists
if [ -z "$VENV_DIR" ]; then
    echo "No virtual environment found - creating .venv ..."
    if ! python3 -m venv .venv; then
        echo "ERROR: Could not create the virtual environment."
        return 1
    fi
    VENV_DIR=".venv"
fi

# Activate it
source "$VENV_DIR/bin/activate"
echo "OK: Virtual environment activated ($VENV_DIR)"

# Install or refresh runtime dependencies (no-op when already satisfied)
echo "Checking dependencies ..."
if ! pip install -q -r requirements.txt; then
    echo "ERROR: Installing dependencies failed."
    return 1
fi
echo "OK: Dependencies installed"

# Generate the configuration file on first run (sets 600 permissions itself)
CONFIG_FILE="$HOME/.hicloud.toml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo ""
    echo "No configuration found - generating $CONFIG_FILE ..."
    python hicloud.py --gen-config "$CONFIG_FILE"
    echo ""
    echo "IMPORTANT: Edit $CONFIG_FILE and replace the placeholder API tokens."
else
    echo "OK: Configuration found at $CONFIG_FILE"
fi

echo ""
echo "Python:  $(which python3)"
echo "Version: $(python3 --version)"
echo ""
echo "================================================="
echo "  hicloud is ready!"
echo "================================================="
echo ""
echo "Usage:"
echo "  python hicloud.py --help         # Show help"
echo "  python hicloud.py                # Start interactive console"
echo ""
echo "To deactivate: type 'deactivate'"
echo ""
