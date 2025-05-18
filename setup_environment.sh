#!/bin/bash
# Sample Buddy AI - Setup Environment Script
# This script sets up the virtual environment and installs all dependencies

# Exit on error
set -e

# Print commands
set -x

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
  echo "Detected macOS"
  OS_TYPE="mac"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  echo "Detected Linux"
  OS_TYPE="linux"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
  echo "Detected Windows"
  OS_TYPE="windows"
else
  echo "Unknown OS: $OSTYPE"
  OS_TYPE="unknown"
fi

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Create log directory
mkdir -p logs

# Log file
LOG_FILE="logs/setup_$(date +"%Y%m%d_%H%M%S").log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo -e "${GREEN}=== Sample Buddy AI - Environment Setup ===${NC}"
echo -e "${YELLOW}Setting up environment. This may take a few minutes.${NC}"
echo "OS Type: $OS_TYPE"
echo "Log file: $LOG_FILE"

# Check Python version
echo -e "${GREEN}Checking Python version...${NC}"
if command -v python3.11 &> /dev/null; then
  PYTHON_CMD=python3.11
  echo "Python 3.11 found at: $(which python3.11)"
elif command -v python3 &> /dev/null; then
  PYTHON_CMD=python3
  echo "Python 3 found at: $(which python3)"
elif command -v python &> /dev/null; then
  PYTHON_CMD=python
  echo "Python found at: $(which python)"
else
  echo -e "${RED}Python not found. Please install Python 3.11 or later.${NC}"
  exit 1
fi

$PYTHON_CMD --version

# Create and activate virtual environment
echo -e "${GREEN}Setting up Python virtual environment...${NC}"
if [ -d "venv" ]; then
  echo "Virtual environment already exists"
else
  $PYTHON_CMD -m venv venv
  echo "Virtual environment created"
fi

# Activate virtual environment
if [ "$OS_TYPE" = "windows" ]; then
  source venv/Scripts/activate
else
  source venv/bin/activate
fi

echo "Virtual environment activated: $VIRTUAL_ENV"

# Upgrade pip
echo -e "${GREEN}Upgrading pip...${NC}"
python -m pip install --upgrade pip

# Install Python dependencies
echo -e "${GREEN}Installing Python dependencies...${NC}"
python -m pip install -r electron-audio-manager/requirements.txt

# Install Node.js dependencies
echo -e "${GREEN}Installing Node.js dependencies...${NC}"
if command -v npm &> /dev/null; then
  cd electron-audio-manager
  npm install
  cd ..
else
  echo -e "${RED}npm not found. Please install Node.js and npm.${NC}"
  exit 1
fi

echo -e "${GREEN}Environment setup complete!${NC}"
echo -e "${YELLOW}To activate the environment in the future, run:${NC}"
echo "source venv/bin/activate  # On Linux/macOS"
echo "venv\\Scripts\\activate     # On Windows"
echo ""
echo -e "${YELLOW}To run the Electron app with debugging:${NC}"
echo "cd electron-audio-manager"
echo "DEBUG=electron* ./node_modules/.bin/electron ."
echo ""
echo -e "${GREEN}===== Setup Complete =====${NC}"