#!/bin/bash

# Start script for Linux/macOS

# Check if the virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found! Please run setup.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Start the Electron application
echo "Starting Sample Buddy AI..."
# Use the local node_modules/.bin/electron instead of relying on global electron
if [ -f "./node_modules/.bin/electron" ]; then
    ./node_modules/.bin/electron .
else
    # Try with npx as fallback
    npx electron .
fi