@echo off
REM Sample Buddy AI - Setup Environment Script for Windows
REM This script sets up the virtual environment and installs all dependencies

echo === Sample Buddy AI - Environment Setup ===
echo Setting up environment. This may take a few minutes.

REM Create log directory
if not exist logs mkdir logs

REM Set log file
set TIMESTAMP=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set LOG_FILE=logs\setup_%TIMESTAMP%.log

echo Log file: %LOG_FILE%

REM Redirect output to log file
echo === Sample Buddy AI - Environment Setup === > %LOG_FILE%
echo Setting up environment. This may take a few minutes. >> %LOG_FILE%

REM Check Python version
echo Checking Python version...
echo Checking Python version... >> %LOG_FILE%

where python3.11 >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set PYTHON_CMD=python3.11
    echo Python 3.11 found >> %LOG_FILE%
) else (
    where python >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set PYTHON_CMD=python
        echo Python found >> %LOG_FILE%
    ) else (
        echo Python not found. Please install Python 3.11 or later.
        echo Python not found. Please install Python 3.11 or later. >> %LOG_FILE%
        exit /b 1
    )
)

%PYTHON_CMD% --version >> %LOG_FILE%

REM Create and activate virtual environment
echo Setting up Python virtual environment...
echo Setting up Python virtual environment... >> %LOG_FILE%

if exist venv (
    echo Virtual environment already exists >> %LOG_FILE%
) else (
    %PYTHON_CMD% -m venv venv
    echo Virtual environment created >> %LOG_FILE%
)

REM Activate virtual environment
call venv\Scripts\activate
echo Virtual environment activated: %VIRTUAL_ENV% >> %LOG_FILE%

REM Upgrade pip
echo Upgrading pip...
echo Upgrading pip... >> %LOG_FILE%
python -m pip install --upgrade pip >> %LOG_FILE% 2>&1

REM Install Python dependencies
echo Installing Python dependencies...
echo Installing Python dependencies... >> %LOG_FILE%
python -m pip install -r electron-audio-manager\requirements.txt >> %LOG_FILE% 2>&1

REM Install Node.js dependencies
echo Installing Node.js dependencies...
echo Installing Node.js dependencies... >> %LOG_FILE%
where npm >nul 2>&1
if %ERRORLEVEL% equ 0 (
    cd electron-audio-manager
    npm install >> ..\%LOG_FILE% 2>&1
    cd ..
) else (
    echo npm not found. Please install Node.js and npm.
    echo npm not found. Please install Node.js and npm. >> %LOG_FILE%
    exit /b 1
)

echo Environment setup complete!
echo Environment setup complete! >> %LOG_FILE%
echo.
echo To activate the environment in the future, run:
echo venv\Scripts\activate
echo.
echo To run the Electron app with debugging:
echo cd electron-audio-manager
echo set DEBUG=electron* && .\node_modules\.bin\electron .
echo.
echo ===== Setup Complete =====

pause