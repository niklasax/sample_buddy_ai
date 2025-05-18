#!/usr/bin/env python3
"""
Sample copying utility for Sample Buddy AI

This script helps create a set of sample audio files for testing the application
by copying them from another location or generating simple test tones.
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
import random

# Variables that will be set if imports are available
np = None
wavfile = None
GENERATE_AVAILABLE = False

# Try to import optional dependencies
try:
    import numpy as np_module
    from scipy.io import wavfile as wavfile_module
    
    # If imports succeed, set the module variables
    np = np_module
    wavfile = wavfile_module
    GENERATE_AVAILABLE = True
except ImportError:
    # These imports are optional and only needed for tone generation
    pass

# Sample types and example filenames
SAMPLE_TYPES = {
    "drums": ["kick", "snare", "hihat", "tom", "crash", "percussion", "loop", "drum"],
    "synth": ["bass", "lead", "pad", "arp", "synth", "synthetic"],
    "vocal": ["vocal", "voice", "acapella", "chorus", "verse", "vox"],
    "fx": ["riser", "downlifter", "impact", "whoosh", "transition", "fx", "effect"],
    "instrument": ["guitar", "piano", "strings", "brass", "wind", "acoustic"]
}

def find_audio_files(source_dir):
    """Find audio files in the source directory recursively"""
    audio_extensions = [".wav", ".mp3", ".ogg", ".aif", ".aiff", ".flac"]
    files = []
    
    for ext in audio_extensions:
        files.extend(list(Path(source_dir).rglob(f"*{ext}")))
    
    return files

def classify_by_filename(filename):
    """Classify a file by its filename"""
    filename_lower = str(filename).lower()
    
    # Check each type
    for sample_type, keywords in SAMPLE_TYPES.items():
        for keyword in keywords:
            if keyword in filename_lower:
                return sample_type
    
    # Default to "other" if no match found
    return "other"

def copy_sample_files(source_dir, target_dir, max_files=5):
    """Copy sample files from source to target directory"""
    if not os.path.exists(source_dir):
        print(f"Error: Source directory '{source_dir}' does not exist.")
        return False
    
    # Create target directory if it doesn't exist
    os.makedirs(target_dir, exist_ok=True)
    
    # Find audio files
    audio_files = find_audio_files(source_dir)
    if not audio_files:
        print(f"No audio files found in '{source_dir}'")
        return False
    
    # Group by type
    files_by_type = {}
    for file in audio_files:
        sample_type = classify_by_filename(file.name)
        if sample_type not in files_by_type:
            files_by_type[sample_type] = []
        files_by_type[sample_type].append(file)
    
    # Copy files
    copied_count = 0
    for sample_type, files in files_by_type.items():
        # Create type directory
        type_dir = os.path.join(target_dir, sample_type)
        os.makedirs(type_dir, exist_ok=True)
        
        # Copy up to max_files per type
        for file in files[:max_files]:
            target_file = os.path.join(type_dir, file.name)
            shutil.copy2(file, target_file)
            copied_count += 1
            print(f"Copied: {file.name} -> {target_file}")
    
    print(f"Copied {copied_count} sample files to '{target_dir}'")
    return True

def generate_test_tones(target_dir, num_samples=10):
    """Generate test tone samples for testing"""
    if not GENERATE_AVAILABLE:
        print("Error: numpy and scipy are required for generating test tones.")
        print("Please install them with: pip install numpy scipy")
        return False
    
    # Create target directory if it doesn't exist
    os.makedirs(target_dir, exist_ok=True)
    
    # Generate sample types
    sample_types = list(SAMPLE_TYPES.keys())
    
    for i in range(num_samples):
        # Random parameters
        sample_type = random.choice(sample_types)
        duration = random.uniform(0.5, 2.0)  # Duration in seconds
        sample_rate = 44100  # Sample rate in Hz
        frequency = random.uniform(80, 1000)  # Frequency in Hz
        
        # Generate time array
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        
        # Generate signal based on sample type
        if sample_type == "drums":
            # Short percussive sound with decay
            signal = np.sin(2 * np.pi * frequency * t) * np.exp(-5 * t)
        elif sample_type == "synth":
            # Synth with harmonics
            signal = 0.5 * np.sin(2 * np.pi * frequency * t) + 0.3 * np.sin(2 * np.pi * 2 * frequency * t)
            # Apply envelope
            envelope = np.ones_like(t)
            attack = int(0.1 * sample_rate)
            release = int(0.3 * sample_rate)
            envelope[:attack] = np.linspace(0, 1, attack)
            envelope[-release:] = np.linspace(1, 0, release)
            signal = signal * envelope
        elif sample_type == "vocal":
            # Vocal-like with vibrato
            vibrato_rate = 5  # Hz
            vibrato_depth = 10  # Hz
            frequency_mod = frequency + vibrato_depth * np.sin(2 * np.pi * vibrato_rate * t)
            signal = np.sin(2 * np.pi * np.cumsum(frequency_mod) / sample_rate)
        elif sample_type == "fx":
            # Sweeping effect
            frequency_mod = np.linspace(frequency, frequency * 3, len(t))
            signal = np.sin(2 * np.pi * np.cumsum(frequency_mod) / sample_rate)
        else:  # instrument or other
            # Basic tone with harmonics and sustain
            signal = 0.7 * np.sin(2 * np.pi * frequency * t) + 0.2 * np.sin(2 * np.pi * 2 * frequency * t) + 0.1 * np.sin(2 * np.pi * 3 * frequency * t)
        
        # Normalize
        signal = signal / np.max(np.abs(signal))
        
        # Convert to 16-bit PCM
        signal = (signal * 32767).astype(np.int16)
        
        # Create sample name with recognizable keywords for classification
        keywords = SAMPLE_TYPES[sample_type]
        keyword = random.choice(keywords)
        filename = f"test_{sample_type}_{keyword}_{i+1:02d}.wav"
        filepath = os.path.join(target_dir, filename)
        
        # Write WAV file
        wavfile.write(filepath, sample_rate, signal)
        print(f"Generated: {filepath}")
    
    print(f"Generated {num_samples} test tone samples in '{target_dir}'")
    return True

def main():
    parser = argparse.ArgumentParser(description="Sample copying utility for Sample Buddy AI")
    parser.add_argument("--source", help="Source directory containing audio files")
    parser.add_argument("--target", default="sample_data", help="Target directory for samples (default: sample_data)")
    parser.add_argument("--max-files", type=int, default=5, help="Maximum files per type (default: 5)")
    parser.add_argument("--generate", action="store_true", help="Generate test tones instead of copying")
    parser.add_argument("--num-samples", type=int, default=10, help="Number of test samples to generate (default: 10)")
    
    args = parser.parse_args()
    
    # Create absolute path for target directory
    target_dir = os.path.abspath(args.target)
    
    if args.generate:
        success = generate_test_tones(target_dir, args.num_samples)
    elif args.source:
        source_dir = os.path.abspath(args.source)
        success = copy_sample_files(source_dir, target_dir, args.max_files)
    else:
        parser.print_help()
        print("\nError: Either --source or --generate is required")
        return 1
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())