const { app, BrowserWindow, ipcMain, dialog, Menu, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');
const { getAppRoot, findPythonScriptsDir, getPythonPath } = require('./fix_paths');
const logger = require('./basic_logger');

// Directory containing Python scripts
const PYTHON_SCRIPTS_DIR = path.join(__dirname, 'python');
// Python executable path
const PYTHON_PATH = getPythonPath();

// Keep a global reference of the window object to avoid garbage collection
let mainWindow;

// Define app data storage paths - store in a visible project folder
const APP_ROOT_DIR = path.join(__dirname, '..');
const APP_DATA_DIR = path.join(APP_ROOT_DIR, 'processed_samples');
const SAMPLES_DB_PATH = path.join(APP_DATA_DIR, 'samples-database.json');
const ORGANIZED_SAMPLES_DIR = path.join(APP_DATA_DIR, 'organized-samples');

// Create app data directories if they don't exist
try {
  fs.mkdirSync(APP_DATA_DIR, { recursive: true });
  fs.mkdirSync(ORGANIZED_SAMPLES_DIR, { recursive: true });

  // Create category subdirectories
  const categories = ['drums', 'bass', 'synth', 'fx', 'vocal', 'other'];
  categories.forEach(category => {
    fs.mkdirSync(path.join(ORGANIZED_SAMPLES_DIR, category), { recursive: true });
  });

  logger.info(`App data directory set up at: ${APP_DATA_DIR}`);
} catch (err) {
  logger.error(`Error setting up app data directory: ${err.message}`);
}

function createWindow() {
  logger.info('Creating main window');
  logger.info('App path: ' + app.getAppPath());
  logger.info('Current working directory: ' + process.cwd());
  logger.info('Python scripts directory: ' + PYTHON_SCRIPTS_DIR);
  logger.info('Python executable: ' + PYTHON_PATH);
  logger.info('Log file location: ' + logger.getLogPath());

  // Create the browser window
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      enableRemoteModule: true,
      devTools: true
    },
    icon: path.join(__dirname, 'assets/icon.png'),
    backgroundColor: '#2e1f3e', // Dark purple theme
  });

  // Load the index.html file
  mainWindow.loadFile('index.html');

  // Open the DevTools in development mode
  mainWindow.webContents.openDevTools();

  // Create application menu with debug options
  const template = [
    {
      label: 'File',
      submenu: [
        { role: 'quit' }
      ]
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' }
      ]
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' }
      ]
    },
    {
      label: 'Debug',
      submenu: [
        {
          label: 'View Logs',
          click: async () => {
            shell.showItemInFolder(logger.getLogPath());
          }
        },
        {
          label: 'Show App Data Folder',
          click: async () => {
            shell.openPath(app.getPath('userData'));
          }
        },
        {
          label: 'Check Python Installation',
          click: async () => {
            const pythonCheck = await runPythonScript(path.join(PYTHON_SCRIPTS_DIR, 'check_environment.py'), []);
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: 'Python Environment Check',
              message: pythonCheck || 'Python check completed with no output',
              buttons: ['OK']
            });
          }
        },
        { type: 'separator' },
        {
          label: 'Install Python Dependencies',
          click: async () => {
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: 'Installing Dependencies',
              message: 'Installing required Python packages. This may take a few minutes...',
              buttons: ['OK']
            });

            try {
              const installResult = await runPythonScript(path.join(PYTHON_SCRIPTS_DIR, 'install_dependencies.py'), []);
              dialog.showMessageBox(mainWindow, {
                type: 'info',
                title: 'Installation Complete',
                message: installResult || 'Dependencies installed successfully',
                buttons: ['OK']
              });
            } catch (error) {
              dialog.showErrorBox('Installation Failed', 
                `Failed to install dependencies: ${error.message}\n\nTry running pip install numpy librosa matplotlib scikit-learn from your command line.`);
            }
          }
        }
      ]
    }
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);

  // Open DevTools in development mode
  if (process.env.NODE_ENV === 'development') {
    mainWindow.webContents.openDevTools();
  }

  // Emitted when the window is closed
  mainWindow.on('closed', function () {
    mainWindow = null;
  });
}

// This method will be called when Electron has finished initialization
app.whenReady().then(() => {
  createWindow();

  app.on('activate', function () {
    // On macOS, recreate a window when the dock icon is clicked and no other windows are open
    if (mainWindow === null) createWindow();
  });
});

// Quit when all windows are closed, except on macOS
app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});

// Handle audio file selection
ipcMain.handle('select-files', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile', 'multiSelections'],
    filters: [
      { name: 'Audio Files', extensions: ['mp3', 'wav', 'ogg', 'flac', 'aif', 'aiff'] }
    ]
  });

  return result.filePaths;
});

// Handle output directory selection
ipcMain.handle('select-output-directory', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory', 'createDirectory']
  });

  return result.filePaths[0];
});

// Function to run Python script
function runPythonScript(scriptPath, args) {
  return new Promise((resolve, reject) => {
    logger.info(`Running Python script: ${PYTHON_PATH} ${scriptPath} ${args.join(' ')}`);

    // Check if the script file exists
    if (!fs.existsSync(scriptPath)) {
      const error = `Python script not found: ${scriptPath}`;
      logger.error(error);
      return reject(new Error(error));
    }

    // Log Python and NumPy versions before running script
    const pythonVersionProcess = spawn(PYTHON_PATH, ['-c', 'import sys; print(f"Python version: {sys.version}")']);
    pythonVersionProcess.stdout.on('data', (data) => {
      logger.info(data.toString().trim());
    });

    // Try to import NumPy to verify it's available
    const numpyCheckProcess = spawn(PYTHON_PATH, ['-c', 'try:\n  import numpy; print(f"NumPy version: {numpy.__version__}")\nexcept ImportError as e:\n  print(f"NumPy import error: {e}")']);
    numpyCheckProcess.stdout.on('data', (data) => {
      logger.info(data.toString().trim());
    });

    // Run the actual script
    logger.info(`Executing Python script: ${scriptPath}`);
    const process = spawn(PYTHON_PATH, [scriptPath, ...args]);

    let outputData = '';
    let errorData = '';

    process.stdout.on('data', (data) => {
      const dataStr = data.toString();
      outputData += dataStr;
      logger.info(`Python stdout: ${dataStr.trim()}`);

      // Check for progress updates in the logs
      if (mainWindow && dataStr.includes('Progress:')) {
        try {
          // Extract progress percentage from the log
          const progressMatch = dataStr.match(/Progress:\s+(\d+\.\d+)%/);
          // Extract files processed and total files count
          const filesProcessedMatch = dataStr.match(/Files processed:\s+(\d+)\s+of\s+(\d+)/);

          let progressData = {};

          if (progressMatch && progressMatch[1]) {
            progressData.progress = parseFloat(progressMatch[1]);
          }

          if (filesProcessedMatch && filesProcessedMatch[1] && filesProcessedMatch[2]) {
            progressData.files_processed = parseInt(filesProcessedMatch[1]);
            progressData.files_total = parseInt(filesProcessedMatch[2]);
          }

          // If we don't find the new format but have a progress percentage, extract processed/total from the message
          if (progressMatch && !filesProcessedMatch) {
            // Try to extract from batch information
            const batchMatch = dataStr.match(/Batch\s+(\d+)\/(\d+)/);
            if (batchMatch && batchMatch[1] && batchMatch[2]) {
              progressData.batch_current = parseInt(batchMatch[1]);
              progressData.batch_total = parseInt(batchMatch[2]);
            }
          }

          progressData.message = dataStr.trim();

          // Send progress update to the renderer
          mainWindow.webContents.send('classification-progress', progressData);
        } catch (e) {
          logger.error('Error parsing progress:', e);
        }
      }
    });

    process.stderr.on('data', (data) => {
      const errorStr = data.toString();
      errorData += errorStr;
      logger.error(`Python stderr: ${errorStr.trim()}`);

      // Check for progress messages in stderr as well (Python logger outputs to stderr)
      if (mainWindow && errorStr.includes('Progress:')) {
        try {
          // Extract progress percentage from the log
          const progressMatch = errorStr.match(/Progress:\s+(\d+\.\d+)%/);
          // Extract files processed and total files count
          const filesProcessedMatch = errorStr.match(/Files processed:\s+(\d+)\s+of\s+(\d+)/);

          let progressData = {};

          if (progressMatch && progressMatch[1]) {
            progressData.progress = parseFloat(progressMatch[1]);
          }

          if (filesProcessedMatch && filesProcessedMatch[1] && filesProcessedMatch[2]) {
            progressData.files_processed = parseInt(filesProcessedMatch[1]);
            progressData.files_total = parseInt(filesProcessedMatch[2]);
          }

          progressData.message = errorStr.trim();

          // Send progress update to the renderer
          mainWindow.webContents.send('classification-progress', progressData);

          // Don't send as error if it's a progress message
          return;
        } catch (e) {
          logger.error('Error parsing progress from stderr:', e);
        }
      }

      // If it's not a progress message, send as error to renderer
      if (mainWindow) {
        mainWindow.webContents.send('classification-error', { 
          error: errorStr.trim() 
        });
      }
    });

    process.on('close', (code) => {
      logger.info(`Python script exited with code: ${code}`);
      if (code === 0) {
        resolve(outputData);
      } else {
        const error = `Python script exited with code ${code}. Error: ${errorData}`;
        logger.error(error);
        reject(new Error(error));
      }
    });
  });
}

// Process audio files with Python classification
ipcMain.handle('process-audio', async (event, { files, useDeepAnalysis = false }) => {
  try {
    // Reset progress in the UI
    if (mainWindow) {
      mainWindow.webContents.send('classification-progress', { 
        progress: 0, 
        message: 'Starting classification...' 
      });
    }

    // Create a temporary JSON file with the list of files to process
    // Using app's internal storage directory instead of requiring output directory
    const tempFilePath = path.join(app.getPath('temp'), 'audio_files.json');
    fs.writeFileSync(tempFilePath, JSON.stringify({ 
      files, 
      outputDir: ORGANIZED_SAMPLES_DIR // Use app's internal directory 
    }));

    // Choose which classifier to use based on the useDeepAnalysis flag
    let classifierScript;
    if (useDeepAnalysis) {
      classifierScript = 'deep_classifier.py';

      // Notify user that deep analysis may take longer
      if (mainWindow) {
        mainWindow.webContents.send('classification-progress', { 
          progress: 0, 
          message: 'Starting deep audio analysis. This may take longer...' 
        });
      }
    } else {
      classifierScript = 'quick_classifier.py';

      if (mainWindow) {
        mainWindow.webContents.send('classification-progress', { 
          progress: 0, 
          message: 'Starting quick filename-based classification...' 
        });
      }
    }

    // Run the selected Python classifier script
    const result = await runPythonScript(
      path.join(PYTHON_SCRIPTS_DIR, classifierScript), 
      [tempFilePath]
    );

    // Send 100% completion notification
    if (mainWindow) {
      mainWindow.webContents.send('classification-progress', { 
        progress: 100, 
        message: 'Classification complete!' 
      });
    }

    // Parse the JSON result
    const resultData = JSON.parse(result);

    return { success: true, result: resultData };
  } catch (error) {
    console.error('Error processing audio files:', error);

    // Send error notification
    if (mainWindow) {
      mainWindow.webContents.send('classification-progress', { 
        progress: 0, 
        message: `Error: ${error.message}` 
      });
    }

    return { success: false, error: error.message };
  }
});

// Show dialog for selecting export directory
ipcMain.handle('show-export-dialog', async () => {
  try {
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openDirectory', 'createDirectory'],
      title: 'Select Export Directory',
      buttonLabel: 'Export Here'
    });

    return {
      canceled: result.canceled,
      filePath: result.filePaths[0]
    };
  } catch (error) {
    logger.error(`Error showing export dialog: ${error.message}`);
    return { canceled: true, error: error.message };
  }
});

// Export samples to a directory
ipcMain.handle('export-samples', async (event, { samples, exportDir, categoryName = 'Samples' }) => {
  try {
    let count = 0;

    // Create export directory if it doesn't exist
    if (!fs.existsSync(exportDir)) {
      fs.mkdirSync(exportDir, { recursive: true });
    }

    // Create a category subfolder
    const categoryDir = path.join(exportDir, categoryName);
    if (!fs.existsSync(categoryDir)) {
      fs.mkdirSync(categoryDir, { recursive: true });
    }

    // Copy each sample file to the export directory
    for (const sample of samples) {
      if (sample.path && fs.existsSync(sample.path)) {
        const targetPath = path.join(categoryDir, path.basename(sample.path));
        fs.copyFileSync(sample.path, targetPath);
        count++;
      }
    }

    logger.info(`Exported ${count} samples to ${categoryDir}`);
    return { success: true, count, exportDir: categoryDir };
  } catch (error) {
    logger.error(`Error exporting samples: ${error.message}`);
    return { success: false, error: error.message };
  }
});

// Get audio sample data - current session
ipcMain.handle('get-samples', async (event, directory) => {
  try {
    logger.info(`Attempting to get samples from directory: ${directory}`);

    // Verify the directory exists
    if (!fs.existsSync(directory)) {
      logger.warn(`Directory does not exist: ${directory}`);

      // Try alternative locations
      const alternativeDirs = [
        path.join(process.cwd(), 'processed_samples', 'organized-samples'),
        path.join(__dirname, '..', 'processed_samples', 'organized-samples'),
        './processed_samples/organized-samples'
      ];

      for (const altDir of alternativeDirs) {
        if (fs.existsSync(altDir)) {
          logger.info(`Found alternative directory: ${altDir}`);
          directory = altDir;
          break;
        }
      }
    }

    // Try to list the contents of the directory
    try {
      const dirContents = fs.readdirSync(directory);
      logger.info(`Contents of ${directory}: ${dirContents.join(', ')}`);

      // Check if there's an 'other' folder and list its contents
      const otherDir = path.join(directory, 'other');
      if (fs.existsSync(otherDir)) {
        const otherContents = fs.readdirSync(otherDir);
        logger.info(`Contents of ${otherDir}: ${otherContents.join(', ')}`);
      }
    } catch (err) {
      logger.error(`Error listing directory contents: ${err.message}`);
    }

    logger.info(`Running Python script with directory: ${directory}`);
    const result = await runPythonScript(
      path.join(PYTHON_SCRIPTS_DIR, 'get_samples.py'),
      [directory]
    );

    // Log the raw result to debug
    logger.info(`Raw result from Python: ${result.substring(0, 200)}...`);

    const parsedResult = JSON.parse(result);
    if (parsedResult.samples) {
      logger.info(`Found ${parsedResult.samples.length} samples`);

      // Log the first few samples for debugging
      if (parsedResult.samples.length > 0) {
        logger.info(`First sample: ${JSON.stringify(parsedResult.samples[0])}`);
      }
    } else {
      logger.warn('No samples found in the result');
    }

    return { success: true, samples: parsedResult.samples || [] };
  } catch (error) {
    logger.error(`Error getting samples: ${error.message}`);
    return { success: false, error: error.message };
  }
});

// Get all audio samples from all categories - for the "All Samples" view
ipcMain.handle('get-all-samples', async (event, directory) => {
  try {
    logger.info(`Attempting to get all samples from directory: ${directory}`);

    // Verify the directory exists
    if (!fs.existsSync(directory)) {
      logger.warn(`Directory does not exist: ${directory}`);

      // Try alternative locations
      const alternativeDirs = [
        path.join(process.cwd(), 'processed_samples', 'organized-samples'),
        path.join(__dirname, '..', 'processed_samples', 'organized-samples'),
        './processed_samples/organized-samples'
      ];

      for (const altDir of alternativeDirs) {
        if (fs.existsSync(altDir)) {
          logger.info(`Found alternative directory: ${altDir}`);
          directory = altDir;
          break;
        }
      }
    }

    // Use the loadAllSamples function
    const loadAllSamples = require('./loadAllSamples');
    const samples = await loadAllSamples(directory, []);

    return { success: true, samples };
  } catch (error) {
    logger.error(`Error getting all samples: ${error.message}`);
    return { success: false, error: error.message };
  }
});

// Get app storage directory
ipcMain.handle('get-app-storage-directory', async () => {
  try {
    // Log all potential sample directories to help with debugging
    logger.info(`Current directory: ${process.cwd()}`);
    logger.info(`App directory: ${APP_ROOT_DIR}`);
    logger.info(`Organized samples directory: ${ORGANIZED_SAMPLES_DIR}`);

    // Check if organized samples directory exists
    if (!fs.existsSync(ORGANIZED_SAMPLES_DIR)) {
      logger.warn(`Organized samples directory does not exist: ${ORGANIZED_SAMPLES_DIR}`);

      // Try looking in some alternative locations
      const alternativeLocations = [
        path.join(process.cwd(), 'processed_samples', 'organized-samples'),
        path.join(process.cwd(), 'processed_samples'),
        path.join(__dirname, 'processed_samples', 'organized-samples'),
        path.join(__dirname, '..', 'processed_samples', 'organized-samples')
      ];

      for (const location of alternativeLocations) {
        if (fs.existsSync(location)) {
          logger.info(`Found alternative samples directory: ${location}`);
          return location;
        }
      }
    }

    // Return the original directory even if it doesn't exist yet
    logger.info(`Returning app storage directory: ${ORGANIZED_SAMPLES_DIR}`);
    return ORGANIZED_SAMPLES_DIR;
  } catch (error) {
    logger.error('Error getting app storage directory:', error);
    throw error;
  }
});

// Export a single sample file
ipcMain.handle('export-sample', async (event, { samplePath, sampleName }) => {
  try {
    logger.info(`Attempting to export sample: ${sampleName}`);

    // Ask user where to save the file
    const result = await dialog.showSaveDialog({
      title: 'Export Sample',
      defaultPath: sampleName,
      buttonLabel: 'Export',
      filters: [
        { name: 'Audio Files', extensions: ['wav', 'mp3', 'ogg', 'flac', 'aif', 'aiff'] }
      ]
    });

    if (result.canceled) {
      logger.info('Export sample canceled by user');
      return { success: false, canceled: true };
    }

    // Copy the file to the selected location
    fs.copyFileSync(samplePath, result.filePath);
    logger.info(`Successfully exported sample to: ${result.filePath}`);

    return { success: true, path: result.filePath };
  } catch (error) {
    logger.error(`Error exporting sample: ${error.message}`);
    return { success: false, error: error.message };
  }
});

// Export samples to a folder
ipcMain.handle('export-samples-to-folder', async (event, { category }) => {
  try {
    logger.info(`Attempting to export samples from category: ${category}`);

    // Ask user for destination folder
    const result = await dialog.showOpenDialog({
      title: 'Select Destination Folder',
      properties: ['openDirectory', 'createDirectory'],
      buttonLabel: 'Export Here'
    });

    if (result.canceled) {
      logger.info('Export to folder canceled by user');
      return { success: false, canceled: true };
    }

    const destinationFolder = result.filePaths[0];
    logger.info(`Selected destination folder: ${destinationFolder}`);

    // Determine source folder based on category
    let sourceFolder;
    if (category === 'all') {
      sourceFolder = ORGANIZED_SAMPLES_DIR;
    } else {
      sourceFolder = path.join(ORGANIZED_SAMPLES_DIR, category);
    }

    if (!fs.existsSync(sourceFolder)) {
      logger.error(`Source folder does not exist: ${sourceFolder}`);
      return { success: false, error: 'Source folder not found' };
    }

    // Export all samples from the source folder
    let exportCount = 0;

    if (category === 'all') {
      // Export from all category folders
      const categories = fs.readdirSync(sourceFolder);
      for (const cat of categories) {
        const catFolder = path.join(sourceFolder, cat);
        if (fs.statSync(catFolder).isDirectory()) {
          // Create category subfolder in destination
          const catDestFolder = path.join(destinationFolder, cat);
          if (!fs.existsSync(catDestFolder)) {
            fs.mkdirSync(catDestFolder, { recursive: true });
          }

          // Copy all audio files from this category
          const files = fs.readdirSync(catFolder);
          for (const file of files) {
            if (file.match(/\.(wav|mp3|ogg|flac|aif|aiff)$/i)) {
              const sourcePath = path.join(catFolder, file);
              const destPath = path.join(catDestFolder, file);
              fs.copyFileSync(sourcePath, destPath);
              exportCount++;
            }
          }
        }
      }
    } else {
      // Export from a specific category folder
      // Create destination folder if needed
      const catDestFolder = path.join(destinationFolder, category);
      if (!fs.existsSync(catDestFolder)) {
        fs.mkdirSync(catDestFolder, { recursive: true });
      }

      // Copy all audio files
      const files = fs.readdirSync(sourceFolder);
      for (const file of files) {
        if (file.match(/\.(wav|mp3|ogg|flac|aif|aiff)$/i)) {
          const sourcePath = path.join(sourceFolder, file);
          const destPath = path.join(catDestFolder, file);
          fs.copyFileSync(sourcePath, destPath);
          exportCount++;
        }
      }
    }

    logger.info(`Successfully exported ${exportCount} samples to: ${destinationFolder}`);
    return { success: true, count: exportCount, path: destinationFolder };
  } catch (error) {
    logger.error(`Error exporting samples to folder: ${error.message}`);
    return { success: false, error: error.message };
  }
});

// Generate waveform data for an audio file
ipcMain.handle('generate-waveform', async (event, audioFile) => {
  try {
    // First attempt: Run a Python script to generate waveform data using librosa
    logger.info('Attempting to generate waveform with librosa for: ' + audioFile);
    let result;

    try {
      result = await runPythonScript(
        path.join(PYTHON_SCRIPTS_DIR, 'generate_waveform.py'),
        [audioFile]
      );
    } catch (libErr) {
      logger.warn('Failed to generate waveform with librosa: ' + libErr.message);
      logger.info('Falling back to simple waveform generator...');

      // Second attempt: Fall back to our simpler implementation if librosa fails
      result = await runPythonScript(
        path.join(PYTHON_SCRIPTS_DIR, 'simple_waveform.py'),
        [audioFile]
      );
    }

    if (!result) {
      throw new Error('Failed to generate waveform data with both methods');
    }

    return JSON.parse(result);
  } catch (error) {
    logger.error('Error generating waveform data: ' + error.message);
    logger.error('Audio file: ' + audioFile);
    return null;
  }
});

// Get raw audio data for waveform generation in the renderer
ipcMain.handle('get-audio-data', async (event, audioPath) => {
  try {
    logger.info(`Getting audio data for: ${audioPath}`);

    // Check if file exists
    if (!fs.existsSync(audioPath)) {
      throw new Error(`Audio file not found: ${audioPath}`);
    }

    // Read the file binary data
    const buffer = fs.readFileSync(audioPath);

    // Return the buffer as ArrayBuffer
    return { 
      success: true, 
      buffer: buffer 
    };
  } catch (error) {
    logger.error(`Error reading audio data: ${error.message}`);
    return { 
      success: false, 
      error: error.message 
    };
  }
});

// Find similar samples based on a reference sample
ipcMain.handle('find-similar-samples', async (event, { referenceSample, samplesDir, maxResults = 5 }) => {
  try {
    logger.info(`Finding samples similar to: ${referenceSample}`);
    logger.info(`Looking in directory: ${samplesDir}`);
    logger.info(`Max results: ${maxResults}`);

    // Run a Python script to find similar samples
    const result = await runPythonScript(
      path.join(PYTHON_SCRIPTS_DIR, 'find_similar_samples.py'),
      [referenceSample, samplesDir, `max_results=${maxResults}`]
    );

    if (!result) {
      throw new Error('Failed to find similar samples');
    }

    return { success: true, result: JSON.parse(result) };
  } catch (error) {
    console.error('Error finding similar samples:', error);
    return { success: false, error: error.message };
  }
});

// Visualization-related code has been removed to focus on sample classification