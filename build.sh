#!/bin/bash
# Build script for Linux

set -e

echo "==================================="
echo "Napoleon TW Cheat Engine - Linux Build"
echo "==================================="

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run tests
echo "Running tests..."
python -m pytest tests/ -v || true

# Build with PyInstaller
echo "Building executable..."
pyinstaller --onefile --windowed --name "NapoleonCheatEngine" src/main.py

# Create AppImage (optional)
echo "Build complete!"
echo ""
echo "Executable: dist/NapoleonCheatEngine"
echo ""
echo "To run: ./dist/NapoleonCheatEngine --gui"
