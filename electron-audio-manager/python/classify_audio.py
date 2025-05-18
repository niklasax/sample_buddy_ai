#!/usr/bin/env python
"""
Audio Sample Classifier
-----------------------
This script processes audio files and classifies them by instrument type and mood.
It's used by the Electron Audio Sample Manager application.
"""

import os
import sys
import json
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try importing audio processing libraries
try:
    import librosa
    import librosa.display
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
except ImportError as e:
    logger.error(f"Required dependency not found: {e}")
    logger.error("Please install required packages: librosa, scikit-learn, numpy")
    sys.exit(1)

def process_audio_files(input_files: List[str], output_dir: str) -> Dict[str, Any]:
    """
    Process a list of audio files, extract features, classify, and organize into categories.
    
    Args:
        input_files: List of file paths to process
        output_dir: Output directory for classified files
        
    Returns:
        Dictionary with processing results
    """
    logger.info(f"Processing {len(input_files)} audio files")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Process each file
    samples = {}
    for file_path in input_files:
        try:
            sample_id = generate_sample_id(file_path)
            filename = os.path.basename(file_path)
            
            logger.info(f"Processing file: {filename}")
            
            # Extract audio features
            y, sr = load_audio(file_path)
            features = extract_features(y, sr)
            
            # Store sample details
            samples[sample_id] = {
                'id': sample_id,
                'name': filename,
                'path': file_path,
                'features': features,
                'category': 'unknown',
                'mood': 'neutral'
            }
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
    
    if not samples:
        return {'success': False, 'error': 'No valid audio files to process', 'samples': []}
    
    # Classify samples
    samples = classify_audio_samples(samples)
    
    # Organize files into categories
    organized_samples = organize_files(samples, output_dir)
    
    return {
        'success': True,
        'samples': list(organized_samples.values())
    }

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
        logger.error(f"Error loading audio file {file_path}: {e}")
        raise

def extract_features(y: np.ndarray, sr: int) -> Dict[str, Any]:
    """
    Extract audio features from an audio signal.
    
    Args:
        y: Audio signal
        sr: Sample rate
        
    Returns:
        Dictionary of audio features
    """
    # Basic features
    features = {}
    
    # Extract spectral features
    features['spectral_centroid'] = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)[0]))
    features['spectral_bandwidth'] = float(np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]))
    features['spectral_rolloff'] = float(np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr)[0]))
    
    # Zero crossing rate (percussiveness)
    features['zero_crossing_rate'] = float(np.mean(librosa.feature.zero_crossing_rate(y)[0]))
    
    # RMS energy
    features['rms'] = float(np.mean(librosa.feature.rms(y=y)[0]))
    
    # Tempo
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo = librosa.beat.tempo(onset_envelope=onset_env, sr=sr)[0]
    features['tempo'] = float(tempo)
    
    # Calculate MFCCs (timbre)
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    features['mfcc'] = [float(np.mean(mfcc)) for mfcc in mfccs]
    
    # Chromagram (pitch content)
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    features['chroma'] = [float(np.mean(c)) for c in chroma]
    
    # Duration
    features['duration'] = float(len(y) / sr)
    
    return features

def classify_audio_samples(samples: Dict[str, Dict]) -> Dict[str, Dict]:
    """
    Classify audio samples by instrument type and mood.
    
    Args:
        samples: Dictionary of audio samples with features
        
    Returns:
        Updated dictionary with classification results
    """
    try:
        # Create feature matrix
        feature_list = []
        sample_ids = []
        
        for sample_id, sample in samples.items():
            if 'features' in sample:
                feature_vector = create_feature_vector(sample['features'])
                feature_list.append(feature_vector)
                sample_ids.append(sample_id)
        
        if not feature_list:
            logger.warning("No feature data available for classification")
            return samples
        
        # Convert to numpy array
        X = np.array(feature_list)
        
        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Classify by instrument type
        instrument_labels = classify_instrument_types(X_scaled, sample_ids, samples)
        
        # Classify by mood
        mood_labels = classify_moods(X_scaled, sample_ids, samples)
        
        logger.info("Classification complete")
        return samples
        
    except Exception as e:
        logger.error(f"Error in classification: {e}")
        return samples

def create_feature_vector(features: Dict[str, Any]) -> List[float]:
    """
    Create a feature vector for classification from features dictionary.
    
    Args:
        features: Dictionary of audio features
        
    Returns:
        Feature vector as list of floats
    """
    # Select most relevant features for clustering
    feature_vector = [
        features.get('spectral_centroid', 0),
        features.get('spectral_bandwidth', 0),
        features.get('spectral_rolloff', 0),
        features.get('zero_crossing_rate', 0),
        features.get('rms', 0),
        features.get('tempo', 0),
    ]
    
    # Add MFCCs (first 5)
    mfccs = features.get('mfcc', [])
    feature_vector.extend(mfccs[:5] if len(mfccs) >= 5 else mfccs + [0] * (5 - len(mfccs)))
    
    # Add chroma features (first 3)
    chroma = features.get('chroma', [])
    feature_vector.extend(chroma[:3] if len(chroma) >= 3 else chroma + [0] * (3 - len(chroma)))
    
    return feature_vector

def classify_instrument_types(X: np.ndarray, sample_ids: List[str], samples: Dict[str, Dict]) -> List[str]:
    """
    Classify audio samples by instrument type using clustering.
    
    Args:
        X: Feature matrix (scaled)
        sample_ids: List of sample IDs
        samples: Dictionary of audio samples with metadata
        
    Returns:
        List of instrument category labels
    """
    # Use k-means clustering to group similar sounds
    num_clusters = min(5, len(X))  # Don't create more clusters than samples
    if num_clusters < 2:
        # Not enough samples for meaningful clustering
        for sample_id in sample_ids:
            # Use heuristic classification based on filename if available
            samples[sample_id]['category'] = classify_by_filename(samples[sample_id]['name'])
        return [samples[sample_id]['category'] for sample_id in sample_ids]
    
    # Perform clustering
    kmeans = KMeans(n_clusters=num_clusters, random_state=42)
    clusters = kmeans.fit_predict(X)
    
    # Define instrument categories based on cluster characteristics
    cluster_categories = assign_categories_to_clusters(X, clusters, kmeans)
    
    # Assign categories to samples
    for i, sample_id in enumerate(sample_ids):
        cluster = clusters[i]
        # Get the category for this cluster
        category = cluster_categories.get(cluster)
        
        # If clustering doesn't provide a clear category, use filename heuristic
        if not category:
            category = classify_by_filename(samples[sample_id]['name'])
            
        samples[sample_id]['category'] = category
    
    return [samples[sample_id]['category'] for sample_id in sample_ids]

def assign_categories_to_clusters(X: np.ndarray, clusters: np.ndarray, kmeans: KMeans) -> Dict[int, str]:
    """
    Assign instrument categories to clusters based on feature characteristics.
    
    Args:
        X: Feature matrix
        clusters: Cluster assignments
        kmeans: Fitted KMeans model
        
    Returns:
        Dictionary mapping cluster IDs to category names
    """
    # Get cluster centers
    centers = kmeans.cluster_centers_
    
    # Define categories
    categories = {
        'percussion': {'zero_crossing_rate': 'high', 'spectral_centroid': 'high'},
        'bass': {'spectral_centroid': 'low'},
        'guitar': {'rms': 'medium', 'spectral_centroid': 'medium'},
        'synth': {'spectral_bandwidth': 'high'},
        'vocal': {'spectral_bandwidth': 'medium', 'spectral_rolloff': 'medium'},
        'ambient': {'rms': 'low', 'spectral_centroid': 'low'},
    }
    
    # Calculate feature importance indices
    feature_indices = {
        'spectral_centroid': 0,
        'spectral_bandwidth': 1,
        'spectral_rolloff': 2,
        'zero_crossing_rate': 3,
        'rms': 4,
    }
    
    # Calculate median values for features
    medians = np.median(X, axis=0)
    
    # Assign categories to clusters
    cluster_categories = {}
    for cluster_id in range(len(centers)):
        center = centers[cluster_id]
        
        # Compare cluster center to feature medians
        feature_levels = {}
        for feature, idx in feature_indices.items():
            if center[idx] > medians[idx] * 1.5:
                feature_levels[feature] = 'high'
            elif center[idx] < medians[idx] * 0.5:
                feature_levels[feature] = 'low'
            else:
                feature_levels[feature] = 'medium'
        
        # Find the best matching category
        best_category = None
        best_score = 0
        
        for category, criteria in categories.items():
            score = 0
            for feature, level in criteria.items():
                if feature in feature_levels and feature_levels[feature] == level:
                    score += 1
            
            if score > best_score:
                best_score = score
                best_category = category
        
        cluster_categories[cluster_id] = best_category if best_score > 0 else 'other'
    
    return cluster_categories

def classify_by_filename(filename: str) -> str:
    """
    Classify audio sample based on filename.
    
    Args:
        filename: Name of the audio file
        
    Returns:
        Category label
    """
    filename = filename.lower()
    
    if any(kw in filename for kw in ['kick', 'snare', 'drum', 'hat', 'perc', 'clap', 'cym']):
        return 'percussion'
    elif any(kw in filename for kw in ['bass', 'sub', '808']):
        return 'bass'
    elif any(kw in filename for kw in ['guitar', 'gtr', 'strum']):
        return 'guitar'
    elif any(kw in filename for kw in ['synth', 'lead', 'arp', 'pad']):
        return 'synth'
    elif any(kw in filename for kw in ['vox', 'vocal', 'voice', 'sing']):
        return 'vocal'
    elif any(kw in filename for kw in ['amb', 'atmo', 'pad', 'texture']):
        return 'ambient'
    elif any(kw in filename for kw in ['fx', 'effect', 'impact', 'trans']):
        return 'fx'
    else:
        return 'other'

def classify_moods(X: np.ndarray, sample_ids: List[str], samples: Dict[str, Dict]) -> List[str]:
    """
    Classify audio samples by mood based on audio features.
    
    Args:
        X: Feature matrix (scaled)
        sample_ids: List of sample IDs
        samples: Dictionary of audio samples with metadata
        
    Returns:
        List of mood category labels
    """
    # Simple heuristic-based mood classification
    for i, sample_id in enumerate(sample_ids):
        features = samples[sample_id]['features']
        
        # Extract relevant features
        rms = features.get('rms', 0)
        tempo = features.get('tempo', 0)
        spec_cent = features.get('spectral_centroid', 0)
        
        # Thresholds for mood classification
        # High energy, fast tempo, bright sound = aggressive
        if rms > 0.3 and tempo > 120 and spec_cent > 2000:
            mood = 'aggressive'
        # Low energy, moderate tempo, darker sound = mellow
        elif rms < 0.15 and tempo < 100:
            mood = 'mellow'
        # High energy, moderate tempo = energetic
        elif rms > 0.2 and tempo > 100:
            mood = 'energetic'
        # Low energy, slow tempo = calm
        elif rms < 0.1 and tempo < 80:
            mood = 'calm'
        # Default
        else:
            mood = 'neutral'
        
        samples[sample_id]['mood'] = mood
    
    return [samples[sample_id]['mood'] for sample_id in sample_ids]

def organize_files(samples: Dict[str, Dict], output_dir: str) -> Dict[str, Dict]:
    """
    Organize audio files into category/mood folders.
    
    Args:
        samples: Dictionary of audio samples with classification
        output_dir: Base output directory
        
    Returns:
        Updated samples dictionary with new file paths
    """
    for sample_id, sample in samples.items():
        try:
            # Create category folder
            category_dir = os.path.join(output_dir, sample['category'])
            os.makedirs(category_dir, exist_ok=True)
            
            # Create mood subfolder
            mood_dir = os.path.join(category_dir, sample['mood'])
            os.makedirs(mood_dir, exist_ok=True)
            
            # Copy file to new location
            filename = os.path.basename(sample['path'])
            new_path = os.path.join(mood_dir, filename)
            
            # Skip if already processed
            if not os.path.exists(new_path) or os.path.getmtime(sample['path']) > os.path.getmtime(new_path):
                shutil.copy2(sample['path'], new_path)
                logger.info(f"Copied {filename} to {sample['category']}/{sample['mood']}")
            
            # Update path in samples dictionary
            sample['path'] = new_path
        except Exception as e:
            logger.error(f"Error organizing file {sample['name']}: {e}")
    
    # Create metadata file
    metadata = {
        'timestamp': str(datetime.datetime.now()),
        'sample_count': len(samples),
        'categories': {}
    }
    
    # Count samples per category
    for sample in samples.values():
        category = sample['category']
        mood = sample['mood']
        
        if category not in metadata['categories']:
            metadata['categories'][category] = {'count': 0, 'moods': {}}
        
        metadata['categories'][category]['count'] += 1
        
        if mood not in metadata['categories'][category]['moods']:
            metadata['categories'][category]['moods'][mood] = 0
        
        metadata['categories'][category]['moods'][mood] += 1
    
    # Write metadata
    metadata_path = os.path.join(output_dir, 'metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    return samples

def generate_sample_id(file_path: str) -> str:
    """
    Generate a unique ID for a sample based on its file path and modification time.
    
    Args:
        file_path: Path to audio file
        
    Returns:
        Unique ID for the sample
    """
    try:
        file_stat = os.stat(file_path)
        file_size = file_stat.st_size
        mod_time = file_stat.st_mtime
        return f"{os.path.basename(file_path)}_{file_size}_{int(mod_time)}"
    except Exception:
        # Fallback to just the filename as ID
        return os.path.basename(file_path)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python classify_audio.py <json_config_file>")
        sys.exit(1)
    
    # Read input configuration
    try:
        with open(sys.argv[1], 'r') as f:
            config = json.load(f)
        
        input_files = config.get('files', [])
        output_dir = config.get('outputDir', '')
        
        if not input_files or not output_dir:
            print("Error: Missing required input files or output directory")
            sys.exit(1)
        
        # Process files
        result = process_audio_files(input_files, output_dir)
        
        # Output result as JSON
        print(json.dumps(result))
        
    except Exception as e:
        error_result = {'success': False, 'error': str(e), 'samples': []}
        print(json.dumps(error_result))
        sys.exit(1)