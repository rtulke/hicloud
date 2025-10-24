#!/bin/bash
# Activation script for hicloud Virtual Environment

echo "================================================="
echo "  hicloud Virtual Environment Activation"
echo "================================================="
echo ""

# Check if .venv exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Please run 'python3 -m venv .venv' first"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

echo "✓ Virtual environment activated"
echo ""
echo "Python: $(which python3)"
echo "Version: $(python3 --version)"
echo ""
echo "Installed packages:"
pip list --format=columns | grep -E "(requests|toml|certifi|urllib3)"
echo ""
echo "================================================="
echo "  hicloud is ready!"
echo "================================================="
echo ""
echo "Usage:"
echo "  ./hicloud.py --help              # Show help"
echo "  ./hicloud.py --gen-config config # Generate configuration"
echo "  ./hicloud.py                     # Start interactive console"
echo ""
echo "To deactivate: type 'deactivate'"
echo ""
