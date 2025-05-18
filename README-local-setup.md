# Sample Buddy AI - Local Setup Guide

This guide helps you set up Sample Buddy AI locally on macOS or Linux.

## Prerequisites

- Python 3.11 or newer
- Node.js 14 or newer
- npm or yarn

## Setup Instructions

1. **Set up the environment**

   Run the setup script to create a Python virtual environment and install all dependencies:

   ```bash
   ./setup_environment.sh
   ```

   This script will:
   - Create a Python virtual environment in the `venv` directory
   - Install all required Python packages
   - Install Node.js dependencies

2. **Start the application**

   Once setup is complete, you can start the application with:

   ```bash
   ./start_buddy.sh
   ```

   This launches the Electron app with debugging enabled.

## Troubleshooting

If you encounter issues with NumPy or other Python dependencies:

1. Start the application using `./start_buddy.sh`
2. In the app, click on `Debug` in the menu bar
3. Select `Install Python Dependencies`
4. Restart the application

## Logs and Debugging

- Application logs are saved in your user data directory
- Access logs via Debug → View Logs in the application menu
- JavaScript errors appear in the DevTools console (automatically opened)
- Python errors are logged to the application logs

## Manual Activation (if needed)

If you need to manually activate the virtual environment:

```bash
source venv/bin/activate
```

## Running with Manual Debug Options

For advanced debugging:

```bash
source venv/bin/activate
cd electron-audio-manager
DEBUG=electron* ./node_modules/.bin/electron .
```