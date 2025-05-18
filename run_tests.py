#!/usr/bin/env python3
"""
Test runner for Sample Buddy AI.

Usage:
    python run_tests.py                   # Run all tests
    python run_tests.py basic             # Run basic functionality tests
    python run_tests.py web               # Run web app tests
    python run_tests.py similarity        # Run similarity search tests
"""

import os
import sys
import unittest

def discover_and_run_tests(pattern=None):
    """Discover and run tests matching the specified pattern."""
    if pattern:
        pattern = f"test_{pattern}*.py"
    
    loader = unittest.TestLoader()
    
    if pattern:
        suite = loader.discover('tests', pattern=pattern)
    else:
        suite = loader.discover('tests')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def print_test_help():
    """Print help information for the test runner."""
    print("Sample Buddy AI Test Runner")
    print("==========================")
    print("Usage:")
    print("  python run_tests.py                   # Run all tests")
    print("  python run_tests.py basic             # Run basic functionality tests")
    print("  python run_tests.py web               # Run web app tests")
    print("  python run_tests.py similarity        # Run similarity search tests")
    print("\nAvailable test suites:")
    print("  basic      - Tests for basic classifier functionality")
    print("  web        - Tests for web application routes")
    print("  similarity - Tests for audio similarity search")


def create_test_sample():
    """Create a simple test sample if none exists."""
    test_samples_dir = os.path.join('tests', 'test_samples')
    test_sample_path = os.path.join(test_samples_dir, 'test_kick.wav')
    
    if not os.path.exists(test_samples_dir):
        os.makedirs(test_samples_dir)
    
    if not os.path.exists(test_sample_path):
        print("Creating a basic test sample file...")
        # Create a minimal valid WAV file (44 bytes minimum RIFF header)
        with open(test_sample_path, 'wb') as f:
            # RIFF header
            f.write(b'RIFF')
            f.write((36).to_bytes(4, byteorder='little'))  # File size - 8
            f.write(b'WAVE')
            
            # Format chunk
            f.write(b'fmt ')
            f.write((16).to_bytes(4, byteorder='little'))  # Chunk size
            f.write((1).to_bytes(2, byteorder='little'))   # Format code (1 = PCM)
            f.write((1).to_bytes(2, byteorder='little'))   # Channels
            f.write((44100).to_bytes(4, byteorder='little'))  # Sample rate
            f.write((88200).to_bytes(4, byteorder='little'))  # Bytes per second
            f.write((2).to_bytes(2, byteorder='little'))   # Block align
            f.write((16).to_bytes(2, byteorder='little'))  # Bits per sample
            
            # Data chunk
            f.write(b'data')
            f.write((0).to_bytes(4, byteorder='little'))  # Chunk size


if __name__ == "__main__":
    # Create a test sample file if needed
    create_test_sample()
    
    if len(sys.argv) > 1:
        if sys.argv[1] in ('-h', '--help'):
            print_test_help()
            sys.exit(0)
        
        pattern = sys.argv[1]
        success = discover_and_run_tests(pattern)
    else:
        success = discover_and_run_tests()
    
    sys.exit(0 if success else 1)