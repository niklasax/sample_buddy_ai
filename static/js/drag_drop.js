/**
 * Drag and Drop Module
 * 
 * This file contains functions for handling drag and drop file uploads
 */

/**
 * Initialize drag and drop functionality
 * 
 * @param {HTMLElement} dropZone - Drop zone element
 * @param {HTMLElement} fileInput - File input element
 * @param {HTMLElement} selectedFilesDiv - Element to display selected files
 * @param {HTMLElement} processBtn - Process button element
 */
function initDragAndDrop(dropZone, fileInput, selectedFilesDiv, processBtn) {
    console.log("Initializing drag and drop with:", {
        dropZone: !!dropZone,
        fileInput: !!fileInput,
        selectedFilesDiv: !!selectedFilesDiv,
        processBtn: !!processBtn
    });
    
    if (!dropZone || !fileInput || !selectedFilesDiv || !processBtn) {
        console.error("Missing required elements for drag and drop functionality");
        return;
    }
    
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });
    
    // Highlight drop zone when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });
    
    // Unhighlight drop zone when item is dragged out
    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });
    
    // Handle dropped files
    dropZone.addEventListener('drop', handleDrop, false);
    
    /**
     * Prevent default behaviors for drag events
     */
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    /**
     * Highlight drop zone
     */
    function highlight() {
        console.log("Highlighting drop zone");
        dropZone.classList.add('highlight');
    }
    
    /**
     * Unhighlight drop zone
     */
    function unhighlight() {
        console.log("Unhighlighting drop zone");
        dropZone.classList.remove('highlight');
    }
    
    /**
     * Handle file drop
     * 
     * @param {Event} e - Drop event
     */
    function handleDrop(e) {
        console.log("Files dropped");
        const dt = e.dataTransfer;
        const files = dt.files;
        
        console.log("Dropped files:", files.length);
        
        // Update file input with dropped files
        // NOTE: fileInput.files is readonly, so we need to trigger a change event manually
        // This is a workaround
        if (window.DataTransfer && window.FileList && files.length > 0) {
            // Create a DataTransfer object and add each file
            let dataTransfer = new DataTransfer();
            for (let i = 0; i < files.length; i++) {
                dataTransfer.items.add(files[i]);
            }
            // Set the new FileList as the files property
            fileInput.files = dataTransfer.files;
            
            // Trigger change event manually
            const event = new Event('change', { bubbles: true });
            fileInput.dispatchEvent(event);
        } else {
            // Fallback for older browsers: just update the UI directly
            console.log("Using fallback for older browsers");
            window.updateSelectedFiles(files, selectedFilesDiv, processBtn);
        }
    }
}

/**
 * Format file size for display
 * 
 * @param {number} bytes - File size in bytes
 * @returns {string} Formatted file size
 */
function formatFileSize(bytes) {
    if (bytes < 1024) {
        return bytes + ' B';
    } else if (bytes < 1024 * 1024) {
        return (bytes / 1024).toFixed(1) + ' KB';
    } else {
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }
}
