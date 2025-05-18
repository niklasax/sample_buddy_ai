#!/bin/bash
# Sample Buddy AI - Startup Script
# This script activates the virtual environment and starts the application

# Exit on error
set -e

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Sample Buddy AI - Startup ===${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
  echo -e "${RED}Virtual environment not found.${NC}"
  echo -e "${YELLOW}Please run setup_environment.sh first.${NC}"
  exit 1
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

echo -e "${GREEN}Virtual environment activated: $VIRTUAL_ENV${NC}"

# Navigate to electron-audio-manager directory
cd electron-audio-manager

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
  echo -e "${RED}Node modules not found.${NC}"
  echo -e "${YELLOW}Installing Node.js dependencies...${NC}"
  npm install
fi

# Start the application with debugging enabled
echo -e "${GREEN}Starting Sample Buddy AI...${NC}"
echo -e "${YELLOW}Debug logs will be available in the application menu.${NC}"
DEBUG=electron* ./node_modules/.bin/electron .

# If we get here, the application has exited
echo -e "${GREEN}Sample Buddy AI has exited.${NC}"