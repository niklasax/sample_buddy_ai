// Import required modules
const { ipcRenderer } = require('electron');
const WaveformData = require('waveform-data');
const fs = require('fs');
const path = require('path');
const events = require('./simple_events');
const logger = require('./basic_logger');

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  logger.info('Application initialized');
  
  // Check critical UI elements
  const criticalElements = [
    { id: 'selectFilesBtn', description: 'Select Files Button' },
    { id: 'processBtn', description: 'Process Samples Button' },
    { id: 'fileUploadArea', description: 'File Upload Area' },
    { id: 'clearSamplesBtn', description: 'Clear Samples Button' }
  ];
  
  // Initialize all UI elements and event handlers
  initializeElements();
  
  criticalElements.forEach(element => {
    events.checkElement(element.id, element.description);
  });
  
  // Add global click handler to close dropdown menus when clicking outside
  document.addEventListener('click', (e) => {
    // If we didn't click directly on a menu button or inside a dropdown
    if (!e.target.closest('.menu-btn') && !e.target.closest('.menu-dropdown')) {
      // Close all dropdown menus
      document.querySelectorAll('.menu-dropdown.show').forEach(dropdown => {
        dropdown.classList.remove('show');
      });
    }
  });
  
  // Initialize all elements
  initializeElements();
});

// DOM Elements
const selectFilesBtn = document.getElementById('selectFilesBtn');
const processBtn = document.getElementById('processBtn');
const fileUploadArea = document.getElementById('fileUploadArea');
const filesList = document.getElementById('filesList');
const samplesArea = document.getElementById('samplesArea');
const samplesGrid = document.getElementById('samplesGrid');
const categoriesList = document.getElementById('categoriesList');
const gridViewBtn = document.getElementById('gridViewBtn');
const listViewBtn = document.getElementById('listViewBtn');
const statusBar = document.getElementById('statusBar');
const progressBar = document.getElementById('progressBar');
const progressPercentage = document.getElementById('progressPercentage');
const useDeepAnalysisCheckbox = document.getElementById('useDeepAnalysis');
const clearSamplesBtn = document.getElementById('clearSamplesBtn');
const sampleCardTemplate = document.getElementById('sampleCardTemplate');
const currentSamplesBtn = document.getElementById('currentSamplesBtn');
const allSamplesBtn = document.getElementById('allSamplesBtn');

/**
 * Initialize all UI elements and attach event listeners
 */
function initializeElements() {
  // Setup window event listeners for cleanup
  window.addEventListener('blur', () => {
    // When window loses focus, suspend audio contexts to free resources
    stopAllAudio();
  });
  
  // Listen for visibility change to handle tab switching
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      stopAllAudio();
    }
  });
  
  // Check if audio system is working
  const audioSystemWorking = checkAudioSystem();
  if (!audioSystemWorking) {
    console.warn('Audio system check failed - some features may not work properly');
  }
  
  // Add event listeners for core functionality buttons
  if (selectFilesBtn) {
    console.log('Attaching event listener to Select Files button');
    selectFilesBtn.addEventListener('click', selectFiles);
  } else {
    console.error('Select Files button not found in the DOM');
  }
  
  // Set up sample view toggle buttons
  const currentSamplesBtn = document.getElementById('currentSamplesBtn');
  const allSamplesBtn = document.getElementById('allSamplesBtn');
  
  if (currentSamplesBtn && allSamplesBtn) {
    console.log('Attaching event listeners to sample view toggle buttons');
    
    // Only add event listeners once
    currentSamplesBtn.addEventListener('click', () => {
      if (state.samplesViewMode !== 'current') {
        state.samplesViewMode = 'current';
        currentSamplesBtn.classList.add('active');
        allSamplesBtn.classList.remove('active');
        showStatus('Showing current session samples', 'info');
        
        // Update the categories list for current samples
        buildCategoriesFromSamples();
        
        // Then display the samples
        displaySamples();
      }
    });
    
    allSamplesBtn.addEventListener('click', async () => {
      if (state.samplesViewMode !== 'all') {
        // Set the view mode first
        state.samplesViewMode = 'all';
        allSamplesBtn.classList.add('active');
        currentSamplesBtn.classList.remove('active');
        
        // Show loading status
        showStatus('Loading all processed samples...', 'processing');
        
        try {
          // Copy current samples first
          if (state.processedSamples.length > 0 && state.allSamples.length === 0) {
            state.allSamples = [...state.processedSamples];
          }
          
          // Get the app storage directory
          const appStorageDir = await getAppStorageDirectory();
          
          if (!appStorageDir) {
            throw new Error('Could not access app storage directory');
          }
          
          // Get all samples from the main process
          const result = await ipcRenderer.invoke('get-all-samples', appStorageDir);
          
          if (result.success) {
            if (result.samples && result.samples.length > 0) {
              // Store the samples and display them
              state.allSamples = result.samples;
              showStatus(`Showing all ${state.allSamples.length} processed samples`, 'success');
            } else {
              // Just use the current samples
              showStatus('No additional samples found, showing current session only', 'info');
            }
          } else {
            // Error occurred
            throw new Error(result.error || 'Failed to load all samples');
          }
        } catch (error) {
          console.error('Error loading all samples:', error);
          showStatus(`Error loading all samples: ${error.message}`, 'error');
          
          // Still show what we have
          if (state.allSamples.length === 0 && state.processedSamples.length > 0) {
            state.allSamples = [...state.processedSamples];
          }
        }
        
        // Update the categories to reflect all samples
        buildCategoriesFromAllSamples();
        
        // Update UI
        displaySamples();
      }
    });
    
    // Event listeners already added above
  } else {
    console.error('Sample view toggle buttons not found in the DOM');
  }
  
  // Show message about using internal storage
  showStatus('Samples will be stored in the app\'s internal storage', 'info');
  
  // Load previously processed samples on startup
  loadSavedSamples();
  
  // This was an error - removing the incorrect console.error message
  
  if (processBtn) {
    console.log('Attaching event listener to Process Samples button');
    processBtn.addEventListener('click', processAudioFiles);
  } else {
    console.error('Process Samples button not found in the DOM');
  }

  // Add event listener for clear samples button
  if (clearSamplesBtn) {
    console.log('Attaching event listener to Clear Samples button');
    clearSamplesBtn.addEventListener('click', () => {
      console.log('Clear Samples button clicked');
      // Confirm before clearing
      if (confirm('Are you sure you want to clear current session samples? This will not affect previously processed samples.')) {
        console.log('User confirmed clearing samples');
        clearAllSamples();
      } else {
        console.log('User cancelled clearing samples');
      }
    });
  } else {
    console.error('Clear Samples button not found in the DOM');
  }
  
  // Check and report on waveform-data library availability
  if (typeof WaveformData === 'undefined') {
    console.error('WaveformData library not found - waveform visualization will not be available');
    showStatus('Warning: Waveform visualization not available', 'warning');
  } else {
    console.log('WaveformData library detected and ready');
  }
}

// Visualization elements removed to focus on sample classification

// Modal elements
const similarSamplesModal = document.getElementById('similarSamplesModal');
const selectSamplesModal = document.getElementById('selectSamplesModal');
const modalCloseButtons = document.querySelectorAll('.modal-close');

// Add event listeners for modal close buttons
modalCloseButtons.forEach(button => {
  events.addSafeEventListener(button, 'click', () => {
    // Find the closest modal parent
    const modal = button.closest('.modal');
    if (modal) {
      modal.classList.remove('show');
      logger.info(`Closing modal: ${modal.id || 'unnamed modal'}`);
    }
  });
});

// Close modals when clicking outside the content
document.querySelectorAll('.modal').forEach(modal => {
  events.addSafeEventListener(modal, 'click', (e) => {
    if (e.target === modal) {
      modal.classList.remove('show');
      logger.info(`Closing modal via background click: ${modal.id || 'unnamed modal'}`);
    }
  });
});

// Application state
const state = {
  selectedFiles: [],
  processedSamples: [], // Current processed samples
  allSamples: [], // All samples from file system
  categories: {},
  currentCategory: 'all',
  isProcessing: false,
  viewMode: 'grid',
  samplesViewMode: 'current', // 'current' or 'all'
  progress: 0,
  // Add a placeholder visualization state to prevent undefined errors
  visualization: {
    selectedSamples: [],
    plotData: null,
    xFeature: 'spectral_centroid',
    yFeature: 'energy',
    colorFeature: 'category',
    currentAudio: null,
    audioToggled: false
  }
};

// Event Listeners - Using safe event handlers
// Main button actions
if (selectFilesBtn) events.addSafeEventListener(selectFilesBtn, 'click', selectFiles);
if (processBtn) events.addSafeEventListener(processBtn, 'click', processAudioFiles);
if (gridViewBtn) events.addSafeEventListener(gridViewBtn, 'click', () => setViewMode('grid'));
if (listViewBtn) events.addSafeEventListener(listViewBtn, 'click', () => setViewMode('list'));

// Tab controls and visualization controls removed to focus on sample classification
// Visualization axis controls removed to focus on sample classification

// Clear files button
const clearFilesBtn = document.getElementById('clearFilesBtn');
if (clearFilesBtn) {
  events.addSafeEventListener(clearFilesBtn, 'click', clearAllFiles);
}

// Search functionality
const searchInput = document.getElementById('searchInput');
const clearSearchBtn = document.getElementById('clearSearchBtn');
if (searchInput) {
  // Add debounce to avoid excessive re-renders
  let searchTimeout;
  
  // Use simple event handler
  events.addSafeEventListener(searchInput, 'input', () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      displaySamples();
    }, 300);
  });
  
  // Add 'Enter' key handler
  events.addSafeEventListener(searchInput, 'keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      displaySamples();
    }
  });
}

// Clear search button
if (clearSearchBtn) {
  events.addSafeEventListener(clearSearchBtn, 'click', () => {
    if (searchInput) {
      searchInput.value = '';
      displaySamples();
      logger.info('Search cleared');
    }
  });
}

// File drag and drop events
if (fileUploadArea) {
  events.addSafeEventListener(fileUploadArea, 'dragover', handleDragOver);
  events.addSafeEventListener(fileUploadArea, 'dragleave', handleDragLeave);
  events.addSafeEventListener(fileUploadArea, 'drop', handleDrop);
}

// Functions

/**
 * Open file dialog and select audio files
 */
async function selectFiles() {
  try {
    const files = await ipcRenderer.invoke('select-files');
    if (files && files.length > 0) {
      addFilesToSelection(files);
      updateProcessButton();
    }
  } catch (error) {
    showStatus(`Error selecting files: ${error.message}`, 'error');
  }
}

/**
 * Function to get app storage directory (no longer user-facing)
 * This is now handled internally by the app
 */
async function getAppStorageDirectory() {
  try {
    // Get the app's internal storage directory from main process
    const appDir = await ipcRenderer.invoke('get-app-storage-directory');
    showStatus('Using internal app storage for processed samples', 'info');
    return appDir;
  } catch (error) {
    logger.error(`Error getting app storage directory: ${error.message}`);
    return null;
  }
}

/**
 * Load previously processed samples from the organized-samples directory
 */
async function loadSavedSamples() {
  try {
    logger.info('Loading previously processed samples...');
    showStatus('Loading previously processed samples...', 'info');
    
    // Get the app's storage directory
    const appStorageDir = await getAppStorageDirectory();
    
    if (!appStorageDir) {
      logger.error('Could not get app storage directory');
      showStatus('Error loading saved samples: Could not access storage directory', 'error');
      return;
    }
    
    logger.info(`Attempting to load samples from: ${appStorageDir}`);
    
    // Get samples from the organized-samples directory using the main process
    const result = await ipcRenderer.invoke('get-samples', appStorageDir);
    
    if (result.success && result.samples && result.samples.length > 0) {
      logger.info(`Successfully found ${result.samples.length} samples`);
      
      // Check for path issues and fix them if necessary
      result.samples.forEach(sample => {
        if (!sample.path || !fs.existsSync(sample.path)) {
          logger.warn(`Sample path does not exist: ${sample.path}`);
          
          // Try to fix the path
          if (sample.category && sample.name) {
            const potentialPaths = [
              path.join(appStorageDir, sample.category, sample.name),
              path.join(process.cwd(), 'processed_samples', 'organized-samples', sample.category, sample.name),
              path.join(__dirname, '..', 'processed_samples', 'organized-samples', sample.category, sample.name)
            ];
            
            for (const potentialPath of potentialPaths) {
              if (fs.existsSync(potentialPath)) {
                logger.info(`Fixed path for sample ${sample.name}: ${potentialPath}`);
                sample.path = potentialPath;
                break;
              }
            }
          }
        }
      });
      
      // Only store samples in allSamples, leaving processedSamples empty on startup
      // This keeps Current Samples view empty when the app starts
      state.processedSamples = []; // Keep empty for Current Samples view
      
      // Populate only allSamples for the "All Samples" view
      state.allSamples = [...result.samples];
      
      // Build categories for the current view mode (Current Samples view)
      buildCategoriesFromSamples();
      
      // Switch to samples view if there are samples in All Samples view
      // Even if Current Samples view is empty
      if (state.allSamples.length > 0) {
        fileUploadArea.classList.add('hidden');
        samplesArea.classList.remove('hidden');
        
        // Always start with Current Samples view on app init
        state.samplesViewMode = 'current';
        
        // Make sure the UI buttons reflect the correct state
        if (currentSamplesBtn && allSamplesBtn) {
          currentSamplesBtn.classList.add('active');
          allSamplesBtn.classList.remove('active');
        }
        
        // Build categories for current view (which will be empty)
        buildCategoriesFromSamples();
        
        displaySamples();
        
        showStatus(`Current Samples view is empty. ${state.allSamples.length} previously processed samples are available in All Samples view.`, 'info');
        logger.info(`Loaded ${state.allSamples.length} samples for All Samples view`);
      }
    } else {
      if (result.error) {
        logger.warn(`Error from get-samples: ${result.error}`);
      }
      logger.info('No previously processed samples found');
      showStatus('No previously processed samples found', 'info');
    }
  } catch (error) {
    logger.error(`Error loading saved samples: ${error.message}`);
    showStatus(`Error loading saved samples: ${error.message}`, 'error');
  }
}

/**
 * Process selected audio files
 */
async function processAudioFiles() {
  if (!state.selectedFiles.length || state.isProcessing) {
    return;
  }

  try {
    state.isProcessing = true;
    state.progress = 0;
    updateUI();
    
    // Get and log the app storage directory where samples will be saved
    const appStorageDir = await getAppStorageDirectory();
    logger.info(`Using app storage directory for samples: ${appStorageDir}`);
    
    // Show progress bar only when processing starts
    const progressWrapper = document.querySelector('.progress-wrapper');
    if (progressWrapper) progressWrapper.style.display = 'flex';
    
    // Check if deep analysis is enabled
    const useDeepAnalysis = useDeepAnalysisCheckbox && useDeepAnalysisCheckbox.checked;
    
    // Show initial message
    if (useDeepAnalysis) {
      showStatus('Starting deep audio analysis. This may take longer...', 'processing');
    } else {
      showStatus('Starting quick filename-based classification...', 'processing');
    }
    
    // Update progress bar
    updateProgress({
      progress: 0,
      message: 'Starting classification...',
      files_processed: 0,
      files_total: state.selectedFiles.length
    });
    
    // Set up event listener for progress updates
    ipcRenderer.removeAllListeners('classification-progress');
    ipcRenderer.on('classification-progress', (event, data) => {
      updateProgress(data);
    });
    
    // Set up event listener for errors
    ipcRenderer.removeAllListeners('classification-error');
    ipcRenderer.on('classification-error', (event, data) => {
      showStatus(`Error: ${data.error}`, 'error');
    });

    // Send files for processing with the deep analysis flag
    // Using app's internal storage instead of requiring output directory
    const result = await ipcRenderer.invoke('process-audio', {
      files: state.selectedFiles,
      useDeepAnalysis: useDeepAnalysis
    });

    if (result.success) {
      // Update processed samples for current view
      state.processedSamples = result.result.samples || [];
      
      // Also add the new samples to allSamples for the "All Samples" view
      if (state.processedSamples.length > 0) {
        // Merge with existing all samples, avoiding duplicates
        const newSampleIds = state.processedSamples.map(sample => sample.id);
        
        // Remove any existing samples with the same IDs to avoid duplicates
        state.allSamples = state.allSamples.filter(sample => !newSampleIds.includes(sample.id));
        
        // Add the new samples
        state.allSamples = [...state.allSamples, ...state.processedSamples];
      }
      
      // Build categories based on current view mode
      if (state.samplesViewMode === 'current') {
        buildCategoriesFromSamples();
      } else {
        buildCategoriesFromAllSamples();
      }
      showStatus(`Processed ${state.processedSamples.length} audio files`, 'success');
      
      // Switch to samples view
      fileUploadArea.classList.add('hidden');
      samplesArea.classList.remove('hidden');
      
      // Reset to current view mode when new samples are processed
      state.samplesViewMode = 'current';
      currentSamplesBtn.classList.add('active');
      allSamplesBtn.classList.remove('active');
      
      displaySamples();
    } else {
      showStatus(`Error: ${result.error}`, 'error');
    }
  } catch (error) {
    showStatus(`Error processing files: ${error.message}`, 'error');
  } finally {
    state.isProcessing = false;
    updateUI();
    
    // Keep progress bar visible with 100% completion
    const progressWrapper = document.querySelector('.progress-wrapper');
    if (progressWrapper) {
      // Keep progress bar visible with successful completion
      progressBar.style.width = '100%';
      progressBar.classList.add('success');
      
      // We'll let the user see the completion status, don't hide it
      // progressWrapper.style.display = 'none';
    }
  }
}

/**
 * Update progress bar and message
 */
function updateProgress(data) {
  // Make sure the progress wrapper is always visible during updates
  const progressWrapper = document.querySelector('.progress-wrapper');
  if (progressWrapper && progressWrapper.style.display !== 'flex') {
    progressWrapper.style.display = 'flex';
  }
  
  // Handle different parameter formats for backward compatibility
  let percent, message, filesProcessed, filesTotal;
  
  if (typeof data === 'object') {
    percent = data.progress || 0;
    message = data.message || 'Processing...';
    filesProcessed = data.files_processed;
    filesTotal = data.files_total;
  } else {
    // Legacy format where first parameter is percent, second is message
    percent = data;
    message = arguments[1] || 'Processing...';
  }
  
  state.progress = percent;
  
  // Add active class for animation when processing is happening
  if (percent > 0 && percent < 100) {
    progressBar.classList.add('active');
  } else {
    progressBar.classList.remove('active');
  }
  
  // Simple, direct update of the progress bar width
  progressBar.style.width = `${percent}%`;
  
  // Ensure the bar is visible by setting a background color directly
  progressBar.style.backgroundColor = '#8e24aa'; // Purple color
  progressBar.style.display = 'block';
  
  // Remove any classes that might interfere
  progressBar.classList.remove('indeterminate');
  
  // Update progress percentage text with more detailed information
  if (progressPercentage) {
    if (filesProcessed !== undefined && filesTotal !== undefined) {
      // Show detailed count of processed files
      progressPercentage.textContent = `${Math.round(percent)}% (${filesProcessed}/${filesTotal} files)`;
      
      // Add a title attribute for a tooltip on hover
      progressPercentage.setAttribute('title', `Processed ${filesProcessed} of ${filesTotal} files`);
    } else {
      progressPercentage.textContent = `${Math.round(percent)}%`;
      progressPercentage.removeAttribute('title');
    }
  }
  
  // Update status message
  const statusMessage = statusBar.querySelector('.status-message');
  if (statusMessage) {
    // If we have files info but it's not in the message, add it
    if (filesProcessed !== undefined && filesTotal !== undefined && !message.includes(`${filesProcessed}/${filesTotal}`)) {
      statusMessage.textContent = `${message} (${filesProcessed}/${filesTotal})`;
    } else {
      statusMessage.textContent = message;
    }
  }
}

/**
 * Add files to the selection list
 */
function addFilesToSelection(filePaths) {
  const newFiles = filePaths.filter(file => {
    // Check if file is already in selection
    return !state.selectedFiles.includes(file);
  });
  
  state.selectedFiles = [...state.selectedFiles, ...newFiles];
  updateFilesList();
}

/**
 * Update the files list in the UI
 */
function updateFilesList() {
  filesList.innerHTML = '';
  
  if (state.selectedFiles.length === 0) {
    return;
  }
  
  state.selectedFiles.forEach((file, index) => {
    const fileItem = document.createElement('div');
    fileItem.className = 'file-item';
    fileItem.draggable = true;
    fileItem.setAttribute('data-index', index);
    
    // Get just the filename
    const fileName = file.split(/[\\/]/).pop();
    
    fileItem.innerHTML = `
      <div class="file-name">${fileName}</div>
      <button class="file-remove" data-index="${index}">✕</button>
    `;
    
    // Add drag & drop event listeners
    events.addSafeEventListener(fileItem, 'dragstart', handleFileDragStart);
    events.addSafeEventListener(fileItem, 'dragover', handleFileDragOver);
    events.addSafeEventListener(fileItem, 'dragleave', handleFileDragLeave);
    events.addSafeEventListener(fileItem, 'drop', handleFileDrop);
    events.addSafeEventListener(fileItem, 'dragend', handleFileDragEnd);
    
    filesList.appendChild(fileItem);
  });
  
  // Add remove event listeners
  document.querySelectorAll('.file-remove').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation(); // Prevent event bubbling
      const index = parseInt(e.target.getAttribute('data-index'));
      removeFile(index);
    });
  });
}

/**
 * Handle file drag start
 */
function handleFileDragStart(e) {
  // Store the dragged element index
  e.dataTransfer.setData('text/plain', e.target.getAttribute('data-index'));
  
  // Add dragging class
  this.classList.add('dragging');
  
  // For Firefox compatibility
  e.dataTransfer.effectAllowed = 'move';
}

/**
 * Handle file drag over
 */
function handleFileDragOver(e) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  this.classList.add('drag-over');
}

/**
 * Handle file drag leave
 */
function handleFileDragLeave(e) {
  this.classList.remove('drag-over');
}

/**
 * Handle file drop
 */
function handleFileDrop(e) {
  e.preventDefault();
  this.classList.remove('drag-over');
  
  // Get source and target indices
  const sourceIndex = parseInt(e.dataTransfer.getData('text/plain'));
  const targetIndex = parseInt(this.getAttribute('data-index'));
  
  if (sourceIndex !== targetIndex) {
    // Reorder the files
    const [movedFile] = state.selectedFiles.splice(sourceIndex, 1);
    state.selectedFiles.splice(targetIndex, 0, movedFile);
    
    // Update the UI
    updateFilesList();
    
    // Show status message
    showStatus('Files reordered', 'info');
  }
}

/**
 * Handle file drag end
 */
function handleFileDragEnd(e) {
  // Remove dragging class from all items
  document.querySelectorAll('.file-item').forEach(item => {
    item.classList.remove('dragging');
    item.classList.remove('drag-over');
  });
}

/**
 * Remove a file from the selection
 */
function removeFile(index) {
  state.selectedFiles.splice(index, 1);
  updateFilesList();
  updateProcessButton();
}

/**
 * Update the process button state
 */
function updateProcessButton() {
  processBtn.disabled = !(state.selectedFiles.length > 0);
}

/**
 * Build categories object from processed samples
 */
/**
 * Build categories based on the current samples set (processed samples)
 */
function buildCategoriesFromSamples() {
  const categories = {
    all: { name: 'All Samples', count: state.processedSamples.length }
  };
  
  state.processedSamples.forEach(sample => {
    if (!categories[sample.category]) {
      categories[sample.category] = {
        name: capitalizeFirstLetter(sample.category),
        count: 0
      };
    }
    categories[sample.category].count++;
  });
  
  state.categories = categories;
  updateCategoriesList();
}

/**
 * Build categories based on all samples (used when in "All Samples" view)
 */
function buildCategoriesFromAllSamples() {
  const categories = {
    all: { name: 'All Samples', count: state.allSamples.length }
  };
  
  state.allSamples.forEach(sample => {
    if (!categories[sample.category]) {
      categories[sample.category] = {
        name: capitalizeFirstLetter(sample.category),
        count: 0
      };
    }
    categories[sample.category].count++;
  });
  
  state.categories = categories;
  updateCategoriesList();
}

/**
 * Update the categories list in the UI
 */
function updateCategoriesList() {
  categoriesList.innerHTML = '';
  
  Object.keys(state.categories).forEach(categoryId => {
    const category = state.categories[categoryId];
    const categoryItem = document.createElement('li');
    categoryItem.setAttribute('data-category', categoryId);
    if (categoryId === state.currentCategory) {
      categoryItem.classList.add('active');
    }
    
    // Create a container for the category content
    const categoryContent = document.createElement('div');
    categoryContent.className = 'category-content';
    categoryContent.innerHTML = `
      <span>${category.name}</span>
      <span class="category-count">${category.count}</span>
    `;
    
    // Add click event to the content div only
    categoryContent.addEventListener('click', () => {
      setCurrentCategory(categoryId);
    });
    
    // Create the menu button container
    const menuContainer = document.createElement('div');
    menuContainer.className = 'sample-menu category-menu';
    
    // Show menu if the category has samples
    if (category.count > 0) {
      // Create the menu button with 3 dots
      const menuBtn = document.createElement('button');
      menuBtn.className = 'menu-btn';
      menuBtn.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 24 24" class="menu-icon">
          <path d="M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z" fill="currentColor"/>
        </svg>
      `;
      
      // Create the dropdown menu
      const menuDropdown = document.createElement('div');
      menuDropdown.className = 'menu-dropdown';
      menuDropdown.innerHTML = `
        <button class="menu-item export-category-btn">Export All ${category.name}</button>
      `;
      
      // Add event to toggle the dropdown
      menuBtn.addEventListener('click', (e) => {
        e.stopPropagation(); // Prevent category selection
        menuDropdown.classList.toggle('show');
        
        // Hide all other open menus
        document.querySelectorAll('.menu-dropdown.show').forEach(dropdown => {
          if (dropdown !== menuDropdown) {
            dropdown.classList.remove('show');
          }
        });
      });
      
      // Add event for the export button
      menuDropdown.querySelector('.export-category-btn').addEventListener('click', (e) => {
        e.stopPropagation();
        exportCategorySamples(categoryId);
        menuDropdown.classList.remove('show');
      });
      
      menuContainer.appendChild(menuBtn);
      menuContainer.appendChild(menuDropdown);
    }
    
    // Add elements to the category item
    categoryItem.appendChild(categoryContent);
    categoryItem.appendChild(menuContainer);
    
    categoriesList.appendChild(categoryItem);
  });
}

/**
 * Set current category and update display
 */
function setCurrentCategory(categoryId) {
  state.currentCategory = categoryId;
  updateCategoriesList();
  displaySamples();
}

/**
 * Generate a waveform visualization for an audio sample
 * This implementation uses a simple direct approach without relying on librosa or waveform-data
 */
async function generateWaveform(audioPath, waveformContainer) {
  waveformContainer.innerHTML = '<div class="waveform-loading">Loading...</div>';
  
  try {
    // First, check if the audio file actually exists
    if (!fs.existsSync(audioPath)) {
      throw new Error(`Audio file not found: ${audioPath}`);
    }
    
    // Clear the container
    waveformContainer.innerHTML = '';
    
    // Create a canvas for our waveform
    const canvas = document.createElement('canvas');
    canvas.width = waveformContainer.clientWidth || 200;
    canvas.height = 60;
    waveformContainer.appendChild(canvas);
    
    const ctx = canvas.getContext('2d');
    
    // Background
    ctx.fillStyle = 'rgba(142, 36, 170, 0.1)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Get the audio data using Web Audio API
    // Use a shared AudioContext to avoid hitting the limit of audio streams
    if (!window.sharedAudioContext) {
      window.sharedAudioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    const audioContext = window.sharedAudioContext;
    
    // Use IPC to get the audio data from the main process to avoid permissions issues
    const audioData = await ipcRenderer.invoke('get-audio-data', audioPath);
    
    if (!audioData || !audioData.success) {
      throw new Error(audioData.error || 'Failed to load audio data');
    }
    
    // Decode the audio data
    const audioBuffer = await audioContext.decodeAudioData(audioData.buffer.buffer);
    
    // Get the audio samples
    const channelData = audioBuffer.getChannelData(0); // Get the first channel
    
    // Track this audioBuffer for cleanup
    if (!window.activeAudioBuffers) {
      window.activeAudioBuffers = [];
    }
    window.activeAudioBuffers.push(audioBuffer);
    
    // Calculate how many samples to skip to fit in our canvas
    const skipCount = Math.ceil(channelData.length / canvas.width);
    
    // Draw the waveform
    ctx.fillStyle = '#8e24aa'; // Purple color matching the theme
    
    const barWidth = 2;
    const gap = 1;
    const centerY = canvas.height / 2;
    
    for (let i = 0; i < canvas.width; i++) {
      const x = i * (barWidth + gap);
      
      // Get the sample data for this position
      const sampleIndex = Math.floor(i * skipCount);
      let height = 0;
      
      // Calculate the average amplitude for this segment
      let sum = 0;
      let count = 0;
      
      for (let j = 0; j < skipCount && (sampleIndex + j) < channelData.length; j++) {
        sum += Math.abs(channelData[sampleIndex + j]);
        count++;
      }
      
      if (count > 0) {
        const amplitude = sum / count;
        height = amplitude * canvas.height * 3; // Scale it up for visibility
        height = Math.min(height, canvas.height * 0.9); // Cap the height
      }
      
      // Draw bar
      ctx.fillRect(x, centerY - height/2, barWidth, height);
    }
    
    // Add a shimmer effect with a gradient overlay
    const gradient = ctx.createLinearGradient(0, 0, canvas.width, 0);
    gradient.addColorStop(0, 'rgba(255, 255, 255, 0.1)');
    gradient.addColorStop(0.5, 'rgba(255, 255, 255, 0.2)');
    gradient.addColorStop(1, 'rgba(255, 255, 255, 0.1)');
    
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Return successful
    return canvas;
    
  } catch (error) {
    console.error('Error generating waveform visualization:', error);
    
    // Create a simple visual indicator as fallback
    waveformContainer.innerHTML = '';
    const fallbackVisual = document.createElement('div');
    fallbackVisual.className = 'fallback-waveform';
    fallbackVisual.style.height = '60px';
    fallbackVisual.style.background = 'linear-gradient(90deg, rgba(142,36,170,0.2) 0%, rgba(142,36,170,0.8) 50%, rgba(142,36,170,0.2) 100%)';
    fallbackVisual.style.borderRadius = '3px';
    waveformContainer.appendChild(fallbackVisual);
    
    // Log error properly
    logger.error('Error generating waveform: ' + error.message);
  }
}

/**
 * Filter samples by search query
 */
function filterSamples(samples, searchQuery) {
  if (!searchQuery) {
    return samples;
  }
  
  const query = searchQuery.toLowerCase();
  return samples.filter(sample => {
    // Search in sample name
    if (sample.name && sample.name.toLowerCase().includes(query)) {
      return true;
    }
    
    // Search in category
    if (sample.category && sample.category.toLowerCase().includes(query)) {
      return true;
    }
    
    // Search in mood
    if (sample.mood && sample.mood.toLowerCase().includes(query)) {
      return true;
    }
    
    // Search in path (filenames)
    if (sample.path && sample.path.toLowerCase().includes(query)) {
      return true;
    }
    
    return false;
  });
}

/**
 * Display samples in the grid
 */
function displaySamples() {
  samplesGrid.innerHTML = '';
  
  // Choose which sample set to use based on view mode
  const samplesSource = state.samplesViewMode === 'current' ? state.processedSamples : state.allSamples;
  
  // Show a message if no samples are available in the current view
  if (samplesSource.length === 0) {
    if (state.samplesViewMode === 'current') {
      samplesGrid.innerHTML = `<div class="empty-state">No samples processed in this session yet. Select audio files and click "Process Samples" to analyze them.</div>`;
    } else {
      samplesGrid.innerHTML = `<div class="empty-state">No previously processed samples found. Process audio files to see them here.</div>`;
    }
    // Return early, no need to continue
    return;
  }
  
  // Make sure categories reflect the current view mode
  if (state.samplesViewMode === 'current') {
    // Only do this if we need to rebuild categories (avoid unnecessary updates)
    if (state.categories.all?.count !== state.processedSamples.length) {
      buildCategoriesFromSamples();
    }
  } else {
    // Only do this if we need to rebuild categories (avoid unnecessary updates)
    if (state.categories.all?.count !== state.allSamples.length) {
      buildCategoriesFromAllSamples();
    }
  }
  
  // First filter by category
  let filteredSamples = state.currentCategory === 'all' 
    ? samplesSource 
    : samplesSource.filter(sample => sample.category === state.currentCategory);
  
  // Then filter by search query if there is one
  const searchInput = document.getElementById('searchInput');
  if (searchInput && searchInput.value) {
    filteredSamples = filterSamples(filteredSamples, searchInput.value);
    
    // Show "no results" message if needed
    if (filteredSamples.length === 0) {
      const noResults = document.createElement('div');
      noResults.className = 'no-results';
      noResults.textContent = `No samples found matching "${searchInput.value}"`;
      samplesGrid.appendChild(noResults);
      return;
    }
  }
  
  // Keep track of currently playing audio
  if (!state.currentAudio) {
    state.currentAudio = null;
    state.currentPlayButton = null;
  }
  
  filteredSamples.forEach(sample => {
    const sampleCard = document.importNode(sampleCardTemplate.content, true);
    const card = sampleCard.querySelector('.sample-card');
    
    // Set sample data
    card.setAttribute('data-id', sample.id);
    
    // Set the sample title text
    const sampleTitle = sampleCard.querySelector('.sample-title');
    if (sampleTitle) {
      sampleTitle.textContent = sample.name;
    }
    
    // Set up menu event listeners
    const menuBtn = sampleCard.querySelector('.menu-btn');
    const menuDropdown = sampleCard.querySelector('.menu-dropdown');
    const exportSampleBtn = sampleCard.querySelector('.export-sample-btn');
    const exportFolderBtn = sampleCard.querySelector('.export-folder-btn');
    
    // Toggle menu visibility
    if (menuBtn && menuDropdown) {
      menuBtn.addEventListener('click', (e) => {
        e.stopPropagation(); // Prevent click from bubbling
        menuDropdown.classList.toggle('show');
      });
      
      // Close dropdown when clicking elsewhere
      document.addEventListener('click', () => {
        menuDropdown.classList.remove('show');
      });
    }
    
    // Export single sample
    if (exportSampleBtn) {
      exportSampleBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        if (menuDropdown) menuDropdown.classList.remove('show');
        
        try {
          showStatus('Exporting sample...', 'processing');
          
          const result = await ipcRenderer.invoke('export-sample', {
            samplePath: sample.path,
            sampleName: sample.name
          });
          
          if (result.success) {
            showStatus(`Sample exported successfully`, 'success');
          } else if (result.canceled) {
            showStatus('Export canceled', 'info');
          } else {
            showStatus(`Error exporting sample: ${result.error}`, 'error');
          }
        } catch (error) {
          console.error(`Error exporting sample: ${error.message}`);
          showStatus(`Error exporting sample: ${error.message}`, 'error');
        }
      });
    }
    
    // Export folder of samples
    if (exportFolderBtn) {
      exportFolderBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        if (menuDropdown) menuDropdown.classList.remove('show');
        
        try {
          showStatus(`Preparing to export ${sample.category} samples...`, 'processing');
          
          const result = await ipcRenderer.invoke('export-samples-to-folder', {
            category: sample.category
          });
          
          if (result.success) {
            showStatus(`Exported ${result.count} samples successfully`, 'success');
          } else if (result.canceled) {
            showStatus('Export canceled', 'info');
          } else {
            showStatus(`Error exporting samples: ${result.error}`, 'error');
          }
        } catch (error) {
          console.error(`Error exporting samples: ${error.message}`);
          showStatus(`Error exporting samples: ${error.message}`, 'error');
        }
      });
    }
    
    sampleCard.querySelector('.sample-category').textContent = sample.category;
    sampleCard.querySelector('.sample-mood').textContent = sample.mood;
    
    // Hide find similar button as this functionality is currently disabled
    const findSimilarBtn = sampleCard.querySelector('.find-similar-btn');
    if (findSimilarBtn) {
      findSimilarBtn.style.display = 'none';
    }
    
    // Get the waveform container
    const waveformContainer = sampleCard.querySelector('.sample-waveform');
    
    // Generate waveform visualization
    if (waveformContainer && sample.path) {
      // Add a loading indicator
      waveformContainer.innerHTML = '<div class="waveform-loading">Loading waveform...</div>';
      
      // Generate the waveform visualization asynchronously
      generateWaveform(sample.path, waveformContainer).catch(error => {
        console.error(`Failed to generate waveform for ${sample.name}:`, error);
        // Show a placeholder if waveform generation fails
        waveformContainer.innerHTML = '<div class="waveform-placeholder"></div>';
      });
    }
    
    // Add play button event
    const playBtn = sampleCard.querySelector('.play-btn');
    const playIcon = playBtn.querySelector('.play-icon');
    const stopIcon = playBtn.querySelector('.stop-icon');
    const volumeControl = sampleCard.querySelector('.volume-control');
    const volumeSlider = sampleCard.querySelector('.volume-slider');
    const volumeIcon = sampleCard.querySelector('.volume-icon');
    
    // Function to toggle play/pause
    const togglePlayback = () => {
      // Stop any visualization audio first
      // Visualization audio stopping code removed to focus on sample classification
      
      // If we already have audio playing, stop it
      if (state.currentAudio) {
        state.currentAudio.pause();
        state.currentAudio = null;
        
        // Reset previous button if it's not this one
        if (state.currentPlayButton && state.currentPlayButton !== playBtn) {
          const prevPlayIcon = state.currentPlayButton.querySelector('.play-icon');
          const prevStopIcon = state.currentPlayButton.querySelector('.stop-icon');
          const prevVolumeControl = state.currentPlayButton.parentNode.querySelector('.volume-control');
          
          // Also remove any loading spinner
          const prevSpinner = state.currentPlayButton.querySelector('.audio-loading-spinner');
          if (prevSpinner) prevSpinner.remove();
          
          if (prevPlayIcon) prevPlayIcon.style.display = '';
          if (prevStopIcon) prevStopIcon.style.display = 'none';
          if (prevVolumeControl) prevVolumeControl.style.display = 'none';
        }
      }
      
      // If this is already the playing button, just stop it
      if (state.currentPlayButton === playBtn) {
        playIcon.style.display = '';
        stopIcon.style.display = 'none';
        volumeControl.style.display = 'none';
        state.currentPlayButton = null;
        return;
      }
      
      // Otherwise, play the new audio
      const audio = new Audio();
      
      // Add loading indicator
      playIcon.style.display = 'none';
      stopIcon.style.display = 'none';
      
      // Show loading spinner
      const loadingIndicator = document.createElement('div');
      loadingIndicator.className = 'audio-loading-spinner';
      loadingIndicator.innerHTML = '<div class="spinner"></div>';
      playBtn.appendChild(loadingIndicator);
      
      // Setup audio events
      audio.addEventListener('canplay', () => {
        // Remove loading indicator
        const spinner = playBtn.querySelector('.audio-loading-spinner');
        if (spinner) spinner.remove();
        
        // Show stop icon
        stopIcon.style.display = '';
        
        // Start playing
        audio.play().catch(err => {
          logger.error('Audio playback error: ' + err.message);
          
          // Reset UI on error
          playIcon.style.display = '';
          stopIcon.style.display = 'none';
          volumeControl.style.display = 'none';
        });
      });
      
      // When playback ends, reset UI
      audio.addEventListener('ended', () => {
        // Reset button when audio ends
        playIcon.style.display = '';
        stopIcon.style.display = 'none';
        volumeControl.style.display = 'none';
        state.currentAudio = null;
        state.currentPlayButton = null;
      });
      
      // Handle errors
      audio.addEventListener('error', (e) => {
        console.error('Audio error: ' + (audio.error ? audio.error.message : 'Unknown error'));
        
        // Remove loading indicator
        const spinner = playBtn.querySelector('.audio-loading-spinner');
        if (spinner) spinner.remove();
        
        // Reset UI
        playIcon.style.display = '';
        stopIcon.style.display = 'none';
        volumeControl.style.display = 'none';
        
        // Create and show an error badge on the play button
        const errorBadge = document.createElement('div');
        errorBadge.className = 'audio-error-badge';
        errorBadge.setAttribute('title', 'Failed to play audio');
        errorBadge.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
        playBtn.appendChild(errorBadge);
        
        // Show error notification with more details
        let errorMsg = `Failed to play audio: ${sample.name}`;
        if (audio.error) {
          // Add more helpful context based on the error code
          switch (audio.error.code) {
            case MediaError.MEDIA_ERR_ABORTED:
              errorMsg += ' - Playback aborted by user';
              break;
            case MediaError.MEDIA_ERR_NETWORK:
              errorMsg += ' - Network error occurred';
              break;
            case MediaError.MEDIA_ERR_DECODE:
              errorMsg += ' - Audio format not supported or file is corrupted';
              break;
            case MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED:
              errorMsg += ' - Audio file format is not supported';
              break;
            default:
              errorMsg += ' - Unknown error';
          }
        }
        showStatus(errorMsg, 'error');
        
        // Reset state
        state.currentAudio = null;
        state.currentPlayButton = null;
      });
      
      // Set the source and load the audio
      try {
        // For Electron's renderer process, we should use a different approach for special characters
        // Instead of trying to encode the URI, let's use the audio element's ability to load files via Blob
        
        console.log('Loading audio file: ' + sample.path);
        
        // For local file playback in Electron, we can read the file directly
        fs.readFile(sample.path, (err, data) => {
          if (err) {
            console.error('Error reading audio file:', err);
            showStatus(`Error reading audio file: ${err.message}`, 'error');
            
            // Reset UI on error
            const spinner = playBtn.querySelector('.audio-loading-spinner');
            if (spinner) spinner.remove();
            playIcon.style.display = '';
            stopIcon.style.display = 'none';
            volumeControl.style.display = 'none';
            return;
          }
          
          // Create a blob from the file data
          const blob = new Blob([data]);
          const objectURL = URL.createObjectURL(blob);
          
          // Set the audio source to the blob URL
          audio.src = objectURL;
          audio.volume = parseFloat(volumeSlider.value);
          audio.load();
          
          // Clean up the object URL when we're done with it
          audio.addEventListener('ended', () => {
            URL.revokeObjectURL(objectURL);
          });
          
          // Also clean up if there's an error
          audio.addEventListener('error', () => {
            URL.revokeObjectURL(objectURL);
          });
        });
      } catch (err) {
        console.error('Error setting up audio playback:', err);
        showStatus(`Error with audio playback: ${err.message}`, 'error');
        
        // Reset UI
        const spinner = playBtn.querySelector('.audio-loading-spinner');
        if (spinner) spinner.remove();
        playIcon.style.display = '';
        stopIcon.style.display = 'none';
        volumeControl.style.display = 'none';
      }
      
      // Update UI
      volumeControl.style.display = 'flex';
      
      // Update state
      state.currentAudio = audio;
      state.currentPlayButton = playBtn;
    };
    
    // Add click event to play button
    playBtn.addEventListener('click', togglePlayback);
    
    // Volume slider event
    volumeSlider.addEventListener('input', () => {
      if (state.currentAudio) {
        state.currentAudio.volume = parseFloat(volumeSlider.value);
      }
    });
    
    // Volume icon click to toggle mute
    volumeIcon.addEventListener('click', () => {
      if (state.currentAudio) {
        if (state.currentAudio.volume > 0) {
          // Store the current volume before muting
          volumeSlider.dataset.prevVolume = volumeSlider.value;
          volumeSlider.value = 0;
          state.currentAudio.volume = 0;
        } else {
          // Restore previous volume
          const prevVolume = volumeSlider.dataset.prevVolume || 0.7;
          volumeSlider.value = prevVolume;
          state.currentAudio.volume = parseFloat(prevVolume);
        }
      }
    });
    
    // Add data-id to identify this card for keyboard shortcuts
    playBtn.dataset.sampleId = sample.id;
    
    samplesGrid.appendChild(sampleCard);
  });
}

/**
 * Set view mode (grid or list)
 */
function setViewMode(mode) {
  state.viewMode = mode;
  
  // Update buttons
  gridViewBtn.classList.toggle('active', mode === 'grid');
  listViewBtn.classList.toggle('active', mode === 'list');
  
  // Update grid class
  samplesGrid.className = mode === 'grid' ? 'samples-grid' : 'samples-list';
}

/**
 * Show status message
 */
function showStatus(message, type = 'info') {
  const statusMessage = statusBar.querySelector('.status-message');
  statusMessage.textContent = message;
  statusMessage.className = 'status-message';
  statusMessage.classList.add(`status-${type}`);
  
  // Update progress bar
  if (type === 'processing') {
    progressBar.style.width = '100%';
    // Add indeterminate animation
    progressBar.classList.add('indeterminate');
  } else {
    progressBar.style.width = '0%';
    progressBar.classList.remove('indeterminate');
  }
}

/**
 * Update UI based on application state
 */
function updateUI() {
  // Update process button
  processBtn.disabled = state.isProcessing || !(state.selectedFiles.length > 0 && state.outputDirectory);
  
  // Disable select buttons while processing
  selectFilesBtn.disabled = state.isProcessing;
  selectOutputBtn.disabled = state.isProcessing;
}

/**
 * Handle drag over event
 */
function handleDragOver(e) {
  e.preventDefault();
  e.stopPropagation();
  fileUploadArea.classList.add('dragover');
}

/**
 * Handle drag leave event
 */
function handleDragLeave(e) {
  e.preventDefault();
  e.stopPropagation();
  fileUploadArea.classList.remove('dragover');
}

/**
 * Handle drop event
 */
function handleDrop(e) {
  e.preventDefault();
  e.stopPropagation();
  fileUploadArea.classList.remove('dragover');
  
  const files = [];
  if (e.dataTransfer.items) {
    // Use DataTransferItemList interface to access the files
    for (let i = 0; i < e.dataTransfer.items.length; i++) {
      // If dropped items aren't files, reject them
      if (e.dataTransfer.items[i].kind === 'file') {
        const file = e.dataTransfer.items[i].getAsFile();
        const path = file.path;
        if (isAudioFile(path)) {
          files.push(path);
        }
      }
    }
  } else {
    // Use DataTransfer interface to access the files
    for (let i = 0; i < e.dataTransfer.files.length; i++) {
      const path = e.dataTransfer.files[i].path;
      if (isAudioFile(path)) {
        files.push(path);
      }
    }
  }
  
  if (files.length > 0) {
    addFilesToSelection(files);
    updateProcessButton();
  }
}

/**
 * Check if a file is an audio file
 */
function isAudioFile(filePath) {
  const validExtensions = ['mp3', 'wav', 'ogg', 'flac', 'aif', 'aiff'];
  const extension = filePath.split('.').pop().toLowerCase();
  return validExtensions.includes(extension);
}

/**
 * Capitalize first letter of a string
 */
function capitalizeFirstLetter(string) {
  return string.charAt(0).toUpperCase() + string.slice(1);
}

/**
 * Check if the audio system is working properly
 * @returns {boolean} True if the audio system is working, false otherwise
 */
function checkAudioSystem() {
  try {
    // Try to create an audio context
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    const testContext = new AudioContext();
    
    // If we got here, it means the audio context was created successfully
    console.log('Audio system check: Audio context created successfully');
    testContext.close();
    return true;
  } catch (error) {
    console.error('Audio system check failed:', error.message);
    showStatus('Warning: Audio playback may not work properly on this system', 'warning');
    return false;
  }
}

/**
 * Handle global keyboard shortcuts
 */
function handleKeyboardShortcuts(e) {
  // Space key for play/pause current audio
  if (e.code === 'Space' && !e.target.matches('input, textarea, button')) {
    e.preventDefault(); // Prevent space from scrolling the page
    
    if (state.currentPlayButton) {
      // If there's audio playing, simulate click on the button
      state.currentPlayButton.click();
    }
  }
  
  // Escape key to stop any playing audio or close modal
  if (e.code === 'Escape') {
    // Check if modal is open
    if (similarSamplesModal.classList.contains('show')) {
      similarSamplesModal.classList.remove('show');
      return;
    }
    
    // Stop all audio playback with our universal function
    if (stopAllAudio()) {
      logger.info('Audio playback stopped via Escape key');
    }
  }
}

/**
 * Stop all audio playback
 * This function stops grid sample audio
 */
function stopAllAudio() {
  let audioStopped = false;
  
  // Stop main grid audio
  if (state.currentAudio) {
    state.currentAudio.pause();
    
    // Reset UI
    if (state.currentPlayButton) {
      const playIcon = state.currentPlayButton.querySelector('.play-icon');
      const stopIcon = state.currentPlayButton.querySelector('.stop-icon');
      const volumeControl = state.currentPlayButton.parentNode.querySelector('.volume-control');
      
      // Remove any loading spinner if present
      const spinner = state.currentPlayButton.querySelector('.audio-loading-spinner');
      if (spinner) spinner.remove();
      
      if (playIcon) playIcon.style.display = '';
      if (stopIcon) stopIcon.style.display = 'none';
      if (volumeControl) volumeControl.style.display = 'none';
    }
    
    // Clear state
    state.currentAudio = null;
    state.currentPlayButton = null;
    audioStopped = true;
  }
  
  // Suspend and close any nodes currently in the shared AudioContext
  // This helps prevent the "too many audio streams" error
  if (window.sharedAudioContext) {
    try {
      // Get all active AudioNodes from the context and disconnect them
      const activeNodes = window.sharedAudioContext._activeNodes;
      if (activeNodes && activeNodes.length > 0) {
        activeNodes.forEach(node => {
          try {
            node.disconnect();
          } catch (e) {
            // Ignore errors from already disconnected nodes
          }
        });
      }
      
      // Clear any tracked audio buffers
      if (window.activeAudioBuffers && window.activeAudioBuffers.length > 0) {
        // There's no direct way to free AudioBuffers in JavaScript, 
        // but we can remove our references to them so they can be garbage collected
        window.activeAudioBuffers = [];
        logger.info('Cleared audio buffer references');
      }
      
      // Suspend the context to free audio resources
      window.sharedAudioContext.suspend();
      
      logger.info('Audio context suspended and nodes disconnected');
    } catch (e) {
      logger.error('Error cleaning up audio context: ' + e.message);
    }
  }
  
  if (audioStopped) {
    logger.info('All audio playback stopped');
  }
  
  return audioStopped;
}

/**
 * Find similar samples based on a reference sample
 */
async function findSimilarSamples(referenceSample) {
  if (!referenceSample) {
    showStatus('Cannot find similar samples: Missing reference sample', 'error');
    return;
  }
  
  try {
    showStatus('Finding similar samples...', 'processing');
    
    // Get the IPC renderer directly from Electron
    const { ipcRenderer } = require('electron');
    
    // Update the modal with the reference sample name
    const similarSamplesModal = document.getElementById('similarSamplesModal');
    const modalReferenceName = similarSamplesModal.querySelector('.reference-sample .sample-name');
    modalReferenceName.textContent = referenceSample.name || 'Unknown';
    
    // Show the modal with a loading indicator
    similarSamplesModal.classList.add('show');
    const similarSamplesList = similarSamplesModal.querySelector('.similar-samples-list');
    similarSamplesList.innerHTML = '<div class="loading">Finding similar samples...</div>';
    
    // Use the preset app storage directory instead of requiring user selection
    // Get similar samples from the main process
    const result = await ipcRenderer.invoke('find-similar-samples', {
      referenceSample: referenceSample.path,
      samplesDir: null, // Let the main process use the default samples directory
      maxResults: 10
    });
    
    if (result.success) {
      // Clear the loading indicator
      similarSamplesList.innerHTML = '';
      
      const similarSamples = result.result.samples || [];
      
      if (similarSamples.length === 0) {
        similarSamplesList.innerHTML = '<div class="no-results">No similar samples found</div>';
        return;
      }
      
      // Create a card for each similar sample
      similarSamples.forEach(sample => {
        const similarityPercentage = Math.round(sample.similarity * 100);
        
        const sampleCard = document.createElement('div');
        sampleCard.className = 'sample-card';
        
        sampleCard.innerHTML = `
          <div class="sample-info">
            <div class="sample-title">${sample.name}</div>
            <div class="sample-metadata">
              <span class="sample-category">${sample.category}</span>
              <span class="sample-mood">${sample.mood}</span>
              <span class="similarity-score">${similarityPercentage}%</span>
            </div>
            <div class="sample-actions">
              <button class="play-similar-btn">Play</button>
            </div>
          </div>
        `;
        
        // Add play button functionality
        const playBtn = sampleCard.querySelector('.play-similar-btn');
        playBtn.addEventListener('click', () => {
          // Stop any currently playing audio
          if (state.currentAudio) {
            state.currentAudio.pause();
            state.currentAudio = null;
          }
          
          // Play this sample
          const audio = new Audio(sample.path);
          audio.play();
          state.currentAudio = audio;
          
          // Update button text
          playBtn.textContent = 'Playing...';
          
          // Reset when done
          audio.addEventListener('ended', () => {
            playBtn.textContent = 'Play';
            state.currentAudio = null;
          });
        });
        
        similarSamplesList.appendChild(sampleCard);
      });
      
      showStatus('Similar samples found', 'success');
    } else {
      similarSamplesList.innerHTML = `<div class="error">Error: ${result.error}</div>`;
      showStatus(`Error finding similar samples: ${result.error}`, 'error');
    }
  } catch (error) {
    showStatus(`Error finding similar samples: ${error.message}`, 'error');
    const similarSamplesList = similarSamplesModal.querySelector('.similar-samples-list');
    similarSamplesList.innerHTML = `<div class="error">Error: ${error.message}</div>`;
  }
}

/**
 * Clear all selected files
 */
function clearAllFiles() {
  state.selectedFiles = [];
  updateFilesList();
  updateProcessButton();
  showStatus('All files cleared', 'info');
}

/**
 * Clear current session samples 
 */
function clearAllSamples() {
  // Use console directly for simplicity
  console.log('[INFO] Clearing current session samples');
  
  // Stop any playing audio first
  if (typeof stopAllAudio === 'function') {
    stopAllAudio();
  }
  
  // Clear only current session samples from state
  state.processedSamples = [];
  
  // Don't clear allSamples, as per user request
  // Just make sure we're in current view mode
  state.samplesViewMode = 'current'; 
  currentSamplesBtn.classList.add('active');
  allSamplesBtn.classList.remove('active');
  
  // Update categories for current view
  buildCategoriesFromSamples();
  
  // Update the current category
  state.currentCategory = 'all';
  
  // If all samples view has samples, keep the samples area visible
  // Otherwise show the file upload area
  if (state.allSamples.length > 0) {
    // Just update the grid with empty state message
    if (samplesGrid) {
      samplesGrid.innerHTML = '<div class="empty-state">No samples processed in this session yet. Select audio files and click "Process Samples" to analyze them.</div>';
    }
    // Keep samples area visible
    if (fileUploadArea && samplesArea) {
      fileUploadArea.classList.add('hidden');
      samplesArea.classList.remove('hidden');
    }
  } else {
    // No samples at all, show file upload area
    if (fileUploadArea && samplesArea) {
      samplesArea.classList.add('hidden');
      fileUploadArea.classList.remove('hidden');
    }
  }
  
  // Reset progress indicators
  if (progressBar) {
    progressBar.style.width = '0%';
    progressBar.classList.remove('indeterminate');
  }
  
  if (progressPercentage) {
    progressPercentage.textContent = '0%';
  }
  
  // Show success message
  showStatus('Current session samples cleared successfully', 'success');
  
  // Log the action - using the correct logger.info method
  logger.info('Current session samples cleared by user');
}

// Add global keyboard event listener
document.addEventListener('keydown', handleKeyboardShortcuts);

// Set up periodic audio resource cleanup to prevent memory leaks
setInterval(() => {
  // Only run cleanup if we have a shared audio context and no active playback
  if (window.sharedAudioContext && !state.currentAudio) {
    try {
      window.sharedAudioContext.suspend();
      
      // Clear any tracked audio buffers
      if (window.activeAudioBuffers && window.activeAudioBuffers.length > 0) {
        window.activeAudioBuffers = [];
      }
      
      logger.info('Periodic audio resource cleanup completed');
    } catch (e) {
      // Ignore errors from cleanup
    }
  }
}, 60000); // Run every minute

/**
 * Update the UI based on current state
 */
function updateUI() {
  // Disable/enable buttons based on processing state
  processBtn.disabled = state.isProcessing || !(state.selectedFiles.length > 0);
  selectFilesBtn.disabled = state.isProcessing;
  
  // Update progress bar
  if (state.isProcessing) {
    progressBar.style.width = `${state.progress}%`;
  } else {
    progressBar.style.width = '0%';
  }

  // Visualization UI update code has been removed to focus on sample classification
}

// Tab switching functionality removed to focus on sample classification

// Visualization function removed to focus on sample classification

/**
 * Open the sample selection modal
 */
function openSampleSelectionModal() {
  if (!state.processedSamples.length) {
    showStatus('No processed samples available for selection', 'error');
    return;
  }
  
  // Clear previous selection list
  const selectionList = document.querySelector('.sample-selection-list');
  if (selectionList) {
    selectionList.innerHTML = '';
    
    // Create checkboxes for all samples
    state.processedSamples.forEach((sample, index) => {
      const isSelected = state.visualization.selectedSamples.some(s => s.id === sample.id);
      
      const item = document.createElement('div');
      item.className = 'sample-selection-item';
      item.innerHTML = `
        <label>
          <input type="checkbox" value="${sample.id}" ${isSelected ? 'checked' : ''}>
          ${sample.name || sample.original_path.split('/').pop() || `Sample ${index + 1}`}
          <span class="item-category">(${sample.category})</span>
        </label>
      `;
      
      selectionList.appendChild(item);
    });
    
    // Add event listeners for select/deselect all buttons
    const selectAllBtn = document.getElementById('selectAllBtn');
    const deselectAllBtn = document.getElementById('deselectAllBtn');
    const applySelectionBtn = document.getElementById('applySelectionBtn');
    
    if (selectAllBtn) {
      selectAllBtn.addEventListener('click', () => {
        document.querySelectorAll('.sample-selection-item input[type="checkbox"]').forEach(checkbox => {
          checkbox.checked = true;
        });
      });
    }
    
    if (deselectAllBtn) {
      deselectAllBtn.addEventListener('click', () => {
        document.querySelectorAll('.sample-selection-item input[type="checkbox"]').forEach(checkbox => {
          checkbox.checked = false;
        });
      });
    }
    
    if (applySelectionBtn) {
      applySelectionBtn.addEventListener('click', applyVisualizationSampleSelection);
    }
    
    // Show the modal
    selectSamplesModal.classList.add('show');
  }
}

// Sample selection application function removed to focus on sample classification

// Visualization sample count display function removed to focus on sample classification

// Visualization axes update function removed to focus on sample classification

/**
 * Create or update the 2D visualization of audio samples
 */
async function visualizeSamples() {
  // Visualization functionality removed to focus on sample classification
  console.log('Visualization feature has been removed');
}

/**
 * Render function was previously used for visualization, now removed
 */
function renderVisualizationPlot() {
  // Visualization functionality removed to focus on sample classification
  console.log('Visualization feature has been removed');
  return false;
}

/**
 * Export all samples from a specific category
 * @param {string} categoryId - The ID of the category to export
 */
function exportCategorySamples(categoryId) {
  try {
    // Get samples for this category
    let samplesToExport = [];
    if (state.samplesViewMode === 'current') {
      samplesToExport = state.processedSamples.filter(sample => 
        categoryId === 'all' || sample.category === categoryId
      );
    } else {
      samplesToExport = state.allSamples.filter(sample => 
        categoryId === 'all' || sample.category === categoryId
      );
    }
    
    if (samplesToExport.length === 0) {
      showStatus(`No samples to export for category: ${categoryId}`, 'info');
      return;
    }
    
    // Get the IPC renderer directly from Electron
    const { ipcRenderer } = require('electron');
    
    // Use the Electron dialog to select the export directory
    ipcRenderer.invoke('show-export-dialog').then(result => {
      if (result.canceled) {
        return;
      }
      
      const exportDir = result.filePath;
      if (!exportDir) {
        showStatus('Export canceled - no directory selected', 'info');
        return;
      }
      
      // Request the export operation in main process with the samples list and target directory
      ipcRenderer.invoke('export-samples', {
        samples: samplesToExport,
        exportDir,
        categoryName: state.categories[categoryId] ? state.categories[categoryId].name : 'All Samples'
      }).then(result => {
        if (result.success) {
          showStatus(`Successfully exported ${result.count} samples to ${result.exportDir}`, 'success');
        } else {
          showStatus(`Error exporting samples: ${result.error}`, 'error');
          logger.error(`Export error: ${result.error}`);
        }
      }).catch(error => {
        showStatus(`Error during export: ${error.message}`, 'error');
        logger.error(`Export error: ${error.message}`);
      });
    }).catch(error => {
      showStatus(`Error showing export dialog: ${error.message}`, 'error');
      logger.error(`Export dialog error: ${error.message}`);
    });
  } catch (error) {
    showStatus(`Error preparing export: ${error.message}`, 'error');
    logger.error(`Export preparation error: ${error.message}`);
  }
}

// All visualization-related code has been removed to focus on sample classification

// Visualization feature formatting functions have been removed to focus on sample classification

// Visualization point color and tooltip functions have been removed to focus on sample classification

// Visualization tooltip and audio toggle functions have been removed to focus on sample classification

// Visualization sample audio playback function has been removed to focus on sample classification

// Visualization sample audio stop function has been removed to focus on sample classification

// Initial UI setup
updateFilesList();
updateProcessButton();