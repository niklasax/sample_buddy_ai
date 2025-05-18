import os
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define category keywords
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

def process_files(input_files: List[str], output_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Process audio files and classify them based on filenames.
    
    Args:
        input_files: List of file paths to process
        output_dir: Output directory for classified files (optional)
        
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
            
            # Classify the sample
            classification = classify_by_filename(file_path)
            
            # Create sample metadata
            sample = {
                "id": sample_id,
                "name": os.path.basename(file_path),
                "path": file_path,
                "category": classification["type"],
                "subtype": classification["subtype"],
                "mood": classification["mood"]
            }
            
            # Organize the file if output directory is provided
            if output_dir:
                # Use the organized-samples folder structure
                organized_dir = output_dir
                
                # Create category directory (drums, bass, synth, etc.)
                category_dir = os.path.join(organized_dir, classification["type"])
                os.makedirs(category_dir, exist_ok=True)
                
                # Destination path directly in the category folder
                dest_path = os.path.join(category_dir, os.path.basename(file_path))
                
                # Also create a JSON file with the classification info
                json_path = os.path.join(category_dir, f"{os.path.splitext(os.path.basename(file_path))[0]}.json")
                
                # Copy the file
                try:
                    import shutil
                    if os.path.exists(file_path) and file_path != dest_path:
                        # Copy the audio file to the destination
                        shutil.copy2(file_path, dest_path)
                        
                        # Write the classification info to a JSON file
                        with open(json_path, 'w') as json_file:
                            json_data = {
                                "file_name": os.path.basename(file_path),
                                "category": classification["type"],
                                "subtype": classification["subtype"],
                                "mood": classification["mood"]
                            }
                            json.dump(json_data, json_file, indent=2)
                        
                        logger.info(f"Copied {os.path.basename(file_path)} to {classification['type']} and saved metadata")
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
            
            # Small delay to show progress in UI
            time.sleep(0.01)
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
    
    return results

def main():
    """Main function to run the classifier from command line."""
    parser = argparse.ArgumentParser(description="Classify audio samples based on filename")
    parser.add_argument("config_file", help="JSON config file with input_files and output_dir")
    
    args = parser.parse_args()
    
    # Load config file
    with open(args.config_file, "r") as f:
        config = json.load(f)
    
    # Process files
    results = process_files(config.get("files", []), config.get("outputDir"))
    
    # Print results as JSON
    print(json.dumps(results))

if __name__ == "__main__":
    main()