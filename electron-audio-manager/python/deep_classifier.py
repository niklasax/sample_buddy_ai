import os
import json
import logging
import argparse
from pathlib import Path
import time
import numpy as np
from typing import Dict, List, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import librosa
try:
    import librosa
    import librosa.display
    logger.info(f"Librosa version {librosa.__version__} successfully imported!")
    LIBROSA_AVAILABLE = True
except ImportError:
    logger.warning("Librosa not installed. Using fallback methods for audio analysis.")
    LIBROSA_AVAILABLE = False

# Define category keywords (same as quick classifier)
CATEGORY_KEYWORDS = {
    "kick": ["kick", "bass drum", "bd", "808"],
    "snare": ["snare", "sd", "rim"],
    "hi_hat_cymbal": ["hat", "hh", "hi-hat", "hihat", "cymbal", "crash", "ride"],
    "tom": ["tom", "floor", "rack"],
    "clap": ["clap", "handclap"],
    "other_percussion": ["perc", "drum", "percussion", "shaker", "tambourine", "conga", "bongo"],
    "bass": ["bass", "sub", "808 bass", "bassline", "bass line"],
    "synth_lead": ["lead", "synth lead", "lead synth", "melody", "arp", "pluck", "saw lead"],
    "synth_pad": ["pad", "synth pad", "atmosphere", "ambient", "texture", "drone"],
    "piano_keys": ["piano", "keys", "keyboard", "rhodes", "wurlitzer", "organ", "epiano", "e-piano"],
    "strings": ["strings", "violin", "viola", "cello", "orchestral", "orchestra"],
    "brass": ["brass", "trumpet", "trombone", "horn", "sax", "saxophone"],
    "guitar": ["guitar", "gtr", "acoustic guitar", "electric guitar"],
    "vocal": ["vocal", "vox", "voice", "acapella", "sing", "choir", "adlib"],
    "fx": ["fx", "effect", "riser", "downlifter", "impact", "whoosh", "transition", "foley"],
}

# Define main categories
MAIN_CATEGORIES = {
    "percussion": ["kick", "snare", "hi_hat_cymbal", "tom", "clap", "other_percussion"],
    "bass": ["bass"],
    "lead": ["synth_lead", "piano_keys"],
    "pad": ["synth_pad", "strings", "brass"],
    "guitar": ["guitar"],
    "vocal": ["vocal"],
    "fx": ["fx"]
}

# Define mood keywords
MOOD_KEYWORDS = {
    "dark": ["dark", "minor", "sad", "moody", "melancholy", "scary", "horror", "tense"],
    "bright": ["bright", "major", "happy", "uplifting", "cheerful", "light"],
    "energetic": ["energetic", "energy", "powerful", "driving", "hard", "aggressive"],
    "chill": ["chill", "calm", "relaxed", "soft", "gentle", "mellow", "ambient"],
    "epic": ["epic", "cinematic", "movie", "trailer", "dramatic"],
}

def classify_by_filename(file_path: str) -> Dict[str, str]:
    """
    Classify audio sample based on filename.
    
    Args:
        file_path: Path to audio file
        
    Returns:
        Dictionary with classification results
    """
    filename = os.path.basename(file_path).lower()
    
    # Initialize with default classification
    classification = {
        'type': 'other',
        'subtype': 'other',
        'mood': 'neutral'
    }
    
    # Check for subtypes first
    for subtype, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in filename for keyword in keywords):
            classification['subtype'] = subtype
            break
    
    # Determine main type based on subtype
    for main_type, subtypes in MAIN_CATEGORIES.items():
        if classification['subtype'] in subtypes:
            classification['type'] = main_type
            break
    
    # Determine mood if possible
    for mood, keywords in MOOD_KEYWORDS.items():
        if any(keyword in filename for keyword in keywords):
            classification['mood'] = mood
            break
    
    return classification

def extract_audio_features(file_path: str) -> Dict[str, Any]:
    """
    Extract audio features using librosa if available.
    
    Args:
        file_path: Path to audio file
        
    Returns:
        Dictionary of audio features or None if extraction fails
    """
    if not LIBROSA_AVAILABLE:
        logger.warning("Librosa not available. Skipping feature extraction.")
        return None
    
    try:
        logger.info(f"Analyzing {os.path.basename(file_path)}...")
        
        # Load the audio file
        y, sr = librosa.load(file_path, sr=None)
        duration = librosa.get_duration(y=y, sr=sr)
        
        # Initialize features
        features = {
            'duration': duration,
            'sample_rate': sr
        }
        
        # Basic energy features
        rms = librosa.feature.rms(y=y)[0]
        features['energy_mean'] = float(np.mean(rms))
        features['energy_std'] = float(np.std(rms))
        features['energy_max'] = float(np.max(rms))
        features['energy_dynamic_range'] = float(features['energy_max'] / (features['energy_mean'] + 1e-5))
        
        # Spectral features
        S = np.abs(librosa.stft(y))
        
        # Spectral centroid (brightness)
        centroid = librosa.feature.spectral_centroid(S=S, sr=sr)[0]
        features['avg_centroid'] = float(np.mean(centroid))
        
        # Spectral bandwidth
        bandwidth = librosa.feature.spectral_bandwidth(S=S, sr=sr)[0]
        features['avg_bandwidth'] = float(np.mean(bandwidth))
        
        # Spectral contrast (tonal contrast)
        contrast = librosa.feature.spectral_contrast(S=S, sr=sr)
        features['avg_contrast'] = float(np.mean(contrast))
        
        # Spectral flatness (tone vs noise)
        flatness = librosa.feature.spectral_flatness(S=S)[0]
        features['avg_flatness'] = float(np.mean(flatness))
        
        # Spectral rolloff (frequency below which X% of energy is contained)
        rolloff = librosa.feature.spectral_rolloff(S=S, sr=sr)[0]
        features['avg_rolloff'] = float(np.mean(rolloff))
        
        # Rhythm features
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        tempo, _ = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
        features['tempo'] = float(tempo)
        
        # Onset rate (attacks per second)
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
        onset_rate = len(onset_frames) / duration if duration > 0 else 0
        features['onset_rate'] = float(onset_rate)
        
        # MFCC features for timbre
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        for i in range(min(5, mfccs.shape[0])):  # First 5 MFCCs
            features[f'mfcc{i+1}'] = float(np.mean(mfccs[i]))
        
        # Attack time
        envelope = np.abs(y)
        frame_length = int(sr * 0.03)  # 30ms frames
        hop_length = int(sr * 0.01)  # 10ms hop
        frames = librosa.util.frame(envelope, frame_length=frame_length, hop_length=hop_length)
        
        if frames.size > 0:
            env_frames = np.mean(frames, axis=0)
            peak_idx = np.argmax(env_frames)
            threshold = 0.8 * env_frames[peak_idx]
            attack_frames = 0
            
            for i in range(min(peak_idx, len(env_frames))):
                if env_frames[peak_idx - i] < threshold:
                    attack_frames = i
                    break
            
            attack_time = attack_frames * hop_length / sr
            features['attack_time'] = float(attack_time)
            features['has_transient'] = bool(attack_time < 0.05)
            
            # Check for sustain
            if peak_idx < len(env_frames) - 1:
                late_energy = np.mean(env_frames[int(len(env_frames)*0.7):])
                early_energy = np.mean(env_frames[int(len(env_frames)*0.1):int(len(env_frames)*0.3)])
                is_sustained = late_energy > (0.5 * early_energy)
                features['is_sustained'] = bool(is_sustained)
        
        # Zero crossing rate (noisiness)
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        features['avg_zcr'] = float(np.mean(zcr))
        
        # Harmonic-percussive source separation
        y_harmonic, y_percussive = librosa.effects.hpss(y)
        harmonic_energy = np.sum(y_harmonic**2)
        percussive_energy = np.sum(y_percussive**2)
        
        if percussive_energy > 0:
            features['harmonic_percussive_ratio'] = float(harmonic_energy / percussive_energy)
        else:
            features['harmonic_percussive_ratio'] = float(1.0)
        
        # Derived metrics for mood
        features['brightness'] = features['avg_centroid'] / (sr/2)  # Normalize by Nyquist
        features['roughness'] = float(1.0 - features['avg_contrast'])
        
        # Frequency band analysis
        spec = np.abs(librosa.stft(y))
        freqs = librosa.fft_frequencies(sr=sr)
        
        def get_band_indices(low, high):
            return np.where((freqs >= low) & (freqs < high))[0]
        
        bands = {
            "sub_bass": (20, 60),
            "bass": (60, 250),
            "low_mid": (250, 500),
            "mid": (500, 2000),
            "upper_mid": (2000, 4000),
            "high": (4000, 20000)
        }
        
        # Total energy
        total_energy = np.sum(spec)
        
        if total_energy > 0:
            # Calculate energy ratio for each band
            for band_name, (low, high) in bands.items():
                indices = get_band_indices(low, high)
                if len(indices) > 0:
                    band_energy = np.sum(spec[:, indices])
                    features[f'{band_name}_ratio'] = float(band_energy / total_energy)
                else:
                    features[f'{band_name}_ratio'] = 0.0
        
        logger.info(f"Successfully extracted {len(features)} features")
        return features
    
    except Exception as e:
        logger.error(f"Error extracting features from {file_path}: {e}")
        return None

def determine_mood_from_features(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Determine mood characteristics from audio features.
    
    Args:
        features: Dictionary of audio features
        
    Returns:
        Dictionary of mood characteristics
    """
    if not features:
        return {"energy": "neutral", "brightness": "neutral", "texture": "neutral"}
    
    mood = {}
    
    # Energy (chill to energetic)
    energy_value = (
        features.get('energy_mean', 0) * 5 + 
        features.get('onset_rate', 0) * 0.5
    )
    mood['energy_value'] = round(energy_value, 2)
    
    if energy_value < 2:
        mood['energy'] = "chill"
    elif energy_value < 5:
        mood['energy'] = "moderate"
    else:
        mood['energy'] = "energetic"
    
    # Brightness (dark to bright)
    brightness_value = (
        features.get('avg_centroid', 0) / 1000 + 
        features.get('avg_rolloff', 0) / 5000
    )
    mood['brightness_value'] = round(brightness_value, 2)
    
    if brightness_value < 3:
        mood['brightness'] = "dark"
    elif brightness_value < 7:
        mood['brightness'] = "warm"
    else:
        mood['brightness'] = "bright"
    
    # Texture (smooth to rough)
    texture_value = (
        -1 * features.get('avg_contrast', 0) - 
        features.get('avg_flatness', 0) * 100
    )
    mood['texture_value'] = round(texture_value, 2)
    
    if texture_value < -60:
        mood['texture'] = "rough"
    else:
        mood['texture'] = "smooth"
    
    # Overall mood (simplistic algorithm)
    mood_list = []
    
    if mood['energy'] == "chill":
        mood_list.append("chill")
    
    if mood['brightness'] == "dark":
        mood_list.append("dark")
        if mood['energy'] == "chill":
            mood_list.append("sad")
    elif mood['brightness'] == "bright":
        mood_list.append("bright")
        if mood['energy'] == "energetic":
            mood_list.append("happy")
    
    if mood['energy'] == "energetic" and mood['texture'] == "rough":
        mood_list.append("aggressive")
    
    if not mood_list:
        mood_list.append("neutral")
    
    mood['overall_mood'] = mood_list
    
    return mood

def process_files(input_files: List[str], output_dir: Optional[str] = None, deep_analysis: bool = True) -> Dict[str, Any]:
    """
    Process audio files with feature extraction and classification.
    
    Args:
        input_files: List of file paths to process
        output_dir: Output directory for classified files (optional)
        deep_analysis: Whether to perform deep audio analysis
        
    Returns:
        Dictionary with processing results
    """
    results = {"success": True, "samples": []}
    total_files = len(input_files)
    
    logger.info(f"Processing {total_files} audio files")
    
    # Process each file
    for i, file_path in enumerate(input_files):
        try:
            # Update progress with file count information for the renderer
            progress = (i + 1) / total_files * 100
            logger.info(f"Progress: {progress:.1f}% - Files processed: {i+1} of {total_files} - Processing file: {os.path.basename(file_path)}")
            
            # Generate a unique ID for the sample
            sample_id = f"sample_{os.path.splitext(os.path.basename(file_path))[0].replace(' ', '_').lower()}"
            
            # Initial classification by filename
            classification = classify_by_filename(file_path)
            
            # Extract audio features if deep analysis is requested
            features = None
            mood_from_features = {}
            
            if deep_analysis and LIBROSA_AVAILABLE:
                features = extract_audio_features(file_path)
                if features:
                    # Determine mood from features
                    mood_from_features = determine_mood_from_features(features)
                    
                    # Override mood with the one determined from features
                    if mood_from_features.get('overall_mood'):
                        classification['mood'] = mood_from_features.get('overall_mood')[0]
                else:
                    logger.warning(f"Could not extract features from {file_path}")
            
            # Create sample metadata
            sample = {
                "id": sample_id,
                "name": os.path.basename(file_path),
                "path": file_path,
                "category": classification["type"],
                "subtype": classification["subtype"],
                "mood": classification["mood"]
            }
            
            # Add features and detailed mood if available
            if features:
                sample["features"] = features
            
            if mood_from_features:
                sample["mood_details"] = mood_from_features
            
            # Organize the file if output directory is provided
            if output_dir:
                # Use the organized-samples folder structure
                organized_dir = output_dir
                
                # Create category directory (drums, bass, synth, etc.)
                category_dir = os.path.join(organized_dir, classification["type"])
                os.makedirs(category_dir, exist_ok=True)
                
                # Destination path directly in the category folder
                dest_path = os.path.join(category_dir, os.path.basename(file_path))
                
                # Also create a JSON file with the features data
                json_path = os.path.join(category_dir, f"{os.path.splitext(os.path.basename(file_path))[0]}.json")
                
                # Copy the file
                try:
                    import shutil
                    if os.path.exists(file_path) and file_path != dest_path:
                        # Copy the audio file to the destination
                        shutil.copy2(file_path, dest_path)
                        
                        # Write the features and classification info to a JSON file
                        with open(json_path, 'w') as json_file:
                            json_data = {
                                "file_name": os.path.basename(file_path),
                                "category": classification["type"],
                                "mood": classification["mood"],
                                "features": features if features else {},
                                "mood_details": mood_from_features if mood_from_features else {}
                            }
                            json.dump(json_data, json_file, indent=2)
                        
                        logger.info(f"Copied {os.path.basename(file_path)} to {classification['type']} and saved features")
                    else:
                        logger.info(f"Would copy {os.path.basename(file_path)} to {classification['type']}")
                except Exception as copy_error:
                    error_msg = f"Error copying {os.path.basename(file_path)}: {str(copy_error)}"
                    logger.error(error_msg)
                    sample["copy_error"] = str(copy_error)
                
                # Add destination path to sample metadata
                sample["dest_path"] = dest_path
            
            # Add sample to results
            results["samples"].append(sample)
            
            # Small delay to show progress in UI (for demo)
            time.sleep(0.05)
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
    
    return results

def main():
    """Main function to run the classifier from command line."""
    parser = argparse.ArgumentParser(description="Deep classify audio samples with feature extraction")
    parser.add_argument("config_file", help="JSON config file with input_files and output_dir")
    parser.add_argument("--quick", action="store_true", help="Skip deep audio analysis")
    
    args = parser.parse_args()
    
    # Load config file
    with open(args.config_file, "r") as f:
        config = json.load(f)
    
    # Process files
    deep_analysis = not args.quick
    results = process_files(config.get("files", []), config.get("outputDir"), deep_analysis)
    
    # Print results as JSON
    print(json.dumps(results))

if __name__ == "__main__":
    main()