# Sample Buddy AI

An AI-powered audio sample classifier and management platform designed for efficient large-scale audio processing and machine learning categorization. This project includes both a web-based classifier (for Replit) and a desktop application (for local use).

![Sample Buddy AI](screenshot.png)

## Project Components

### 1. Web-Based Classifier

The web-based classifier runs in Replit and provides a simple interface for classifying audio samples:

- Upload audio files through a web form
- Toggle between quick and deep analysis
- View classification results with a progress bar
- Generate JSON output of sample classifications
- Find similar samples with similarity percentage
- Interactive 2D visualization of sample collection

### 2. Desktop Application

The Electron desktop application is designed for local use with a full audio analysis:

- Drag-and-drop file selection
- Category and mood-based organization
- Visual interface with dark purple theme
- Full audio feature extraction
- Find similar samples with similarity scoring
- Interactive 2D visualization with customizable axes

## Classification Methods

### Quick Classification

The quick classifier uses filename patterns to categorize audio samples:
- **Percussion:** kick, snare, hihat, tom, clap, perc, drum
- **Bass:** bass, sub, 808
- **Lead:** lead, arp, pluck, synth
- **Pad:** pad, atmosphere, ambient, strings
- **Vocal:** vocal, vox, voice, sing
- **FX:** fx, effect, riser, impact

### Deep Classification

The deep classifier extracts audio features using librosa:
- **Spectral Features:** centroid, bandwidth, contrast, rolloff
- **Energy & Rhythm:** RMS energy, tempo, onset detection
- **Timbre & Texture:** MFCCs, harmonic-percussive separation
- **Envelope Analysis:** Attack time, sustain detection
- **Frequency Bands:** Sub-bass, bass, mids, highs ratios

## Technical Architecture

### Web Interface
- **Backend:** Flask (Python)
- **Frontend:** HTML/CSS/JavaScript with Bootstrap
- **Classification:** Python scripts with librosa
- **Data Visualization:** Interactive 2D plots with customizable feature mapping
- **Similarity Search:** Feature-based sample matching algorithm

### Desktop Application
- **Frontend:** Electron.js with vanilla JavaScript
- **Backend:** Python scripts for audio processing
- **Communication:** Node.js child process execution
- **Visualization:** Interactive plot with feature dimension mapping
- **Audio Preview:** Waveform visualization with audio playback

## Development Notes

### Replit Environment Considerations

The application has two classifiers:
- `quick_classifier.py`: A lightweight classifier for Replit that uses filename patterns
- `deep_classifier.py`: The full classifier with librosa audio analysis

When running in Replit, the deep classifier may take longer to process files due to resource constraints.

### Local Setup

To run the desktop application locally, you can use the automated setup scripts:

#### On Windows:
1. Clone the repository
2. Navigate to the electron-audio-manager directory:
   ```
   cd electron-audio-manager
   ```
3. Run the setup script:
   ```
   setup.bat
   ```
4. Start the application:
   ```
   start.bat
   ```

#### On macOS/Linux:
1. Clone the repository
2. Navigate to the electron-audio-manager directory:
   ```
   cd electron-audio-manager
   ```
3. Make the scripts executable:
   ```
   chmod +x setup.sh start.sh
   ```
4. Run the setup script:
   ```
   ./setup.sh
   ```
5. Start the application:
   ```
   ./start.sh
   ```

#### Manual Setup (if scripts don't work):
1. Create a Python virtual environment:
   ```
   python -m venv venv
   ```
2. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
3. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Install Node.js dependencies:
   ```
   npm install
   ```
5. Start the application:
   ```
   npm start
   ```

## Resource Requirements

Audio processing with librosa is computationally intensive. When running locally:
- Ensure adequate CPU resources for audio analysis
- Allow for sufficient memory allocation (~1GB minimum recommended)
- For large batches of files, consider processing in smaller groups