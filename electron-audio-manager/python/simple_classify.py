#!/usr/bin/env python
"""
Simplified Audio Sample Classifier
---------------------------------
A lightweight version of the classifier for testing
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def simple_process(input_files: List[str], output_dir: str) -> Dict[str, Any]:
    """
    A simplified processing function that doesn't use heavy audio processing
    """
    logger.info(f"Processing {len(input_files)} audio files")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Process each file (just metadata, no actual audio processing)
    samples = {}
    for file_path in input_files:
        try:
            # Simple ID generation based on filename
            filename = os.path.basename(file_path)
            sample_id = f"sample_{filename.replace('.', '_')}"
            
            logger.info(f"Processing file: {filename}")
            
            # Use simple classification based on the filename
            category = classify_by_filename(filename)
            
            # Generate a mood based on the extension
            ext = os.path.splitext(filename)[1].lower()
            if ext == '.wav':
                mood = 'neutral'
            elif ext == '.mp3':
                mood = 'energetic'
            else:
                mood = 'calm'
            
            # Store sample details
            samples[sample_id] = {
                'id': sample_id,
                'name': filename,
                'path': file_path,
                'category': category,
                'mood': mood
            }
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
    
    if not samples:
        return {'success': False, 'error': 'No valid audio files to process', 'samples': []}
    
    # Create category directories
    for sample_id, sample in samples.items():
        category_dir = os.path.join(output_dir, sample['category'])
        os.makedirs(category_dir, exist_ok=True)
        
        mood_dir = os.path.join(category_dir, sample['mood'])
        os.makedirs(mood_dir, exist_ok=True)
        
        # We could copy the file here, but we'll just log for testing
        logger.info(f"Would copy {sample['name']} to {sample['category']}/{sample['mood']}")
    
    return {
        'success': True,
        'samples': list(samples.values())
    }

def classify_by_filename(filename: str) -> str:
    """
    Classify audio sample based on filename.
    """
    filename = filename.lower()
    
    if any(kw in filename for kw in ['kick', 'snare', 'drum', 'hat', 'perc']):
        return 'percussion'
    elif any(kw in filename for kw in ['bass', 'sub', '808']):
        return 'bass'
    elif any(kw in filename for kw in ['synth', 'lead', 'arp']):
        return 'synth'
    elif any(kw in filename for kw in ['vocal', 'voice', 'sing']):
        return 'vocal'
    else:
        return 'other'

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python simple_classify.py <json_config_file>")
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
        result = simple_process(input_files, output_dir)
        
        # Output result as JSON
        print(json.dumps(result))
        
    except Exception as e:
        error_result = {'success': False, 'error': str(e), 'samples': []}
        print(json.dumps(error_result))
        sys.exit(1)