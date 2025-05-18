#!/bin/bash

# Setup script for Linux/macOS
echo "Setting up Sample Buddy AI environment..."

# Check Python version
if ! command -v python &> /dev/null; then
    echo "Error: Python is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [[ $PYTHON_MAJOR -lt 3 || ($PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 8) ]]; then
    echo "Error: Python version must be 3.8 or higher. Your version: $PYTHON_VERSION"
    exit 1
fi

# Check Node.js version
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed. Please install Node.js 14 or higher."
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2)
NODE_MAJOR=$(echo $NODE_VERSION | cut -d. -f1)

if [[ $NODE_MAJOR -lt 14 ]]; then
    echo "Error: Node.js version must be 14 or higher. Your version: $NODE_VERSION"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python -m venv venv
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create Python virtual environment."
        exit 1
    fi
else
    echo "Virtual environment already exists."
fi

# Activate virtual environment
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "Error: Failed to activate virtual environment."
    exit 1
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install Python dependencies."
    exit 1
fi

# Install Node.js dependencies
echo "Installing Node.js dependencies..."
npm install
if [ $? -ne 0 ]; then
    echo "Error: Failed to install Node.js dependencies."
    exit 1
fi

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p processed_samples

echo "Setup complete! Run ./start.sh to launch the application."