import os
import logging
import numpy as np
from typing import Dict, List, Any, Tuple
import joblib
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# Define instrument categories
INSTRUMENT_CATEGORIES = [
    "percussion", "drums", "kick", "snare", "hihat", "cymbal",
    "bass", "guitar", "piano", "synth", "pad", "lead",
    "vocal", "voice", "fx", "ambient", "noise", "texture",
    "brass", "strings", "wind", "orchestral"
]

# Define mood categories
MOOD_CATEGORIES = [
    "aggressive", "energetic", "intense", "powerful",
    "chill", "relaxed", "mellow", "calm",
    "happy", "upbeat", "bright", "cheerful",
    "dark", "sad", "melancholic", "mysterious",
    "atmospheric", "dreamy", "spacey", "ethereal"
]

def classify_audio_samples(samples: Dict[str, Dict]) -> Dict[str, Dict]:
    """
    Classify audio samples by instrument type and mood.
    
    Args:
        samples: Dictionary of audio samples with features
        
    Returns:
        Updated dictionary with classification results
    """
    logging.info("Classifying audio samples")
    
    # Extract feature vectors for classification
    feature_vectors = []
    sample_ids = []
    
    for sample_id, sample in samples.items():
        if 'features' in sample and sample['features']:
            # Create feature vector for classification
            feature_vector = create_feature_vector(sample['features'])
            feature_vectors.append(feature_vector)
            sample_ids.append(sample_id)
    
    if not feature_vectors:
        logging.warning("No valid feature vectors found for classification")
        return samples
    
    # Convert to numpy array
    X = np.array(feature_vectors)
    
    # Normalize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Classify by instrument type
    instrument_categories = classify_instrument_types(X_scaled, sample_ids, samples)
    
    # Classify by mood
    mood_categories = classify_moods(X_scaled, sample_ids, samples)
    
    # Update samples with classification results
    for i, sample_id in enumerate(sample_ids):
        samples[sample_id]['category'] = instrument_categories[i]
        samples[sample_id]['mood'] = mood_categories[i]
    
    return samples

def create_feature_vector(features: Dict[str, Any]) -> List[float]:
    """
    Create a feature vector for classification from features dictionary.
    
    Args:
        features: Dictionary of audio features
        
    Returns:
        Feature vector as list of floats
    """
    # Select relevant features for classification
    feature_vector = [
        features.get('spectral_centroid', 0.0),
        features.get('spectral_bandwidth', 0.0),
        features.get('spectral_rolloff', 0.0),
        features.get('zero_crossing_rate', 0.0),
        features.get('energy', 0.0),
        features.get('tempo', 0.0),
        features.get('rms', 0.0)
    ]
    
    # Add first few MFCC coefficients
    mfccs = features.get('mfcc', [])
    for i in range(min(5, len(mfccs))):
        feature_vector.append(mfccs[i])
    
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
    # Use KMeans clustering to group similar sounds
    n_clusters = min(len(X), 8)  # Limit number of clusters
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    clusters = kmeans.fit_predict(X)
    
    # Map clusters to more meaningful categories
    # This ensures we use predefined categories instead of generic groups
    cluster_categories = {
        0: "drums",
        1: "bass",
        2: "synth",
        3: "vocal",
        4: "fx",
        5: "percussion",
        6: "ambient",
        7: "guitar"
    }
    
    # Assign instrument categories based on feature characteristics
    categories = []
    
    for i in range(len(X)):
        # Get sample features
        spectral_centroid = X[i, 0]
        zero_crossing_rate = X[i, 3]
        energy = X[i, 4]
        cluster = clusters[i]
        
        # Simple rule-based classification
        if zero_crossing_rate > 1.0:  # High ZCR indicates noisy sounds
            if energy > 1.0:
                category = "percussion"
            else:
                category = "fx"
        elif spectral_centroid > 1.0:  # High spectral centroid indicates bright sounds
            if energy > 1.0:
                category = "synth"
            else:
                category = "guitar"
        elif spectral_centroid < -0.5:  # Low spectral centroid indicates bass sounds
            category = "bass"
        elif energy > 1.5:  # High energy might indicate drums
            category = "drums"
        elif energy < -0.5:  # Low energy might indicate ambient sounds
            category = "ambient"
        else:
            # Use the cluster mapping instead of generic group_X
            if cluster in cluster_categories:
                category = cluster_categories[cluster]
            else:
                # Fallback to a named category rather than a generic group
                category = "sample"
                
                # Include the word that might appear in filename for better categorization
                # Get the current sample name directly
                sample_name = ""
                if i < len(sample_ids):
                    sample_id = sample_ids[i]
                    # Get the actual filename from the sample id metadata
                    for s_id, s_data in samples.items():
                        if s_id == sample_id and 'name' in s_data:
                            sample_name = s_data['name'].lower()
                            logging.debug(f"Found sample name for id {sample_id}: {sample_name}")
                            break
                
                logging.debug(f"Analyzing sample name: {sample_name}")
                
                # Fall back to the sample_id if name isn't available
                if not sample_name and i < len(sample_ids):
                    sample_name = sample_ids[i].lower()
                
                # Check for specific terms in the filename
                if sample_name:
                    if "vocal" in sample_name or "vox" in sample_name or "voc" in sample_name or "voice" in sample_name or "choir" in sample_name or "sing" in sample_name or "acapella" in sample_name:
                        category = "vocal"
                        logging.debug(f"Classified as vocal: {sample_name}")
                    elif "bass" in sample_name:
                        category = "bass"
                        logging.debug(f"Classified as bass: {sample_name}")
                    elif "drum" in sample_name or "perc" in sample_name or "kick" in sample_name or "snare" in sample_name:
                        category = "percussion"
                        logging.debug(f"Classified as percussion: {sample_name}")
                    elif "synth" in sample_name or "lead" in sample_name or "key" in sample_name or "piano" in sample_name or "keys" in sample_name or "keyboard" in sample_name:
                        category = "synth"
                        logging.debug(f"Classified as synth: {sample_name}")
                    elif "fx" in sample_name or "effect" in sample_name:
                        category = "fx"
                        logging.debug(f"Classified as fx: {sample_name}")
                    elif "guitar" in sample_name or "gtr" in sample_name:
                        category = "guitar"
                        logging.debug(f"Classified as guitar: {sample_name}")
                    elif "pad" in sample_name or "ambient" in sample_name or "atmo" in sample_name:
                        category = "ambient"
                        logging.debug(f"Classified as ambient: {sample_name}")
        
        categories.append(category)
    
    logging.debug(f"Classified categories: {set(categories)}")
    return categories

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
    moods = []
    
    # Predefined moods to ensure we use meaningful categories
    available_moods = [
        "aggressive", "energetic", "intense", "powerful",
        "chill", "relaxed", "mellow", "calm",
        "happy", "upbeat", "bright", "cheerful",
        "dark", "sad", "melancholic", "mysterious",
        "atmospheric", "dreamy", "spacey", "ethereal"
    ]
    
    for i in range(len(X)):
        # Get relevant features for mood classification
        energy = X[i, 4]
        tempo = X[i, 5]
        spectral_centroid = X[i, 0]
        
        # Simple rule-based mood classification
        if energy > 1.0 and tempo > 1.0:
            mood = "energetic"
        elif energy > 1.0 and spectral_centroid < -0.5:
            mood = "aggressive"
        elif energy < -0.5 and tempo < -0.5:
            mood = "chill"
        elif energy < -0.5 and spectral_centroid < -0.5:
            mood = "dark"
        elif tempo > 0.5 and spectral_centroid > 0.5:
            mood = "happy"
        elif spectral_centroid > 1.0 and energy < 0:
            mood = "atmospheric"
        elif spectral_centroid < -1.0:
            mood = "melancholic"
        else:
            # More intelligent mood assignment based on file name
            mood = "neutral"
            
            # Get the current sample name directly from the samples dictionary
            sample_name = ""
            if i < len(sample_ids):
                sample_id = sample_ids[i]
                # Get the actual filename from the sample id metadata
                for s_id, s_data in samples.items():
                    if s_id == sample_id and 'name' in s_data:
                        sample_name = s_data['name'].lower()
                        logging.debug(f"Found sample name for mood analysis: {sample_name}")
                        break
            
            # Fall back to the sample_id if name isn't available
            if not sample_name and i < len(sample_ids):
                sample_name = sample_ids[i].lower()
            
            logging.debug(f"Analyzing sample name for mood: {sample_name}")
            
            # Check for mood indicators in the filename
            if sample_name:
                for available_mood in available_moods:
                    if available_mood in sample_name:
                        mood = available_mood
                        logging.debug(f"Classified mood from name match: {mood}")
                        break
                
                # Alternative terms that suggest moods
                if mood == "neutral":  # Only apply if we didn't already match a mood
                    if "hard" in sample_name or "heavy" in sample_name or "pressure" in sample_name:
                        mood = "intense"
                        logging.debug(f"Classified as intense: {sample_name}")
                    elif "soft" in sample_name or "gentle" in sample_name or "chill" in sample_name:
                        mood = "mellow"
                        logging.debug(f"Classified as mellow: {sample_name}")
                    elif "bright" in sample_name or "sunny" in sample_name or "happy" in sample_name:
                        mood = "cheerful"
                        logging.debug(f"Classified as cheerful: {sample_name}")
                    elif "dark" in sample_name or "ominous" in sample_name or "deep" in sample_name:
                        mood = "mysterious"
                        logging.debug(f"Classified as mysterious: {sample_name}")
                    elif "ambient" in sample_name or "atmos" in sample_name or "space" in sample_name:
                        mood = "atmospheric"
                        logging.debug(f"Classified as atmospheric: {sample_name}")
                    elif "dreamy" in sample_name or "dream" in sample_name or "float" in sample_name:
                        mood = "dreamy"
                        logging.debug(f"Classified as dreamy: {sample_name}")
        
        moods.append(mood)
    
    logging.debug(f"Classified moods: {set(moods)}")
    return moods
