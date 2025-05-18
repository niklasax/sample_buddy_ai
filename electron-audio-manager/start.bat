@echo off

:: Check if the virtual environment exists
if not exist venv (
    echo Virtual environment not found! Please run setup.bat first.
    pause
    exit 1
)

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Start the Electron application
echo Starting Sample Buddy AI...
npm start