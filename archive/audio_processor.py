import os
import logging
import librosa
import numpy as np
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple

def process_audio_folder(folder_path: str) -> Dict[str, Dict]:
    """
    Process a folder of audio files and return a dictionary of sample metadata.
    
    Args:
        folder_path: Path to folder containing audio files
        
    Returns:
        Dictionary of audio samples with ID as key
    """
    logging.info(f"Processing audio folder: {folder_path}")
    
    samples = {}
    
    # Get all audio files in the folder
    for root, _, files in os.walk(folder_path):
        for file in files:
            # Check if file is an audio file
            if file.lower().endswith(('.wav', '.mp3', '.ogg', '.flac', '.aif', '.aiff')):
                file_path = os.path.join(root, file)
                
                try:
                    # Generate a unique ID for the sample
                    sample_id = generate_sample_id(file_path)
                    
                    # Get basic sample information
                    sample_info = {
                        'id': sample_id,
                        'name': os.path.basename(file_path),
                        'path': file_path
                    }
                    
                    samples[sample_id] = sample_info
                    
                except Exception as e:
                    logging.error(f"Error processing {file_path}: {str(e)}")
    
    logging.info(f"Found {len(samples)} audio samples")
    return samples

def get_sample_details(file_path: str) -> Tuple[float, float]:
    """
    Get basic details of an audio sample.
    
    Args:
        file_path: Path to audio file
        
    Returns:
        Tuple of (duration, sample_rate)
    """
    try:
        y, sr = librosa.load(file_path, sr=None, duration=10)  # Load first 10 seconds to get info
        duration = librosa.get_duration(y=y, sr=sr)
        return duration, sr
    except Exception as e:
        logging.error(f"Error getting sample details for {file_path}: {str(e)}")
        return 0.0, 0.0

def generate_sample_id(file_path: str) -> str:
    """
    Generate a unique ID for a sample based on its file path and modification time.
    
    Args:
        file_path: Path to audio file
        
    Returns:
        Unique ID for the sample
    """
    file_info = f"{file_path}_{os.path.getmtime(file_path)}"
    return hashlib.md5(file_info.encode()).hexdigest()

def load_audio(file_path: str, sr: int = 22050, mono: bool = True) -> Tuple[np.ndarray, int]:
    """
    Load audio file using librosa.
    
    Args:
        file_path: Path to audio file
        sr: Sample rate to resample audio (default: 22050 Hz)
        mono: Whether to convert audio to mono (default: True)
        
    Returns:
        Tuple of (audio_data, sample_rate)
    """
    try:
        y, sr = librosa.load(file_path, sr=sr, mono=mono)
        return y, sr
    except Exception as e:
        logging.error(f"Error loading audio {file_path}: {str(e)}")
        return np.array([]), sr
