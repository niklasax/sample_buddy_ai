# Sample Buddy AI - Desktop Application

This is the desktop version of Sample Buddy AI, an intelligent audio sample classifier and manager.

## Prerequisites

Before running the application, make sure you have:

1. **Python 3.8+** installed (with pip)
2. **Node.js 14+** installed (with npm)

## Quick Setup

### Windows
1. Run `setup.bat` to create a virtual environment and install dependencies
2. Run `start.bat` to launch the application

### macOS/Linux
1. Make the scripts executable: `chmod +x setup.sh start.sh copy_samples.py`
2. Run `./setup.sh` to create a virtual environment and install dependencies
3. Run `./start.sh` to launch the application

## Test Samples

If you need test audio samples for trying out the application, you can:

1. **Generate simple test tones**:
   ```
   # Make sure the virtual environment is activated first
   python copy_samples.py --generate --num-samples 20
   ```

2. **Copy samples from another directory**:
   ```
   # Replace /path/to/samples with your audio samples directory
   python copy_samples.py --source /path/to/samples --max-files 5
   ```

This will create properly named samples in the `sample_data` directory that you can use to test the classification system.

## Features

- Drag-and-drop interface for audio file selection
- Deep audio analysis with librosa
- Categorization by instrument type and mood
- Batch processing capabilities
- Category-based file organization

## Troubleshooting

If you encounter any issues:

1. **Python not found**: Make sure Python is in your PATH
2. **Node.js not found**: Make sure Node.js is in your PATH
3. **Installation errors**: Check that you have internet connectivity and appropriate permissions
4. **Audio processing errors**: Some audio formats may not be supported; try converting to WAV format

## Requirements

The application uses the following Python packages:
- librosa (audio analysis)
- numpy (numerical processing)
- scikit-learn (machine learning)
- scipy (scientific computing)
- matplotlib (visualization)

And the following Node.js packages:
- electron (desktop application framework)
- electron-builder (packaging)