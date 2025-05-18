@echo off
echo Setting up Sample Buddy AI environment...

:: Check Python version
python --version 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python is not installed or not in PATH. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

:: Check Python version meets minimum requirements
for /f "tokens=2" %%I in ('python --version 2^>^&1') do set PYVER=%%I
set PYVER=%PYVER:~0,3%
if "%PYVER%" LSS "3.8" (
    echo Error: Python version must be 3.8 or higher. Your version: %PYVER%
    pause
    exit /b 1
)

:: Check Node.js version
node --version 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo Error: Node.js is not installed or not in PATH. Please install Node.js 14 or higher.
    pause
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist venv (
    echo Creating Python virtual environment...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo Error: Failed to create Python virtual environment.
        pause
        exit /b 1
    )
) else (
    echo Virtual environment already exists.
)

:: Activate virtual environment
call venv\Scripts\activate.bat
if %ERRORLEVEL% NEQ 0 (
    echo Error: Failed to activate virtual environment.
    pause
    exit /b 1
)

:: Install Python dependencies
echo Installing Python dependencies...
pip install --upgrade pip
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo Error: Failed to install Python dependencies.
    pause
    exit /b 1
)

:: Install Node.js dependencies
echo Installing Node.js dependencies...
npm install
if %ERRORLEVEL% NEQ 0 (
    echo Error: Failed to install Node.js dependencies.
    pause
    exit /b 1
)

:: Create necessary directories
echo Creating necessary directories...
if not exist processed_samples mkdir processed_samples

echo.
echo Setup complete! Run start.bat to launch the application.
pause