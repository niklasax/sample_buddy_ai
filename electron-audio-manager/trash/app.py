import os
import json
import tempfile
import logging
import datetime
import subprocess
import shutil
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Configure upload settings
UPLOAD_FOLDER = os.path.join("uploads")
OUTPUT_FOLDER = os.path.join("processed_samples")
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'ogg', 'flac', 'aif', 'aiff'}

# Create upload and output directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max upload

# Store process status for AJAX polling
process_status = {
    'running': False,
    'progress': 0,
    'total': 0,
    'current': 0,
    'message': ''
}

def allowed_file(filename):
    """Check if the file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def run_classifier(files, output_dir, use_deep=False, batch_size=None, max_workers=None):
    """Run the appropriate classifier on the provided files with batch processing

    Args:
        files: List of file paths to process
        output_dir: Directory to store processed files
        use_deep: Whether to use deep analysis with audio feature extraction
        batch_size: Number of files to process in each batch
        max_workers: Maximum number of worker threads for parallel processing
    """
    # Set default batch processing parameters based on classifier type
    if batch_size is None:
        batch_size = 10 if use_deep else 20  # Smaller batches for deep analysis
    
    if max_workers is None:
        max_workers = 2 if use_deep else 4  # Fewer workers for deep analysis (more CPU intensive)
    
    # Create a temporary config file for the classifier
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tf:
        config = {
            "files": files,
            "outputDir": output_dir
        }
        json.dump(config, tf)
        config_path = tf.name
    
    # Choose classifier based on deep flag
    classifier_script = "deep_classifier.py" if use_deep else "quick_classifier.py"
    
    # Reset process status
    global process_status
    process_status = {
        'running': True,
        'progress': 0,  # Keep for backward compatibility
        'overall_progress': 0,  # Frontend uses this field
        'total_files': len(files),
        'processed_files': 0,
        'message': f"Starting {'deep' if use_deep else 'quick'} classification with batch processing...",
        'batches': {
            'total': (len(files) + batch_size - 1) // batch_size,
            'current': 0,
            'progress': 0
        },
        'start_time': datetime.datetime.now().isoformat(),
        'batch_size': batch_size,
        'max_workers': max_workers
    }
    
    # Run the classifier as a subprocess
    cmd = ["python", classifier_script, config_path, 
           f"--batch-size={batch_size}", 
           f"--max-workers={max_workers}"]
    
    if use_deep:
        # Deep classifier has a --quick flag, but we don't use it here as we want deep analysis
        pass
    
    try:
        # Run classifier and capture output
        logger.info(f"Running classifier: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout
        
        # Parse JSON result
        try:
            results = json.loads(output)
            
            # Calculate timing and throughput statistics
            end_time = datetime.datetime.now()
            start_time = datetime.datetime.fromisoformat(process_status['start_time'])
            elapsed_seconds = (end_time - start_time).total_seconds()
            files_per_second = len(files) / elapsed_seconds if elapsed_seconds > 0 else 0
            
            # Add additional statistics if they're not already in the results
            if 'stats' not in results:
                results['stats'] = {
                    'total_files': len(files),
                    'processed_files': len(results.get('samples', [])),
                    'total_time': elapsed_seconds,
                    'files_per_second': files_per_second
                }
            
            # Update process status
            process_status['running'] = False
            process_status['progress'] = 100  # Keep for backward compatibility
            process_status['overall_progress'] = 100  # Frontend uses this field
            process_status['processed_files'] = len(results.get('samples', []))
            process_status['batches']['current'] = process_status['batches']['total']
            process_status['batches']['progress'] = 100
            process_status['message'] = (
                f"Classification complete! {len(results.get('samples', []))} files processed "
                f"in {elapsed_seconds:.1f} seconds ({files_per_second:.1f} files/sec)."
            )
            
            # Clean up temp file
            os.unlink(config_path)
            
            return results
        except json.JSONDecodeError:
            logger.error(f"Failed to parse classifier output: {output}")
            process_status['running'] = False
            process_status['message'] = "Error: Failed to parse classifier output"
            return {
                "success": False, 
                "error": "Failed to parse classifier output",
                "raw_output": output[:500] + "..." if len(output) > 500 else output
            }
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Classifier failed: {e}")
        logger.error(f"Stderr: {e.stderr}")
        
        # Update process status
        process_status['running'] = False
        process_status['message'] = f"Error: Classifier failed - {e.stderr}"
        
        # Clean up temp file
        os.unlink(config_path)
        
        return {
            "success": False, 
            "error": str(e),
            "stderr": e.stderr,
            "stdout": e.stdout
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and classification"""
    try:
        # Check if files were uploaded
        if 'file' not in request.files:
            flash('No files uploaded', 'error')
            return redirect(url_for('index'))
        
        # Get upload settings
        use_deep = request.form.get('use_deep', 'false') == 'true'
        custom_output_dir = request.form.get('custom_output_dir', '').strip()
        
        # Get batch processing parameters (or use defaults)
        try:
            batch_size = int(request.form.get('batch_size', '0'))
            if batch_size <= 0:
                batch_size = 10 if use_deep else 20  # Default batch sizes
        except ValueError:
            batch_size = 10 if use_deep else 20
            
        try:
            max_workers = int(request.form.get('max_workers', '0'))
            if max_workers <= 0:
                max_workers = 2 if use_deep else 4  # Default worker counts
        except ValueError:
            max_workers = 2 if use_deep else 4
        
        # Process uploaded files
        files = request.files.getlist('file')
        valid_files = []
        
        # Generate a unique output directory
        if custom_output_dir:
            # Create a session folder with the custom name
            output_dir = os.path.join(app.config['OUTPUT_FOLDER'], f"session_{custom_output_dir}")
        else:
            # Generate a unique session ID
            session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = os.path.join(app.config['OUTPUT_FOLDER'], f"session_{session_id}")
        
        os.makedirs(output_dir, exist_ok=True)
        session['output_dir'] = output_dir
        
        # Save all uploaded files
        for file in files:
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                valid_files.append(file_path)
        
        if not valid_files:
            flash('No valid audio files were uploaded', 'error')
            return redirect(url_for('index'))
        
        # Run the classifier (this is just saving the request - actual processing happens asynchronously)
        session['classification_job'] = {
            'files': valid_files,
            'output_dir': output_dir,
            'use_deep': use_deep,
            'batch_size': batch_size,
            'max_workers': max_workers,
            'started_at': datetime.datetime.now().isoformat(),
            'total_files': len(valid_files)
        }
        
        # Redirect to the results page which will poll for progress
        return redirect(url_for('results'))
        
    except Exception as e:
        logger.exception(f"Error processing upload: {e}")
        flash(f'Error processing upload: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/results')
def results():
    """Display classification results"""
    # Check if we have a classification job
    job = session.get('classification_job')
    if not job:
        flash('No classification job found', 'error')
        return redirect(url_for('index'))
    
    return render_template('results.html', job=job)

@app.route('/start_classification', methods=['POST'])
def start_classification():
    """Start classification process (AJAX)"""
    try:
        # Get job from session
        job = session.get('classification_job')
        if not job:
            return jsonify({'success': False, 'error': 'No classification job found'})
        
        # Get batch processing parameters from the job
        batch_size = job.get('batch_size', None)
        max_workers = job.get('max_workers', None)
        
        # Run the classifier with batch processing
        results = run_classifier(
            files=job['files'],
            output_dir=job['output_dir'], 
            use_deep=job['use_deep'],
            batch_size=batch_size,
            max_workers=max_workers
        )
        
        # Store results in session
        session['classification_results'] = results
        
        return jsonify({'success': True})
    except Exception as e:
        logger.exception(f"Error starting classification: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/classification_status')
def classification_status():
    """Get classification status for AJAX polling"""
    global process_status
    return jsonify(process_status)

@app.route('/classification_results')
def classification_results():
    """Get classification results"""
    results = session.get('classification_results', {'success': False, 'error': 'No results found'})
    return jsonify(results)

@app.route('/clear_samples', methods=['POST'])
def clear_samples():
    """Clear all uploaded and processed samples"""
    try:
        # Clear upload folder
        for file in os.listdir(app.config['UPLOAD_FOLDER']):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file)
            if os.path.isfile(file_path):
                os.unlink(file_path)
        
        # Don't clear output folder, as users might want to keep their classified samples
        
        # Reset process status
        global process_status
        process_status = {
            'running': False,
            'progress': 0,
            'total': 0,
            'current': 0,
            'message': ''
        }
        
        # Clear session
        session.pop('classification_job', None)
        session.pop('classification_results', None)
        session.pop('output_dir', None)
        
        flash('All uploaded samples have been cleared', 'success')
    except Exception as e:
        logger.exception(f"Error clearing samples: {e}")
        flash(f'Error clearing samples: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/restart')
def restart():
    """Restart the application by clearing the session"""
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)