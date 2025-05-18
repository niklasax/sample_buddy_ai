import os
import logging
import librosa
import numpy as np
from typing import Dict, List, Any
from models import AudioFeatures

def extract_audio_features(samples: Dict[str, Dict]) -> Dict[str, Dict]:
    """
    Extract audio features from a dictionary of samples.
    
    Args:
        samples: Dictionary of audio samples with ID as key
        
    Returns:
        Updated dictionary with features added to each sample
    """
    logging.info(f"Extracting features for {len(samples)} samples")
    
    for sample_id, sample in samples.items():
        try:
            file_path = sample['path']
            logging.debug(f"Extracting features for {file_path}")
            
            # Load audio file
            y, sr = librosa.load(file_path, sr=None, mono=True)
            
            # Extract features
            features = extract_features(y, sr)
            
            # Add features to sample
            samples[sample_id]['features'] = features
            
        except Exception as e:
            logging.error(f"Error extracting features for {sample['path']}: {str(e)}")
            samples[sample_id]['features'] = {}
    
    return samples

def extract_features(y: np.ndarray, sr: int) -> Dict[str, Any]:
    """
    Extract audio features from an audio signal.
    
    Args:
        y: Audio signal
        sr: Sample rate
        
    Returns:
        Dictionary of audio features
    """
    # Create AudioFeatures object
    features = AudioFeatures()
    
    # Calculate duration
    features.duration = librosa.get_duration(y=y, sr=sr)
    
    # Extract spectral features
    if len(y) > 0:
        # Spectral centroid
        cent = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        features.spectral_centroid = float(np.mean(cent))
        
        # Spectral bandwidth
        bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
        features.spectral_bandwidth = float(np.mean(bandwidth))
        
        # Spectral rolloff
        rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
        features.spectral_rolloff = float(np.mean(rolloff))
        
        # Zero crossing rate
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        features.zero_crossing_rate = float(np.mean(zcr))
        
        # RMS energy
        rms = librosa.feature.rms(y=y)[0]
        features.rms = float(np.mean(rms))
        features.energy = float(np.mean(rms**2))
        
        # MFCCs
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        features.mfcc = [float(np.mean(mfcc)) for mfcc in mfccs]
        
        # Chroma features
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        features.chroma = [float(np.mean(c)) for c in chroma]
        
        # Tempo
        try:
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            features.tempo = float(tempo)
        except:
            features.tempo = 0.0
    
    return features.to_dict()

def normalize_features(features_dict: Dict[str, Dict]) -> Dict[str, Dict]:
    """
    Normalize feature values across all samples to range [0, 1].
    
    Args:
        features_dict: Dictionary of sample IDs to feature dictionaries
        
    Returns:
        Dictionary with normalized features
    """
    # Collect all values for each feature
    feature_values = {}
    
    for sample_id, features in features_dict.items():
        for feature, value in features.items():
            if feature not in ['mfcc', 'chroma']:  # Handle these separately
                if feature not in feature_values:
                    feature_values[feature] = []
                feature_values[feature].append(value)
    
    # Normalize features
    normalized_features = {}
    
    for sample_id, features in features_dict.items():
        normalized_features[sample_id] = {}
        
        for feature, value in features.items():
            if feature not in ['mfcc', 'chroma']:
                # Get min and max for this feature
                min_val = min(feature_values[feature])
                max_val = max(feature_values[feature])
                
                # Avoid division by zero
                if max_val > min_val:
                    normalized_features[sample_id][feature] = (value - min_val) / (max_val - min_val)
                else:
                    normalized_features[sample_id][feature] = 0.0
            else:
                normalized_features[sample_id][feature] = value
    
    return normalized_features
