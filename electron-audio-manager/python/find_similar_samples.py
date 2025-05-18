#!/usr/bin/env python3
"""
Find similar audio samples based on audio features.

Usage:
    python find_similar_samples.py /path/to/reference_sample.wav processed_dir max_results=5
"""

import os
import sys
import json
import glob
import numpy as np
from pathlib import Path
from scipy.spatial.distance import cosine


def load_sample_features(sample_path):
    """
    Load audio features for a sample. If the sample has an associated
    JSON file with features, load it, otherwise return None.
    
    Args:
        sample_path: Path to the audio file
        
    Returns:
        Dictionary of features or None if no features found
    """
    # Look for a corresponding JSON file with the same name
    features_path = Path(str(sample_path).rsplit('.', 1)[0] + '.json')
    
    # If no features file exists, return None
    if not features_path.exists():
        return None
    
    # Load the features from the JSON file
    try:
        with open(features_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading features for {sample_path}: {str(e)}", file=sys.stderr)
        return None


def create_feature_vector(features):
    """
    Create a normalized feature vector from features dictionary.
    
    Args:
        features: Dictionary of audio features
        
    Returns:
        Numpy array with normalized feature values
    """
    # List of features to include in the vector (adjust as needed)
    feature_keys = [
        'spectral_centroid', 'spectral_bandwidth', 'spectral_rolloff',
        'zero_crossing_rate', 'energy', 'tempo'
    ]
    
    # Extract MFCC features if available
    mfcc_features = []
    if 'mfcc' in features and isinstance(features['mfcc'], list):
        # Use only the first N MFCCs to keep vector size reasonable
        mfcc_features = features['mfcc'][:10]
    
    # Build the feature vector from available features
    vector = []
    for key in feature_keys:
        if key in features and isinstance(features[key], (int, float)):
            vector.append(float(features[key]))
        else:
            vector.append(0.0)  # Default value if feature is missing
    
    # Add MFCCs if available
    vector.extend(mfcc_features)
    
    # Convert to numpy array
    feature_vector = np.array(vector)
    
    # Normalize the vector (if not all zeros)
    norm = np.linalg.norm(feature_vector)
    if norm > 0:
        feature_vector = feature_vector / norm
    
    return feature_vector


def find_similar_samples(reference_path, samples_dir, max_results=5):
    """
    Find samples similar to the reference sample.
    
    Args:
        reference_path: Path to the reference audio file
        samples_dir: Directory containing processed samples and their feature files
        max_results: Maximum number of similar samples to return
        
    Returns:
        List of dictionaries with similar samples info
    """
    # Load reference sample features
    reference_features = load_sample_features(reference_path)
    if not reference_features:
        print(f"No features found for reference sample: {reference_path}", file=sys.stderr)
        return []
    
    # Create reference feature vector
    reference_vector = create_feature_vector(reference_features)
    
    # Get all audio files in the samples directory
    audio_extensions = ['.wav', '.mp3', '.ogg', '.flac', '.aif', '.aiff']
    sample_files = []
    for ext in audio_extensions:
        sample_files.extend(glob.glob(os.path.join(samples_dir, '**', f'*{ext}'), recursive=True))
    
    # Calculate similarity scores for each sample
    similarity_scores = []
    for sample_path in sample_files:
        # Skip the reference sample itself
        if os.path.abspath(sample_path) == os.path.abspath(reference_path):
            continue
        
        # Load sample features
        sample_features = load_sample_features(sample_path)
        if not sample_features:
            continue
        
        # Create sample feature vector
        sample_vector = create_feature_vector(sample_features)
        
        # Calculate cosine similarity (1 is most similar, 0 is least similar)
        similarity = 1 - cosine(reference_vector, sample_vector)
        
        # Add to results if similarity is positive
        if similarity > 0:
            sample_name = os.path.basename(sample_path)
            similarity_scores.append({
                'path': sample_path,
                'name': sample_name,
                'similarity': float(similarity),
                'category': sample_features.get('category', 'Unknown'),
                'mood': sample_features.get('mood', 'Unknown')
            })
    
    # Sort by similarity score (highest first) and limit to max_results
    similarity_scores.sort(key=lambda x: x['similarity'], reverse=True)
    return similarity_scores[:max_results]


def main():
    """Main function."""
    if len(sys.argv) < 3:
        print("Usage: python find_similar_samples.py <reference_sample> <samples_dir> [max_results]", 
              file=sys.stderr)
        sys.exit(1)
    
    reference_path = sys.argv[1]
    samples_dir = sys.argv[2]
    
    max_results = 5
    if len(sys.argv) > 3:
        try:
            # Check if the format is max_results=N
            if '=' in sys.argv[3]:
                max_results_str = sys.argv[3].split('=')[1]
                max_results = int(max_results_str)
            else:
                max_results = int(sys.argv[3])
        except (ValueError, IndexError):
            print(f"Invalid max_results value: {sys.argv[3]}, using default (5)", file=sys.stderr)
    
    # Check if files/directories exist
    if not os.path.isfile(reference_path):
        print(f"Reference sample not found: {reference_path}", file=sys.stderr)
        sys.exit(1)
    
    if not os.path.isdir(samples_dir):
        print(f"Samples directory not found: {samples_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Find similar samples
    similar_samples = find_similar_samples(reference_path, samples_dir, max_results)
    
    # Output as JSON
    print(json.dumps({
        'reference': os.path.basename(reference_path),
        'samples': similar_samples
    }))


if __name__ == "__main__":
    main()