import os
import json
import logging
import argparse
import traceback
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import time
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

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

def _update_progress(increment: int = 0, batch_num: int = None, message: str = None, error: str = None):
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
        
        if message:
            _progress_data["status_message"] = message
        
        if error:
            _progress_data["errors"].append(error)
        
        # Calculate progress percentages
        if _progress_data["total_files"] > 0:
            _progress_data["overall_progress"] = (_progress_data["processed_files"] / _progress_data["total_files"]) * 100
        
        if _progress_data["total_batches"] > 0:
            _progress_data["batch_progress"] = (_progress_data["current_batch"] / _progress_data["total_batches"]) * 100
        
        # Log progress
        logger.info(f"Progress: {_progress_data['overall_progress']:.1f}% - Batch {_progress_data['current_batch']}/{_progress_data['total_batches']} - {_progress_data['status_message']}")

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

def process_single_file(file_path: str, output_dir: Optional[str] = None, 
                        batch_num: int = 0, file_num: int = 0) -> Dict[str, Any]:
    """
    Process a single audio file with quick classification.
    
    Args:
        file_path: Path to the audio file
        output_dir: Output directory for classified files (optional)
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
        
        # Classify the sample
        classification = classify_by_filename(file_path)
        
        # Create sample metadata
        sample = {
            "id": sample_id,
            "name": file_name,
            "path": file_path,
            "category": classification["type"],
            "subtype": classification["subtype"],
            "mood": classification["mood"],
            "batch": batch_num,
            "processing_time": time.time() - start_time
        }
        
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

def process_files(input_files: List[str], output_dir: Optional[str] = None, 
                  batch_size: int = 20, max_workers: int = 4) -> Dict[str, Any]:
    """
    Process audio files with classification using batch processing.
    
    Args:
        input_files: List of file paths to process
        output_dir: Output directory for classified files (optional)
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
    parser = argparse.ArgumentParser(description="Classify audio samples based on filename")
    parser.add_argument("config_file", help="JSON config file with input_files and output_dir")
    parser.add_argument("--batch-size", type=int, default=20, help="Number of files to process in each batch")
    parser.add_argument("--max-workers", type=int, default=4, help="Maximum number of worker threads")
    
    args = parser.parse_args()
    
    # Load config file
    with open(args.config_file, "r") as f:
        config = json.load(f)
    
    # Process files
    results = process_files(
        input_files=config.get("files", []), 
        output_dir=config.get("outputDir"),
        batch_size=args.batch_size,
        max_workers=args.max_workers
    )
    
    # Print results as JSON
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()