// Fix paths for various environments
const path = require('path');
const fs = require('fs');

// Get the actual app root directory
function getAppRoot() {
  return path.resolve(path.join(__dirname, '..'));
}

// Check if Python scripts directory exists in various locations
function findPythonScriptsDir() {
  const possiblePaths = [
    path.join(getAppRoot(), 'python'),      // Standard location
    path.join(getAppRoot(), '..', 'python'), // One level up
    path.join(getAppRoot(), '..', '..', 'python'), // Two levels up
    path.join(process.cwd(), 'python'),     // Current working directory
  ];

  for (const dir of possiblePaths) {
    if (fs.existsSync(dir)) {
      console.log(`Found Python scripts directory at: ${dir}`);
      return dir;
    }
  }

  // Default to the standard location even if it doesn't exist yet
  return path.join(getAppRoot(), 'python');
}

// Helper to check if Python has NumPy installed
function checkPythonDependencies(pythonPath) {
  const { spawnSync } = require('child_process');
  try {
    // Run a simple Python script to check if NumPy is available
    const result = spawnSync(pythonPath, ['-c', 'import numpy; print("NumPy OK")'], {
      encoding: 'utf8',
      timeout: 5000 // 5 second timeout
    });
    
    if (result.stdout && result.stdout.includes('NumPy OK')) {
      console.log(`Python at ${pythonPath} has NumPy installed`);
      return true;
    } else {
      console.log(`Python at ${pythonPath} does not have NumPy installed or failed to run`);
      console.log(`Error: ${result.stderr}`);
      return false;
    }
  } catch (err) {
    console.log(`Error checking Python dependencies: ${err.message}`);
    return false;
  }
}

// Get the Python executable path
function getPythonPath() {
  // Check if we're in a Conda environment
  if (process.env.CONDA_PREFIX) {
    const condaPython = process.platform === 'win32' 
      ? path.join(process.env.CONDA_PREFIX, 'python.exe')
      : path.join(process.env.CONDA_PREFIX, 'bin', 'python');
      
    if (fs.existsSync(condaPython) && checkPythonDependencies(condaPython)) {
      console.log(`Using Conda Python at: ${condaPython}`);
      return condaPython;
    }
  }
  
  // Check if we're in a standard virtual environment
  if (process.env.VIRTUAL_ENV) {
    const venvPython = process.platform === 'win32'
      ? path.join(process.env.VIRTUAL_ENV, 'Scripts', 'python.exe')
      : path.join(process.env.VIRTUAL_ENV, 'bin', 'python');
      
    if (fs.existsSync(venvPython) && checkPythonDependencies(venvPython)) {
      console.log(`Using virtualenv Python at: ${venvPython}`);
      return venvPython;
    }
  }
  
  // Try to find conda in the user's home directory
  const homeDir = process.env.HOME || process.env.USERPROFILE;
  const possiblePythonPaths = [
    // Conda paths
    path.join(homeDir, 'anaconda3', 'bin', 'python'),
    path.join(homeDir, 'miniconda3', 'bin', 'python'),
    path.join(homeDir, 'opt', 'anaconda3', 'bin', 'python'),
    '/opt/anaconda3/bin/python',
    '/usr/local/anaconda3/bin/python',
    // System Python paths
    '/usr/bin/python3',
    '/usr/local/bin/python3',
    // Windows Python paths
    'C:\\Python39\\python.exe',
    'C:\\Python310\\python.exe',
    'C:\\Python311\\python.exe',
    'C:\\Python312\\python.exe',
    // Try these generic names last
    'python3',
    'python'
  ];
  
  // Windows-specific paths with backslashes
  if (process.platform === 'win32') {
    for (let i = 39; i <= 312; i++) {
      possiblePythonPaths.push(`C:\\Python${i}\\python.exe`);
    }
  }
  
  for (const pythonPath of possiblePythonPaths) {
    if (fs.existsSync(pythonPath) && checkPythonDependencies(pythonPath)) {
      console.log(`Found Python with NumPy at: ${pythonPath}`);
      return pythonPath;
    }
  }
  
  // If no Python with NumPy was found, fall back to 'python'
  console.log('No Python installation with NumPy found, defaulting to "python"');
  return 'python';
}

module.exports = {
  getAppRoot,
  findPythonScriptsDir,
  getPythonPath
};