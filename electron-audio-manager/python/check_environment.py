#!/usr/bin/env python
"""
Environment checker for Sample Buddy AI
This script verifies Python environment setup and dependencies
"""

import sys
import os
import platform
import subprocess
import json

def check_environment():
    """Check Python environment and dependencies"""
    result = {
        "python_version": platform.python_version(),
        "python_path": sys.executable,
        "platform": platform.platform(),
        "dependencies": {}
    }
    
    # Required dependencies for audio processing
    required_packages = [
        "numpy", "librosa", "soundfile", "scipy", "matplotlib",
        "sklearn", "tensorflow", "torch"
    ]
    
    # Check each package
    for package in required_packages:
        try:
            # Attempt to import the package
            __import__(package)
            result["dependencies"][package] = "Installed"
        except ImportError:
            result["dependencies"][package] = "Missing"
    
    # Check for audio libraries
    audio_libs = {}
    
    # Check for ffmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE, 
                      check=False,
                      timeout=2)
        audio_libs["ffmpeg"] = "Installed"
    except (subprocess.SubprocessError, FileNotFoundError):
        audio_libs["ffmpeg"] = "Missing or not in PATH"
    
    # Add audio libraries check to result
    result["audio_libraries"] = audio_libs
    
    return result

if __name__ == "__main__":
    env_check = check_environment()
    print(json.dumps(env_check, indent=2))