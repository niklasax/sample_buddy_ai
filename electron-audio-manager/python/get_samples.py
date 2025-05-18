#!/usr/bin/env python
"""
Get Samples Script
-----------------
This script scans a directory for audio samples and returns their metadata as JSON.
It's used by the Electron Audio Sample Manager application.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any

# Set up logging with more detailed output
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_samples(directory: str) -> Dict[str, Any]:
    """
    Scan a directory for audio samples and return their metadata.
    
    Args:
        directory: Directory to scan for audio samples
        
    Returns:
        Dictionary with sample information
    """
    if not os.path.exists(directory):
        logger.warning(f"Directory not found: {directory}")
        
        # Try to find the samples directory in alternative locations
        possible_directories = [
            os.path.join(os.getcwd(), "processed_samples", "organized-samples"),
            os.path.join(os.getcwd(), "processed_samples"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "processed_samples", "organized-samples"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "processed_samples", "organized-samples")
        ]
        
        found_dir = None
        for possible_dir in possible_directories:
            if os.path.exists(possible_dir):
                logger.info(f"Found alternative samples directory: {possible_dir}")
                found_dir = possible_dir
                break
        
        if found_dir:
            directory = found_dir
        else:
            return {'success': False, 'error': f"Could not find samples directory. Tried: {directory} and alternatives", 'samples': []}
    
    logger.info(f"Scanning directory: {directory}")
    samples = []
    
    # Check if this is the organized-samples directory
    organized_dir = directory
    if os.path.basename(directory) != "organized-samples" and os.path.exists(os.path.join(directory, "organized-samples")):
        organized_dir = os.path.join(directory, "organized-samples")
        logger.info(f"Found organized-samples directory: {organized_dir}")
    
    # Scan the category folders in the organized directory
    if os.path.exists(organized_dir):
        logger.debug(f"Organized directory exists at: {organized_dir}")
        
        # Print all contents of the organized directory for debugging
        try:
            dir_contents = os.listdir(organized_dir)
            logger.debug(f"Contents of {organized_dir}: {dir_contents}")
        except Exception as e:
            logger.error(f"Error listing contents of {organized_dir}: {str(e)}")
        
        for category_folder in os.listdir(organized_dir):
            category_path = os.path.join(organized_dir, category_folder)
            
            # Skip files, only look at directories
            if not os.path.isdir(category_path) or category_folder.startswith('.'):
                logger.debug(f"Skipping {category_folder} - not a directory or hidden")
                continue
            
            # This is a category folder, get all audio files directly in it
            logger.info(f"Scanning category folder: {category_folder} at {category_path}")
            
            # Print all contents of the category directory for debugging
            try:
                category_contents = os.listdir(category_path)
                logger.debug(f"Contents of {category_path}: {category_contents}")
            except Exception as e:
                logger.error(f"Error listing contents of {category_path}: {str(e)}")
            
            for file_name in os.listdir(category_path):
                logger.debug(f"Checking file: {file_name}")
                if is_audio_file(file_name):
                    file_path = os.path.join(category_path, file_name)
                    logger.debug(f"Found audio file: {file_path}")
                    
                    # Verify the file exists and has content
                    if os.path.exists(file_path):
                        try:
                            file_size = os.path.getsize(file_path)
                            logger.debug(f"File size of {file_path}: {file_size} bytes")
                        except Exception as e:
                            logger.warning(f"Error checking file size of {file_path}: {str(e)}")
                    else:
                        logger.warning(f"File path does not exist: {file_path}")
                        continue
                        
                    sample_id = f"sample_{os.path.splitext(file_name)[0].replace(' ', '_').lower()}"
                    
                    # Check if there's a matching JSON file with metadata
                    json_file = os.path.join(category_path, f"{os.path.splitext(file_name)[0]}.json")
                    logger.debug(f"Looking for JSON metadata at: {json_file}")
                    
                    mood = "neutral"  # Default mood
                    subtype = ""
                    
                    if os.path.exists(json_file):
                        logger.debug(f"Found JSON metadata file: {json_file}")
                        try:
                            with open(json_file, 'r') as f:
                                metadata = json.load(f)
                                if 'mood' in metadata:
                                    mood = metadata['mood']
                                    logger.debug(f"Extracted mood: {mood}")
                                if 'subtype' in metadata:
                                    subtype = metadata['subtype']
                                    logger.debug(f"Extracted subtype: {subtype}")
                        except Exception as e:
                            logger.warning(f"Error loading JSON metadata for {file_name}: {str(e)}")
                    else:
                        logger.debug(f"No JSON metadata file found at {json_file}")
                    
                    sample = {
                        'id': sample_id,
                        'name': file_name,
                        'path': file_path,
                        'category': category_folder,
                        'subtype': subtype,
                        'mood': mood
                    }
                    
                    logger.info(f"Adding sample: {sample['name']} ({sample['category']}/{sample['mood']})")
                    samples.append(sample)
                else:
                    logger.debug(f"Skipping non-audio file: {file_name}")
    
    # If no samples found in the category structure, check if there are audio files directly
    if not samples:
        logger.info("No samples found in category structure, checking for direct audio files")
        for file_name in os.listdir(directory):
            if is_audio_file(file_name):
                file_path = os.path.join(directory, file_name)
                sample_id = f"sample_{os.path.splitext(file_name)[0].replace(' ', '_').lower()}"
                
                # Try to guess category from filename
                category = guess_category(file_name)
                
                sample = {
                    'id': sample_id,
                    'name': file_name,
                    'path': file_path,
                    'category': category,
                    'mood': 'neutral'
                }
                
                samples.append(sample)
    
    logger.info(f"Found {len(samples)} samples")
    return {'success': True, 'samples': samples}

def is_audio_file(filename: str) -> bool:
    """Check if a file is an audio file based on extension."""
    valid_extensions = ('.wav', '.mp3', '.ogg', '.flac', '.aif', '.aiff')
    return filename.lower().endswith(valid_extensions)

def guess_category(filename: str) -> str:
    """Guess instrument category from filename."""
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

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python get_samples.py <directory>")
        sys.exit(1)
    
    try:
        directory = sys.argv[1]
        result = get_samples(directory)
        print(json.dumps(result))
    except Exception as e:
        error_result = {'success': False, 'error': str(e), 'samples': []}
        print(json.dumps(error_result))
        sys.exit(1)