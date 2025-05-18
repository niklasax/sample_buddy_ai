import os
import json
import logging
import argparse
from pathlib import Path
import time
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import shutil
import traceback
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    logger.warning("Librosa not installed. Some features will be unavailable.")
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
        Dictionary of audio features - uses fallback features if librosa is not available
    """
    # Define basic fallback features for when librosa is not available
    basic_features = {
        "duration": 0.0,
        "sample_rate": 44100,  # Standard CD quality
        "energy": 0.5,
        "brightness": 0.5,
        "roughness": 0.3,
        "tempo": 120,
        "extraction_method": "basic_fallback"
    }
    
    # Try to get at least duration from file size if possible
    try:
        file_size = os.path.getsize(file_path)
        # Rough estimate: ~10MB per minute of decent quality audio
        estimated_duration = file_size / (10 * 1024 * 1024) * 60
        basic_features["duration"] = max(0.1, min(estimated_duration, 10))  # Cap between 0.1s and 10min
    except Exception as e:
        logger.warning(f"Could not estimate duration from file size: {e}")
    
    if not LIBROSA_AVAILABLE:
        logger.warning("Librosa not available. Using basic fallback features.")
        return basic_features
    
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
        # Return a basic feature set instead of None to maintain type consistency
        return {
            "duration": 0.0,
            "sample_rate": 44100,
            "energy": 0.5,
            "brightness": 0.5,
            "roughness": 0.3,
            "tempo": 120,
            "extraction_method": "error_fallback",
            "error": str(e)
        }

def determine_mood_from_features(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Determine mood characteristics from audio features.
    
    Args:
        features: Dictionary of audio features
        
    Returns:
        Dictionary of mood characteristics
    """
    if not features:
        return {"energy": "neutral", "brightness": "neutral", "texture": "neutral", "overall_mood": ["neutral"]}
    
    mood = {}
    
    # Check if we're using fallback features
    is_fallback = features.get('extraction_method') == 'basic_fallback'
    
    if is_fallback:
        # For fallback features, use the direct values provided
        energy_value = features.get('energy', 0.5) * 10  # Scale 0-1 to 0-10
        brightness_value = features.get('brightness', 0.5) * 10  # Scale 0-1 to 0-10
        texture_value = features.get('roughness', 0.3) * -100  # Convert to texture scale
    else:
        # For full librosa features, calculate as before
        energy_value = (
            features.get('energy_mean', 0) * 5 + 
            features.get('onset_rate', 0) * 0.5
        )
        
        brightness_value = (
            features.get('avg_centroid', 0) / 1000 + 
            features.get('avg_rolloff', 0) / 5000
        )
        
        texture_value = (
            -1 * features.get('avg_contrast', 0) - 
            features.get('avg_flatness', 0) * 100
        )
    
    # Set the calculated values
    mood['energy_value'] = round(energy_value, 2)
    mood['brightness_value'] = round(brightness_value, 2)
    mood['texture_value'] = round(texture_value, 2)
    
    # Energy classification
    if energy_value < 2:
        mood['energy'] = "chill"
    elif energy_value < 5:
        mood['energy'] = "moderate"
    else:
        mood['energy'] = "energetic"
    
    # Brightness classification
    if brightness_value < 3:
        mood['brightness'] = "dark"
    elif brightness_value < 7:
        mood['brightness'] = "warm"
    else:
        mood['brightness'] = "bright"
    
    # Texture classification
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

# Global variables for progress tracking
_progress_lock = threading.Lock()
_progress_data = {
    "total_files": 0,
    "processed_files": 0,
    "current_batch": 0,
    "total_batches": 0,
    "batch_progress": 0,
    "overall_progress": 0,
    "status_message": "Initializing...",
    "errors": []
}

def _update_progress(increment: int = 0, batch_num: Optional[int] = None, message: Optional[str] = None, error: Optional[str] = None):
    """
    Update the global progress tracking data.
    
    Args:
        increment: Number of files to increment the processed count
        batch_num: Current batch number (if changed)
        message: Status message to update
        error: Error message to add to the error list
    """
    with _progress_lock:
        if increment > 0:
            _progress_data["processed_files"] += increment
        
        if batch_num is not None:
            _progress_data["current_batch"] = batch_num
        
        if message is not None:
            _progress_data["status_message"] = message
        
        if error is not None:
            _progress_data["errors"].append(error)
        
        # Calculate progress percentages
        if _progress_data["total_files"] > 0:
            _progress_data["overall_progress"] = (_progress_data["processed_files"] / _progress_data["total_files"]) * 100
        
        if _progress_data["total_batches"] > 0:
            _progress_data["batch_progress"] = (_progress_data["current_batch"] / _progress_data["total_batches"]) * 100
        
        # Log progress
        logger.info(f"Progress: {_progress_data['overall_progress']:.1f}% - Batch {_progress_data['current_batch']}/{_progress_data['total_batches']} - {_progress_data['status_message']}")

def process_single_file(file_path: str, output_dir: Optional[str] = None, deep_analysis: bool = True, 
                        batch_num: int = 0, file_num: int = 0) -> Dict[str, Any]:
    """
    Process a single audio file with feature extraction and classification.
    
    Args:
        file_path: Path to the audio file
        output_dir: Output directory for classified files (optional)
        deep_analysis: Whether to perform deep audio analysis
        batch_num: Current batch number (for logging)
        file_num: Current file number within batch (for logging)
        
    Returns:
        Dictionary with processing results for the file
    """
    start_time = time.time()
    file_name = os.path.basename(file_path)
    
    try:
        _update_progress(message=f"Processing file: {file_name}")
        
        # Generate a unique ID for the sample
        sample_id = f"sample_{os.path.splitext(file_name)[0].replace(' ', '_').lower()}"
        
        # Initial classification by filename
        classification = classify_by_filename(file_path)
        
        # Extract audio features if deep analysis is requested
        features = None
        mood_from_features = {}
        feature_extraction_time = 0
        
        if deep_analysis:
            feature_start_time = time.time()
            _update_progress(message=f"Extracting features from {file_name}")
            
            # Always call extract_audio_features - it now has built-in fallback
            features = extract_audio_features(file_path)
            feature_extraction_time = time.time() - feature_start_time
            
            if features:
                # Check if we're using fallback features
                if features.get('extraction_method') == 'basic_fallback':
                    logger.info(f"Using basic fallback features for {file_name} (librosa not available)")
                
                # Determine mood from features - handle both full and fallback feature sets
                mood_from_features = determine_mood_from_features(features)
                
                # Override mood with the one determined from features if available
                if (mood_from_features and 
                    isinstance(mood_from_features, dict) and 
                    'overall_mood' in mood_from_features and
                    isinstance(mood_from_features['overall_mood'], list) and
                    len(mood_from_features['overall_mood']) > 0):
                    classification['mood'] = mood_from_features['overall_mood'][0]
            else:
                logger.warning(f"Could not extract any features from {file_path}")
        
        # Create sample metadata
        sample = {
            "id": sample_id,
            "name": file_name,
            "path": file_path,
            "category": classification["type"],
            "subtype": classification["subtype"],
            "mood": classification["mood"],
            "batch": batch_num,
            "processing_time": time.time() - start_time,
            "feature_extraction_time": feature_extraction_time
        }
        
        # Add compact features if available
        if features:
            # Only include selected features to keep the JSON size reasonable
            sample["features"] = {
                "tempo": features.get('tempo', 0),
                "energy": features.get('energy_mean', 0),
                "brightness": features.get('avg_centroid', 0),
                "warmth": features.get('low_mid_ratio', 0) if 'low_mid_ratio' in features else 0,
                "transients": features.get('avg_zcr', 0)
            }
        
        if mood_from_features:
            sample["mood_details"] = mood_from_features
        
        # Organize the file if output directory is provided
        if output_dir:
            category_dir = os.path.join(output_dir, classification["type"])
            mood_dir = os.path.join(category_dir, classification["mood"])
            
            # Create category and mood directories
            os.makedirs(mood_dir, exist_ok=True)
            
            # Destination path
            dest_path = os.path.join(mood_dir, file_name)
            
            # Copy the file
            try:
                if os.path.exists(file_path) and file_path != dest_path:
                    shutil.copy2(file_path, dest_path)
                    logger.info(f"Copied {file_name} to {classification['type']}/{classification['mood']}")
                else:
                    logger.info(f"Would copy {file_name} to {classification['type']}/{classification['mood']}")
            except Exception as copy_error:
                error_msg = f"Error copying {file_name}: {str(copy_error)}"
                logger.error(error_msg)
                sample["copy_error"] = str(copy_error)
            
            # Add destination path to sample metadata
            sample["dest_path"] = dest_path
        
        # Signal successful processing
        _update_progress(increment=1)
        
        return {"success": True, "sample": sample}
        
    except Exception as e:
        error_msg = f"Error processing {file_name}: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        _update_progress(increment=1, error=error_msg)
        
        return {
            "success": False, 
            "error": str(e), 
            "file_path": file_path,
            "batch": batch_num,
            "file_num": file_num
        }

def process_files(input_files: List[str], output_dir: Optional[str] = None, deep_analysis: bool = True, 
                  batch_size: int = 10, max_workers: int = 2) -> Dict[str, Any]:
    """
    Process audio files with feature extraction and classification using batch processing.
    
    Args:
        input_files: List of file paths to process
        output_dir: Output directory for classified files (optional)
        deep_analysis: Whether to perform deep audio analysis
        batch_size: Number of files to process in each batch
        max_workers: Maximum number of worker threads for processing
        
    Returns:
        Dictionary with processing results
    """
    # Initialize results and statistics
    results = {
        "success": True, 
        "samples": [], 
        "errors": [],
        "stats": {
            "total_files": len(input_files),
            "processed_files": 0,
            "failed_files": 0,
            "total_time": 0,
            "batch_size": batch_size,
            "max_workers": max_workers
        }
    }
    
    # Validate input
    if not input_files:
        logger.warning("No input files provided")
        return results
    
    total_files = len(input_files)
    processed_files = 0
    failed_files = 0
    
    # Calculate number of batches
    num_batches = (total_files + batch_size - 1) // batch_size
    
    # Initialize progress tracking
    global _progress_data
    with _progress_lock:
        _progress_data = {
            "total_files": total_files,
            "processed_files": 0,
            "current_batch": 0,
            "total_batches": num_batches,
            "batch_progress": 0,
            "overall_progress": 0,
            "status_message": "Starting processing...",
            "errors": []
        }
    
    start_time = time.time()
    
    # Log start of processing
    logger.info(f"Processing {total_files} audio files in {num_batches} batches (batch size: {batch_size}, workers: {max_workers})")
    
    # Process files in batches
    for batch_num in range(num_batches):
        batch_start_time = time.time()
        
        # Calculate batch range
        batch_start = batch_num * batch_size
        batch_end = min(batch_start + batch_size, total_files)
        batch_files = input_files[batch_start:batch_end]
        
        # Update progress with batch information
        _update_progress(batch_num=batch_num+1, 
                        message=f"Starting batch {batch_num+1}/{num_batches} with {len(batch_files)} files")
        
        # Process files in this batch with ThreadPoolExecutor for parallel processing
        batch_results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks and collect futures
            futures = {
                executor.submit(
                    process_single_file, 
                    file_path, 
                    output_dir, 
                    deep_analysis, 
                    batch_num+1, 
                    i+1
                ): (i, file_path) for i, file_path in enumerate(batch_files)
            }
            
            # Process results as they complete
            for future in as_completed(futures):
                file_idx, file_path = futures[future]
                try:
                    file_result = future.result()
                    batch_results.append(file_result)
                    
                    if file_result["success"]:
                        results["samples"].append(file_result["sample"])
                    else:
                        results["errors"].append(file_result)
                        failed_files += 1
                    
                except Exception as e:
                    error_msg = f"Unexpected error processing {os.path.basename(file_path)}: {str(e)}"
                    logger.error(error_msg)
                    logger.error(traceback.format_exc())
                    results["errors"].append({
                        "file_path": file_path,
                        "error": str(e),
                        "batch": batch_num+1,
                        "file_num": file_idx+1
                    })
                    failed_files += 1
        
        # Calculate batch stats
        batch_time = time.time() - batch_start_time
        processed_in_batch = len(batch_files) - sum(1 for r in batch_results if not r.get("success", False))
        processed_files += processed_in_batch
        
        # Log batch completion
        logger.info(f"Batch {batch_num+1}/{num_batches} completed in {batch_time:.2f} seconds. "
                    f"Processed {processed_in_batch}/{len(batch_files)} files successfully.")
    
    # Calculate final stats
    end_time = time.time()
    total_time = end_time - start_time
    files_per_second = processed_files / total_time if total_time > 0 else 0
    
    # Update statistics
    results["stats"].update({
        "processed_files": processed_files,
        "failed_files": failed_files, 
        "total_time": total_time,
        "files_per_second": files_per_second,
        "num_batches": num_batches
    })
    
    # Log completion
    logger.info(f"Processing completed: {processed_files}/{total_files} files processed "
                f"in {total_time:.2f} seconds ({files_per_second:.2f} files/sec)")
    
    return results

def main():
    """Main function to run the classifier from command line."""
    parser = argparse.ArgumentParser(description="Deep classify audio samples with feature extraction")
    parser.add_argument("config_file", help="JSON config file with input_files and output_dir")
    parser.add_argument("--quick", action="store_true", help="Skip deep audio analysis")
    parser.add_argument("--batch-size", type=int, default=10, help="Number of files to process in each batch")
    parser.add_argument("--max-workers", type=int, default=2, help="Maximum number of worker threads")
    
    args = parser.parse_args()
    
    # Load config file
    with open(args.config_file, "r") as f:
        config = json.load(f)
    
    # Process files
    deep_analysis = not args.quick
    results = process_files(
        input_files=config.get("files", []),
        output_dir=config.get("outputDir"),
        deep_analysis=deep_analysis,
        batch_size=args.batch_size,
        max_workers=args.max_workers
    )
    
    # Print results as JSON
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()