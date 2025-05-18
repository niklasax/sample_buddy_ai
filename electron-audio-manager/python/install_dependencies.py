#!/usr/bin/env python
"""
Dependency installer for Sample Buddy AI
This script will install required Python packages
"""

import sys
import subprocess
import os
import platform

def install_packages():
    """Install required packages using pip"""
    print("Starting dependency installation process...")
    print(f"Python version: {platform.python_version()}")
    print(f"Python path: {sys.executable}")
    
    # Find requirements.txt
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    requirements_path = os.path.join(parent_dir, "requirements.txt")
    
    if not os.path.exists(requirements_path):
        print(f"Error: requirements.txt not found at {requirements_path}")
        
        # Fallback to list of required packages
        packages = [
            "numpy", 
            "librosa>=0.10.0",  # Specify minimum version 
            "soundfile", 
            "scipy", 
            "matplotlib", 
            "scikit-learn"
        ]
        
        # Install each package
        for package in packages:
            print(f"Installing {package}...")
            try:
                # Use the same Python executable that's running this script
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print(f"Successfully installed {package}")
            except subprocess.CalledProcessError as e:
                print(f"Error installing {package}: {e}")
                return False
    else:
        print(f"Found requirements.txt at {requirements_path}")
        try:
            # Install all requirements at once
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_path])
            print("Successfully installed all requirements")
        except subprocess.CalledProcessError as e:
            print(f"Error installing requirements: {e}")
            return False
    
    print("All dependencies installed successfully!")
    
    # List of packages to verify
    packages_to_verify = [
        "numpy", 
        "librosa", 
        "scipy", 
        "matplotlib", 
        "sklearn"  # scikit-learn is imported as sklearn
    ]
    
    # Verify installations
    print("\nVerifying installations:")
    for package in packages_to_verify:
        try:
            __import__(package.replace("-", "_"))  # replace dash with underscore for import
            print(f"✓ {package} is installed and importable")
        except ImportError:
            print(f"✗ {package} could not be imported")
    
    return True

if __name__ == "__main__":
    success = install_packages()
    sys.exit(0 if success else 1)