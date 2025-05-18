import os
import shutil
import argparse
import numpy as np
from pathlib import Path
import json
import csv
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Import librosa for audio analysis
try:
    import librosa
    import librosa.display
    print(f"Librosa version {librosa.__version__} successfully imported!")
except ImportError:
    print("Librosa not installed. Installing...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "librosa"])
    try:
        import librosa
        import librosa.display
        print(f"Librosa version {librosa.__version__} successfully installed and imported!")
    except ImportError:
        print("Failed to install librosa. Please install manually with:")
        print("pip install librosa")
        exit(1)

def list_audio_files(input_dir):
    """List all audio files in the input directory"""
    audio_files = []
    for file in os.listdir(input_dir):
        if file.lower().endswith(('.wav', '.mp3', '.aiff', '.aif', '.flac')):
            audio_files.append(os.path.join(input_dir, file))
    return audio_files

def extract_audio_features(file_path):
    """Extract comprehensive audio features using Librosa"""
    try:
        print(f"  Analyzing {os.path.basename(file_path)}...")
        
        # Load the audio file with librosa
        try:
            # Try default loading
            y, sr = librosa.load(file_path, sr=None)
            
            # If loaded successfully, get duration
            duration = librosa.get_duration(y=y, sr=sr)
            print(f"  Loaded audio: {duration:.2f} seconds, {sr} Hz")
        except Exception as e:
            print(f"  Warning: Error in basic loading: {e}")
            # Try with different parameters
            try:
                y, sr = librosa.load(file_path, sr=22050, mono=True)
                duration = librosa.get_duration(y=y, sr=sr)
                print(f"  Loaded with fallback: {duration:.2f} seconds, 22050 Hz")
            except Exception as e2:
                print(f"  Error: Could not load audio file: {e2}")
                return None
        
        # Initialize features dictionary
        features = {
            'duration': duration,
            'sample_rate': sr
        }
        
        # Basic energy features
        try:
            # RMS energy (loudness)
            rms = librosa.feature.rms(y=y)[0]
            energy_mean = np.mean(rms)
            energy_std = np.std(rms)
            energy_max = np.max(rms)
            
            features['energy_mean'] = float(energy_mean)
            features['energy_std'] = float(energy_std)
            features['energy_max'] = float(energy_max)
            features['energy_dynamic_range'] = float(energy_max / (energy_mean + 1e-5))
            
            print(f"  Extracted energy features")
        except Exception as e:
            print(f"  Warning: Error extracting energy features: {e}")
        
        # Spectral features
        try:
            # Compute spectrogram
            S = np.abs(librosa.stft(y))
            
            # Spectral centroid
            centroid = librosa.feature.spectral_centroid(S=S, sr=sr)[0]
            features['avg_centroid'] = float(np.mean(centroid))
            
            # Spectral bandwidth
            bandwidth = librosa.feature.spectral_bandwidth(S=S, sr=sr)[0]
            features['avg_bandwidth'] = float(np.mean(bandwidth))
            
            # Spectral contrast
            contrast = librosa.feature.spectral_contrast(S=S, sr=sr)
            features['avg_contrast'] = float(np.mean(contrast))
            
            # Spectral flatness
            flatness = librosa.feature.spectral_flatness(S=S)[0]
            features['avg_flatness'] = float(np.mean(flatness))
            
            # Spectral rolloff
            rolloff = librosa.feature.spectral_rolloff(S=S, sr=sr)[0]
            features['avg_rolloff'] = float(np.mean(rolloff))
            
            print(f"  Extracted spectral features")
        except Exception as e:
            print(f"  Warning: Error extracting spectral features: {e}")
        
        # Rhythm features
        try:
            # Tempo estimation
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            tempo, _ = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
            features['tempo'] = float(tempo)
            
            # Onset rate
            onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
            onset_rate = len(onset_frames) / duration if duration > 0 else 0
            features['onset_rate'] = float(onset_rate)
            
            print(f"  Extracted rhythm features")
        except Exception as e:
            print(f"  Warning: Error extracting rhythm features: {e}")
        
        # MFCC features for timbre analysis
        try:
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            for i in range(min(5, mfccs.shape[0])):  # Just use first 5 MFCCs
                features[f'mfcc{i+1}'] = float(np.mean(mfccs[i]))
            
            print(f"  Extracted MFCC features")
        except Exception as e:
            print(f"  Warning: Error extracting MFCC features: {e}")
        
        # Envelope analysis for ADSR
        try:
            # Calculate envelope
            envelope = np.abs(y)
            
            # Smooth envelope
            frame_length = int(sr * 0.03)  # 30ms frames
            hop_length = int(sr * 0.01)  # 10ms hop
            frames = librosa.util.frame(envelope, frame_length=frame_length, hop_length=hop_length)
            env_frames = np.mean(frames, axis=0)
            
            # Find attack time (time to reach 80% of peak)
            if len(env_frames) > 0:
                peak_idx = np.argmax(env_frames)
                threshold = 0.8 * env_frames[peak_idx]
                attack_frames = 0
                
                for i in range(min(peak_idx, len(env_frames))):
                    if env_frames[peak_idx - i] < threshold:
                        attack_frames = i
                        break
                
                attack_time = attack_frames * hop_length / sr
                features['attack_time'] = float(attack_time)
                
                # Check for transient (fast attack)
                features['has_transient'] = bool(attack_time < 0.05)
                
                # Check for sustain
                if peak_idx < len(env_frames) - 1:
                    late_energy = np.mean(env_frames[int(len(env_frames)*0.7):])
                    early_energy = np.mean(env_frames[int(len(env_frames)*0.1):int(len(env_frames)*0.3)])
                    is_sustained = late_energy > (0.5 * early_energy)
                    features['is_sustained'] = bool(is_sustained)
                
                print(f"  Extracted envelope features")
            else:
                features['attack_time'] = 0
                features['has_transient'] = False
                features['is_sustained'] = False
        except Exception as e:
            print(f"  Warning: Error extracting envelope features: {e}")
            features['attack_time'] = 0
            features['has_transient'] = False
            features['is_sustained'] = False
        
        # Frequency band analysis
        try:
            # Get frequency bands
            spec = np.abs(librosa.stft(y))
            
            # Define frequency bands
            freqs = librosa.fft_frequencies(sr=sr)
            
            # Get indices for frequency bands
            def get_band_indices(low, high, freqs):
                return np.where((freqs >= low) & (freqs < high))[0]
            
            sub_bass_idx = get_band_indices(20, 60, freqs)
            bass_idx = get_band_indices(60, 250, freqs)
            low_mid_idx = get_band_indices(250, 500, freqs)
            mid_idx = get_band_indices(500, 2000, freqs)
            upper_mid_idx = get_band_indices(2000, 4000, freqs)
            high_idx = get_band_indices(4000, 20000, freqs)
            
            # Calculate energy in each band
            total_energy = np.sum(spec)
            
            if total_energy > 0:
                sub_bass_energy = np.sum(spec[:, sub_bass_idx]) if len(sub_bass_idx) > 0 else 0
                bass_energy = np.sum(spec[:, bass_idx]) if len(bass_idx) > 0 else 0
                low_mid_energy = np.sum(spec[:, low_mid_idx]) if len(low_mid_idx) > 0 else 0
                mid_energy = np.sum(spec[:, mid_idx]) if len(mid_idx) > 0 else 0
                upper_mid_energy = np.sum(spec[:, upper_mid_idx]) if len(upper_mid_idx) > 0 else 0 
                high_energy = np.sum(spec[:, high_idx]) if len(high_idx) > 0 else 0
                
                features['sub_bass_ratio'] = float(sub_bass_energy / total_energy)
                features['bass_ratio'] = float(bass_energy / total_energy)
                features['low_mid_ratio'] = float(low_mid_energy / total_energy)
                features['mid_ratio'] = float(mid_energy / total_energy)
                features['upper_mid_ratio'] = float(upper_mid_energy / total_energy)
                features['high_ratio'] = float(high_energy / total_energy)
                
                print(f"  Extracted frequency band features")
            else:
                features['sub_bass_ratio'] = 0.0
                features['bass_ratio'] = 0.0 
                features['low_mid_ratio'] = 0.0
                features['mid_ratio'] = 0.0
                features['upper_mid_ratio'] = 0.0
                features['high_ratio'] = 0.0
        except Exception as e:
            print(f"  Warning: Error extracting frequency band features: {e}")
        
        # Zero crossing rate (noisiness/harshness)
        try:
            zcr = librosa.feature.zero_crossing_rate(y)[0]
            features['avg_zcr'] = float(np.mean(zcr))
            print(f"  Extracted ZCR features")
        except Exception as e:
            print(f"  Warning: Error extracting ZCR features: {e}")
        
        # Additional features for mood classification
        try:
            # Harmonic-percussive source separation for additional features
            y_harmonic, y_percussive = librosa.effects.hpss(y)
            
            # Harmonic to percussive ratio
            harmonic_energy = np.sum(y_harmonic**2)
            percussive_energy = np.sum(y_percussive**2)
            if percussive_energy > 0:
                features['harmonic_percussive_ratio'] = float(harmonic_energy / percussive_energy)
            else:
                features['harmonic_percussive_ratio'] = float(1.0)
            
            # Roughness approximation using spectral contrast
            if 'avg_contrast' in features:
                features['roughness'] = float(1.0 - features['avg_contrast'])
            
            print(f"  Extracted additional mood features")
        except Exception as e:
            print(f"  Warning: Error extracting additional mood features: {e}")
        
        # Print summary of extracted features
        print(f"  Successfully extracted {len(features)} features")
        
        return features
    
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        import traceback
        traceback.print_exc()
        return None

def classify_by_filename(file_path):
    """Classify audio sample based on filename"""
    filename = os.path.basename(file_path).lower()
    
    # Traditional sample categories
    classification = {
        'type': 'other',
        'subtype': 'other'
    }
    
    # Percussion
    if any(word in filename for word in ['kick', 'bass drum', 'bd', '808']):
        classification['type'] = 'percussion'
        classification['subtype'] = 'kick'
    elif any(word in filename for word in ['snare', 'sd']):
        classification['type'] = 'percussion'
        classification['subtype'] = 'snare'
    elif any(word in filename for word in ['hat', 'hh', 'hi-hat', 'hihat', 'cymbal', 'crash', 'ride']):
        classification['type'] = 'percussion'
        classification['subtype'] = 'hi_hat_cymbal'
    elif any(word in filename for word in ['tom', 'floor', 'rack']):
        classification['type'] = 'percussion'
        classification['subtype'] = 'tom'
    elif any(word in filename for word in ['clap', 'handclap']):
        classification['type'] = 'percussion'
        classification['subtype'] = 'clap'
    elif any(word in filename for word in ['perc', 'drum', 'percussion']):
        classification['type'] = 'percussion'
        classification['subtype'] = 'other_percussion'
    
    # Bass
    elif any(word in filename for word in ['808']):
        classification['type'] = 'bass'
        classification['subtype'] = '808_bass'
    elif any(word in filename for word in ['bass', 'sub']):
        classification['type'] = 'bass'
        classification['subtype'] = 'other_bass'
    
    # Strings/Pads
    elif any(word in filename for word in ['pad', 'string', 'strings', 'ambient', 'atmo', 'atmosphere', 'chord']):
        classification['type'] = 'pad'
        classification['subtype'] = 'strings_pad'
    
    # Leads/Synths
    elif any(word in filename for word in ['lead', 'synth', 'melody', 'arp', 'pluck']):
        classification['type'] = 'lead'
        classification['subtype'] = 'synth_lead'
    
    # FX
    elif any(word in filename for word in ['fx', 'effect', 'glitch', 'transition', 'riser', 'sweep', 'impact', 'whoosh']):
        classification['type'] = 'fx'
        classification['subtype'] = 'effect'
    
    # Vocals
    elif any(word in filename for word in ['vocal', 'vox', 'voice']):
        classification['type'] = 'vocal'
        classification['subtype'] = 'vocal'
    
    # Try to extract mood hints from filename
    mood_words = {
        'aggressive': ['aggressive', 'hard', 'distort', 'heavy', 'intense', 'angry', 'rage', 'fierce', 'monster', 'beast'],
        'chill': ['chill', 'calm', 'relax', 'ambient', 'smooth', 'gentle', 'soft', 'mellow'],
        'dark': ['dark', 'horror', 'scary', 'creepy', 'spooky', 'gloomy', 'tension', 'evil', 'cinematic'],
        'bright': ['bright', 'happy', 'upbeat', 'uplifting', 'joyful', 'cheerful', 'light', 'shine', 'vivid'],
        'sad': ['sad', 'melancholic', 'emotional', 'moody', 'sorrow', 'blue', 'longing', 'nostalgic'],
        'epic': ['epic', 'cinematic', 'dramatic', 'grand', 'powerful', 'massive', 'huge', 'impact'],
        'funky': ['funk', 'funky', 'groovy', 'disco', 'retro', 'dance'],
        'ethereal': ['ethereal', 'dreamy', 'floating', 'atmospheric', 'space', 'cosmic', 'heaven']
    }
    
    # Check for genre hints in filename
    genre_words = {
        'electronic': ['edm', 'electronic', 'techno', 'house', 'dance', 'trance', 'dubstep', 'glitch'],
        'hiphop': ['hip', 'hop', 'trap', 'rap', 'gangsta', 'dirty', 'south'],
        'pop': ['pop', 'commercial', 'radio', 'chart', 'hit'],
        'rock': ['rock', 'band', 'guitar', 'grunge', 'metal', 'alternative'],
        'jazz': ['jazz', 'blues', 'swing', 'brass'],
        'cinematic': ['cinematic', 'score', 'soundtrack', 'film', 'movie', 'trailer', 'epic']
    }
    
    # Extract mood hints
    for mood, keywords in mood_words.items():
        if any(word in filename for word in keywords):
            classification['mood_hint'] = mood
            break
    
    # Extract genre hints
    for genre, keywords in genre_words.items():
        if any(word in filename for word in keywords):
            classification['genre_hint'] = genre
            break
    
    return classification

def classify_by_traditional_categories(features):
    """Traditional classification by instrument/sound type"""
    if features is None or 'duration' not in features:
        return {'type': 'other', 'subtype': 'other'}
    
    # Classification dictionary
    classification = {
        'type': 'other',
        'subtype': 'other'
    }
    
    # Check if we have enough features for classification
    has_sufficient_features = (
        'avg_centroid' in features and 
        'energy_mean' in features and
        'bass_ratio' in features and 
        'mid_ratio' in features and 
        'high_ratio' in features
    )
    
    if not has_sufficient_features:
        return classification
    
    # Percussion classification
    if ('has_transient' in features and features['has_transient'] and 
        'onset_rate' in features and features['onset_rate'] > 1.0):
        classification['type'] = 'percussion'
        
        # Percussion subtypes
        if features['bass_ratio'] > 0.4 and features['avg_centroid'] < 500:
            classification['subtype'] = 'kick'
        elif features['mid_ratio'] > 0.4 and features.get('attack_time', 1.0) < 0.05:
            classification['subtype'] = 'snare'
        elif features['high_ratio'] > 0.4 and features['avg_centroid'] > 5000:
            classification['subtype'] = 'hi_hat_cymbal'
        else:
            classification['subtype'] = 'other_percussion'
    
    # Bass classification
    elif features['bass_ratio'] > 0.5 and features['avg_centroid'] < 500:
        classification['type'] = 'bass'
        
        # Bass subtypes
        if features.get('is_sustained', False) and features['duration'] > 0.8:
            classification['subtype'] = '808_bass'
        else:
            classification['subtype'] = 'other_bass'
    
    # Pad classification
    elif features.get('is_sustained', False) and features['duration'] > 1.5 and features.get('avg_zcr', 1.0) < 0.2:
        classification['type'] = 'pad'
        classification['subtype'] = 'strings_pad'
    
    # Lead classification
    elif features['mid_ratio'] > 0.4 and features['upper_mid_ratio'] > 0.2:
        classification['type'] = 'lead'
        classification['subtype'] = 'synth_lead'
    
    # FX classification
    elif (features.get('avg_flatness', 0) > 0.3 or 
          features.get('avg_zcr', 0) > 0.3 or 
          features['high_ratio'] > 0.5):
        classification['type'] = 'fx'
        classification['subtype'] = 'effect'
    
    return classification

def classify_by_mood(features):
    """Classify by mood characteristics (aggressive, chill, dark, bright, etc.)"""
    if features is None or 'duration' not in features:
        return {}
    
    mood = {}
    
    # ENERGY LEVEL (Aggressive vs Chill)
    # Base energy score on multiple factors
    energy_score = 0
    energy_count = 0
    
    # Energy mean (0-1)
    if 'energy_mean' in features:
        energy_score += features['energy_mean'] * 10  # Scale up for impact
        energy_count += 1
    
    # Dynamic range contributes to perceived energy
    if 'energy_dynamic_range' in features:
        energy_score += min(features['energy_dynamic_range'], 5)
        energy_count += 1
    
    # Attack time (fast attacks = more aggressive)
    if 'attack_time' in features:
        # Inverse relationship: shorter attack = higher energy score
        attack_factor = max(0, 1 - (features['attack_time'] * 20))  # Scale to make small differences matter
        energy_score += attack_factor * 3
        energy_count += 1
    
    # Onset rate (more onsets = more energetic)
    if 'onset_rate' in features:
        energy_score += min(features['onset_rate'], 5)
        energy_count += 1
    
    # Zero crossing rate (noisy = more aggressive)
    if 'avg_zcr' in features:
        energy_score += features['avg_zcr'] * 30  # Scale up for impact
        energy_count += 1
    
    # Spectral centroid (brightness contributes to perceived energy)
    if 'avg_centroid' in features:
        # Normalize to 0-1 range (assuming 10kHz is very bright)
        centroid_factor = min(features['avg_centroid'] / 10000, 1)
        energy_score += centroid_factor * 3
        energy_count += 1
    
    # Normalize energy score to 0-10 scale
    if energy_count > 0:
        normalized_energy = min(energy_score / energy_count, 10)
    else:
        normalized_energy = 5  # Default mid-level energy
    
    # Convert to qualitative descriptions
    if normalized_energy > 7.5:
        mood['energy'] = 'aggressive'
    elif normalized_energy > 5:
        mood['energy'] = 'energetic'
    elif normalized_energy > 2.5:
        mood['energy'] = 'moderate'
    else:
        mood['energy'] = 'chill'
    
    # Store numerical value for reference
    mood['energy_value'] = round(normalized_energy, 2)
    
    # BRIGHTNESS (Dark vs Bright)
    brightness_score = 0
    brightness_count = 0
    
    # Spectral centroid is the primary indicator of brightness
    if 'avg_centroid' in features:
        # Map centroid to 0-10 scale (0-10kHz range)
        brightness_score += min(features['avg_centroid'] / 1000, 10)
        brightness_count += 1
    
    # High frequency content contributes to brightness
    if 'high_ratio' in features and 'upper_mid_ratio' in features:
        brightness_score += (features['high_ratio'] + features['upper_mid_ratio']) * 10
        brightness_count += 1
    
    # Low frequency content reduces brightness
    if 'bass_ratio' in features and 'sub_bass_ratio' in features:
        brightness_score -= (features['bass_ratio'] + features['sub_bass_ratio']) * 5
        brightness_count += 1
    
    # Normalize brightness score to 0-10
    if brightness_count > 0:
        normalized_brightness = max(min(brightness_score / brightness_count, 10), 0)
    else:
        normalized_brightness = 5  # Default mid-level brightness
    
    # Convert to qualitative descriptions
    if normalized_brightness > 7.5:
        mood['brightness'] = 'bright'
    elif normalized_brightness > 5:
        mood['brightness'] = 'balanced'
    elif normalized_brightness > 2.5:
        mood['brightness'] = 'warm'
    else:
        mood['brightness'] = 'dark'
    
    # Store numerical value for reference
    mood['brightness_value'] = round(normalized_brightness, 2)
    
    # TEXTURE (Smooth vs Rough)
    texture_score = 0
    texture_count = 0
    
    # Flatness is a key indicator (inverse relationship to roughness)
    if 'avg_flatness' in features:
        texture_score += (1 - features['avg_flatness']) * 5
        texture_count += 1
    
    # Zero crossing rate contributes to roughness
    if 'avg_zcr' in features:
        texture_score += features['avg_zcr'] * 20
        texture_count += 1
    
    # Roughness directly relates to texture
    if 'roughness' in features:
        texture_score += features['roughness'] * 10
        texture_count += 1
    
    # Normalize texture score to 0-10
    if texture_count > 0:
        normalized_texture = min(texture_score / texture_count, 10)
    else:
        normalized_texture = 5  # Default mid-level texture
    
    # Convert to qualitative descriptions
    if normalized_texture > 7.5:
        mood['texture'] = 'rough'
    elif normalized_texture > 5:
        mood['texture'] = 'textured'
    elif normalized_texture > 2.5:
        mood['texture'] = 'balanced'
    else:
        mood['texture'] = 'smooth'
    
    # Store numerical value for reference
    mood['texture_value'] = round(normalized_texture, 2)
    
    # WEIGHT (Heavy vs Light)
    weight_score = 0
    weight_count = 0
    
    # Low frequency content contributes to heaviness
    if 'bass_ratio' in features and 'sub_bass_ratio' in features:
        weight_score += (features['bass_ratio'] + features['sub_bass_ratio'] * 2) * 10
        weight_count += 1
    
    # High energy contributes to perceived weight
    if 'energy_mean' in features:
        weight_score += features['energy_mean'] * 5
        weight_count += 1
    
    # Sustain contributes to weight
    if 'is_sustained' in features:
        if features['is_sustained']:
            weight_score += 3
        weight_count += 1
    
    # Normalize weight score to 0-10
    if weight_count > 0:
        normalized_weight = min(weight_score / weight_count, 10)
    else:
        normalized_weight = 5  # Default mid-level weight
    
    # Convert to qualitative descriptions
    if normalized_weight > 7.5:
        mood['weight'] = 'heavy'
    elif normalized_weight > 5:
        mood['weight'] = 'solid'
    elif normalized_weight > 2.5:
        mood['weight'] = 'balanced'
    else:
        mood['weight'] = 'light'
    
    # Store numerical value for reference
    mood['weight_value'] = round(normalized_weight, 2)
    
    # OVERALL MOOD
    # Combine factors to determine overall mood labels
    
    mood_labels = []
    
    # Aggressive sound
    if mood.get('energy') == 'aggressive' and mood.get('texture', '') in ['rough', 'textured']:
        mood_labels.append('aggressive')
    
    # Chill sound
    if mood.get('energy') in ['chill', 'moderate'] and mood.get('texture', '') in ['smooth', 'balanced']:
        mood_labels.append('chill')
    
    # Dark sound
    if mood.get('brightness') in ['dark', 'warm'] and normalized_brightness < 4:
        mood_labels.append('dark')
    
    # Bright sound
    if mood.get('brightness') == 'bright' and normalized_brightness > 6:
        mood_labels.append('bright')
    
    # Heavy sound
    if mood.get('weight') == 'heavy' and normalized_weight > 7:
        mood_labels.append('heavy')
    
    # Ethereal sound
    if (mood.get('energy') == 'chill' and 
        mood.get('texture', '') in ['smooth', 'balanced'] and 
        mood.get('brightness', '') in ['bright', 'balanced']):
        mood_labels.append('ethereal')
    
    # Epic sound
    if (mood.get('energy', '') in ['energetic', 'aggressive'] and 
        mood.get('weight', '') in ['heavy', 'solid'] and 
        features.get('duration', 0) > 2.0):
        mood_labels.append('epic')
    
    # Sad sound
    if (mood.get('energy') == 'chill' and 
        mood.get('brightness', '') in ['dark', 'warm'] and
        normalized_brightness < 3.5):
        mood_labels.append('sad')
    
    # Tense sound
    if 'avg_zcr' in features and features['avg_zcr'] > 0.2 and mood.get('brightness') in ['dark', 'warm']:
        mood_labels.append('tense')
    
    # If we have no mood labels yet, create a fallback
    if not mood_labels:
        if normalized_energy > 5:
            if normalized_brightness > 5:
                mood_labels.append('vibrant')
            else:
                mood_labels.append('intense')
        else:
            if normalized_brightness > 5:
                mood_labels.append('airy')
            else:
                mood_labels.append('reserved')
    
    mood['overall_mood'] = mood_labels
    
    return mood

def classify_by_production_use(features):
    """Classify by how the sound would be used in production"""
    if features is None or 'duration' not in features:
        return {}
    
    production_use = {}
    
    # Sample type based on length and characteristics
    if features['duration'] < 0.5 and features.get('has_transient', False):
        production_use['sample_type'] = 'one_shot'
    elif features['duration'] > 1.0 and features.get('is_sustained', False):
        production_use['sample_type'] = 'atmosphere'
    elif features['duration'] > 2.0 and features.get('tempo', 0) > 20:
        production_use['sample_type'] = 'loop'
    else:
        production_use['sample_type'] = 'element'
    
    # Determine mix position
    if 'bass_ratio' in features and features['bass_ratio'] > 0.5:
        production_use['mix_position'] = 'foundation'
    elif 'mid_ratio' in features and features['mid_ratio'] > 0.5:
        production_use['mix_position'] = 'center'
    elif 'high_ratio' in features and features['high_ratio'] > 0.4:
        production_use['mix_position'] = 'top'
    else:
        production_use['mix_position'] = 'flexible'
    
    # Determine starting point hint
    if features.get('has_transient', False) and features['duration'] < 0.5:
        production_use['starting_point'] = 'rhythmic_element'
    elif features.get('is_sustained', False) and features['duration'] > 2.0:
        production_use['starting_point'] = 'background'
    elif 'high_ratio' in features and 'mid_ratio' in features and features['high_ratio'] + features['mid_ratio'] > 0.7:
        production_use['starting_point'] = 'accent'
    else:
        production_use['starting_point'] = 'building_block'
    
    return production_use

def analyze_and_classify_sample(file_path, classification_types=['traditional', 'mood']):
    """Analyze and classify an audio sample using multiple approaches"""
    print(f"Processing: {os.path.basename(file_path)}")
    
    # Extract audio features
    features = extract_audio_features(file_path)
    
    # Initialize complete classification dictionary
    all_classifications = {}
    
    # Always include filename-based classification as backup
    filename_classification = classify_by_filename(file_path)
    
    # Initialize core 'type' and 'subtype' from filename or set to 'other'
    classification = {}
    if filename_classification['type'] != 'other':
        classification['type'] = filename_classification['type']
        classification['subtype'] = filename_classification['subtype']
        method = "filename"
    else:
        classification['type'] = 'other'
        classification['subtype'] = 'other'
        method = "default"
    
    # Add mood hint from filename if available
    if 'mood_hint' in filename_classification:
        classification['mood_hint'] = filename_classification['mood_hint']
    
    # Add genre hint from filename if available
    if 'genre_hint' in filename_classification:
        classification['genre_hint'] = filename_classification['genre_hint']
    
    # Apply all requested classification types
    for class_type in classification_types:
        if class_type == 'traditional' and features is not None:
            trad_classification = classify_by_traditional_categories(features)
            if trad_classification['type'] != 'other' and classification['type'] == 'other':
                classification['type'] = trad_classification['type']
                classification['subtype'] = trad_classification['subtype']
                method = "audio_features"
            all_classifications['traditional'] = trad_classification
        
        if class_type == 'mood' and features is not None:
            mood_classification = classify_by_mood(features)
            if mood_classification:  # Only add if non-empty
                all_classifications['mood'] = mood_classification
        
        if class_type == 'production_use' and features is not None:
            production_classification = classify_by_production_use(features)
            if production_classification:  # Only add if non-empty
                all_classifications['production_use'] = production_classification
    
    # Add duration classification
    if features is not None and features.get('duration', 0) > 0:
        if features['duration'] < 0.15:
            classification['duration'] = 'very_short'
        elif features['duration'] < 0.5:
            classification['duration'] = 'short'
        elif features['duration'] < 2.0:
            classification['duration'] = 'medium'
        elif features['duration'] < 8.0:
            classification['duration'] = 'long'
        else:
            classification['duration'] = 'very_long'
        
        # Add flattened classifications for easier access
        for class_type, class_dict in all_classifications.items():
            for key, value in class_dict.items():
                # Handle special case for overall_mood which is a list
                if key == 'overall_mood' and isinstance(value, list):
                    # Add each mood as a separate key for easier searching
                    for i, mood in enumerate(value):
                        classification[f"mood_{i+1}"] = mood
                    # Keep the original list for reference
                    classification[f"{class_type}_{key}"] = value
                elif key != 'type' and key != 'subtype':  # Avoid overwriting primary type/subtype
                    classification[f"{class_type}_{key}"] = value
    else:
        classification['duration'] = 'unknown'
    
    # Print results
    print(f"\nClassification results for: {os.path.basename(file_path)}")
    print(f"  Primary classification method: {method}")
    print(f"  Type: {classification['type']}")
    print(f"  Subtype: {classification['subtype']}")
    print(f"  Duration: {classification['duration']}")
    
    # Print mood classification if available
    if 'mood' in all_classifications:
        print("\n  Mood Classification:")
        if 'overall_mood' in all_classifications['mood']:
            print(f"    Overall mood: {', '.join(all_classifications['mood']['overall_mood'])}")
        for key, value in all_classifications['mood'].items():
            if key != 'overall_mood' and not key.endswith('_value'):
                print(f"    {key}: {value}")
    
    # Print other classifications if available
    for class_type in [t for t in classification_types if t not in ['traditional', 'mood']]:
        if class_type in all_classifications and all_classifications[class_type]:
            print(f"\n  {class_type.capitalize().replace('_', ' ')} Classification:")
            for key, value in all_classifications[class_type].items():
                print(f"    {key}: {value}")
    
    # Print extracted features (just a few key ones)
    if features is not None and features.get('duration', 0) > 0:
        print("\n  Key Audio Features:")
        # Print just a few key features
        key_features = ['duration', 'energy_mean', 'avg_centroid', 'avg_flatness', 'tempo', 'onset_rate']
        for feature in key_features:
            if feature in features:
                if isinstance(features[feature], float):
                    print(f"    {feature}: {features[feature]:.4f}")
                else:
                    print(f"    {feature}: {features[feature]}")
    
    return classification, features, all_classifications

def organize_samples(input_dir, output_dir, classification_types=['traditional', 'mood'], organize_by='type', copy_mode='copy'):
    """Organize samples into folders based on analysis"""
    audio_files = list_audio_files(input_dir)
    
    if not audio_files:
        print(f"No audio files found in {input_dir}")
        return
    
    print(f"Found {len(audio_files)} audio files for analysis")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Keep track of classifications and features
    all_data = {}
    
    # Analyze and categorize each file
    for file_path in audio_files:
        # Analyze and classify the sample
        classification, features, all_classifications = analyze_and_classify_sample(file_path, classification_types)
        
        # Store results
        filename = os.path.basename(file_path)
        all_data[filename] = {
            'classification': classification,
            'features': features,
            'all_classifications': all_classifications
        }
        
        # Determine destination folder based on organization method
        dest_folder = output_dir
        
        # Handle mood organization specially
        if organize_by.startswith('mood_'):
            try:
                mood_index = int(organize_by.split('_')[1])
                if f"mood_{mood_index}" in classification:
                    mood_category = classification[f"mood_{mood_index}"]
                    dest_folder = os.path.join(output_dir, "mood", mood_category)
                else:
                    dest_folder = os.path.join(output_dir, "mood", "uncategorized")
            except (ValueError, IndexError):
                # Handle mood organization by overall_mood
                if 'mood' in all_classifications and 'overall_mood' in all_classifications['mood']:
                    if all_classifications['mood']['overall_mood']:
                        # Use the first mood in the list
                        mood_category = all_classifications['mood']['overall_mood'][0]
                        dest_folder = os.path.join(output_dir, "mood", mood_category)
                    else:
                        dest_folder = os.path.join(output_dir, "mood", "uncategorized")
                else:
                    dest_folder = os.path.join(output_dir, classification['type'])
        # Check if the organize_by contains an underscore (e.g., 'mood_energy')
        elif '_' in organize_by:
            class_type, attribute = organize_by.split('_', 1)
            if (class_type in all_classifications and 
                attribute in all_classifications[class_type]):
                # Get the category from the specified classification type
                category = all_classifications[class_type][attribute]
                dest_folder = os.path.join(output_dir, attribute, str(category))
            elif organize_by in classification:
                # Direct match to a flattened classification key
                dest_folder = os.path.join(output_dir, organize_by, str(classification[organize_by]))
            else:
                # Fallback to type
                dest_folder = os.path.join(output_dir, classification['type'])
        else:
            # Traditional organization methods
            if organize_by in classification:
                main_category = classification[organize_by]
                
                # If organizing by type and subtype is available, use it for further organization
                if organize_by == 'type' and 'subtype' in classification:
                    dest_folder = os.path.join(output_dir, main_category, classification['subtype'])
                else:
                    dest_folder = os.path.join(output_dir, main_category)
            else:
                # Fallback to type
                dest_folder = os.path.join(output_dir, classification['type'])
        
        # Create the destination folder if it doesn't exist
        os.makedirs(dest_folder, exist_ok=True)
        
        # Copy or move the file to the destination
        dest_file = os.path.join(dest_folder, filename)
        if copy_mode == 'copy':
            shutil.copy2(file_path, dest_file)
            print(f"  Copied to: {dest_folder}")
        else:  # move mode
            shutil.move(file_path, dest_file)
            print(f"  Moved to: {dest_folder}")
    
    # Generate classification report
    report_path = os.path.join(output_dir, "sample_classification_report.txt")
    with open(report_path, 'w') as f:
        f.write("Sample Classification Report\n")
        f.write("=========================\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Classification types used: {', '.join(classification_types)}\n\n")
        
        for filename, data in all_data.items():
            f.write(f"File: {filename}\n")
            f.write("Primary Classification:\n")
            for category, value in data['classification'].items():
                f.write(f"  {category}: {value}\n")
            
            f.write("\nDetailed Classifications:\n")
            for class_type, class_dict in data['all_classifications'].items():
                f.write(f"  {class_type.capitalize()}:\n")
                for key, value in class_dict.items():
                    if isinstance(value, list):
                        f.write(f"    {key}: {', '.join(str(v) for v in value)}\n")
                    else:
                        f.write(f"    {key}: {value}\n")
            f.write("\n" + "="*50 + "\n\n")
    
    # Generate JSON report (for local LLM access)
    json_report_path = os.path.join(output_dir, "sample_classification_data.json")
    with open(json_report_path, 'w') as f:
        json_data = {}
        for filename, data in all_data.items():
            json_data[filename] = {
                'classification': data['classification'],
                'all_classifications': data['all_classifications']
            }
            # Include selected features but not all (some might not be serializable)
            if data['features']:
                safe_features = {}
                for key, value in data['features'].items():
                    if isinstance(value, (int, float, bool, str)) or value is None:
                        safe_features[key] = value
                json_data[filename]['features'] = safe_features
        
        json.dump(json_data, f, indent=2)
    
    # Generate CSV feature report
    if any(data['features'] for data in all_data.values()):
        feature_report_path = os.path.join(output_dir, "sample_features.csv")
        with open(feature_report_path, 'w', newline='') as f:
            # Get all unique feature names
            feature_names = set()
            for data in all_data.values():
                if data['features']:
                    feature_names.update(k for k, v in data['features'].items() 
                                        if isinstance(v, (int, float, bool, str)))
            
            # Sort feature names for consistent ordering
            feature_names = sorted(feature_names)
            
            # Write CSV header
            writer = csv.writer(f)
            writer.writerow(['Filename'] + list(feature_names))
            
            # Write each file's features
            for filename, data in all_data.items():
                row = [filename]
                if data['features']:
                    for feature in feature_names:
                        value = data['features'].get(feature, "")
                        if isinstance(value, (int, float, bool, str)):
                            row.append(value)
                        else:
                            row.append("")
                else:
                    row.extend([""] * len(feature_names))
                writer.writerow(row)
        
        print(f"\nFeature data saved to: {feature_report_path}")
    
    print(f"\nClassification report saved to: {report_path}")
    print(f"JSON data for LLM access saved to: {json_report_path}")
    return all_data

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Librosa-based Audio Sample Classifier with Mood Detection")
    parser.add_argument("--input", type=str, default="input", help="Input directory containing audio samples")
    parser.add_argument("--output", type=str, default="output", help="Output directory for organized samples")
    parser.add_argument("--classification-types", type=str, nargs='+', 
                        default=['traditional', 'mood'], 
                        choices=['traditional', 'mood', 'production_use', 'all'],
                        help="Classification approaches to use")
    parser.add_argument("--organize-by", type=str, default="type", 
                        help="Method for organizing samples (e.g., 'type', 'mood_energy', 'mood_1')")
    parser.add_argument("--mode", type=str, default="copy", 
                        choices=["copy", "move"],
                        help="Whether to copy or move files")
    args = parser.parse_args()
    
    # Handle 'all' classification type
    if 'all' in args.classification_types:
        classification_types = ['traditional', 'mood', 'production_use']
    else:
        classification_types = args.classification_types
    
    print(f"Organizing samples from {args.input} into {args.output}")
    print(f"Using classification types: {', '.join(classification_types)}")
    print(f"Organizing by: {args.organize_by}")
    
    organize_samples(args.input, args.output, classification_types, args.organize_by, args.mode)
    print("\nSample organization complete!")

if __name__ == "__main__":
    main()

'''
# Basic usage with default settings
python librosa_classifier.py --input input --output organized_samples

# Using all classification types
python librosa_classifier.py --input input --output organized_samples --classification-types all

# Organize by mood categories
python librosa_classifier.py --input input --output mood_organized --organize-by mood_1

# Organize by energy level
python librosa_classifier.py --input input --output energy_organized --organize-by mood_energy
'''