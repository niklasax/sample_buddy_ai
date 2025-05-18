/**
 * Load all samples from the file system, including ones processed in previous sessions
 * @param {string} appStorageDir - The directory where samples are stored
 * @param {Array} currentSamples - Current samples array to combine with found samples
 * @returns {Promise<Array>} Array of all found samples
 */
async function loadAllSamples(appStorageDir, currentSamples = []) {
  const fs = require('fs');
  const path = require('path');
  const logger = require('./basic_logger');
  
  try {
    logger.info('Loading all processed samples from file system...');
    
    if (!appStorageDir) {
      logger.error('Invalid storage directory');
      throw new Error('Could not access storage directory');
    }
    
    logger.info(`Attempting to load all samples from: ${appStorageDir}`);
    
    // Get all samples from all category folders
    const categories = ['drums', 'bass', 'synth', 'fx', 'vocal', 'other'];
    let totalSamples = [];
    
    // Check each category folder for samples
    for (const category of categories) {
      const categoryPath = path.join(appStorageDir, category);
      
      try {
        if (fs.existsSync(categoryPath)) {
          const files = fs.readdirSync(categoryPath);
          
          // Filter for audio files only
          const audioFiles = files.filter(file => {
            const extension = path.extname(file).toLowerCase();
            return ['.wav', '.mp3', '.ogg', '.flac', '.aif', '.aiff'].includes(extension);
          });
          
          // For each audio file, create a sample object
          for (const file of audioFiles) {
            const filePath = path.join(categoryPath, file);
            const jsonFilePath = filePath.replace(/\.[^.]+$/, '.json');
            
            // Check if there's a corresponding JSON metadata file
            if (fs.existsSync(jsonFilePath)) {
              try {
                const metadata = JSON.parse(fs.readFileSync(jsonFilePath, 'utf8'));
                
                // Add the sample if it has proper metadata
                if (metadata.id && metadata.name) {
                  // Check if this sample is already in our list
                  const existingSample = totalSamples.find(s => s.id === metadata.id);
                  if (!existingSample) {
                    metadata.path = filePath;
                    totalSamples.push(metadata);
                  }
                }
              } catch (jsonError) {
                logger.warn(`Error reading JSON for ${file}: ${jsonError.message}`);
              }
            } else {
              // No JSON, create a basic sample object from the file
              const sampleName = path.basename(file);
              const sampleId = `${category}-${sampleName}-${Date.now()}`;
              
              totalSamples.push({
                id: sampleId,
                name: sampleName,
                path: filePath,
                category: category,
                mood: 'unknown'
              });
            }
          }
        }
      } catch (error) {
        logger.warn(`Error reading category ${category}: ${error.message}`);
      }
    }
    
    // Combine with current samples
    if (totalSamples.length > 0 || currentSamples.length > 0) {
      // Use a Map to deduplicate samples by ID
      const samplesMap = new Map();
      
      // Add current samples first
      currentSamples.forEach(sample => {
        samplesMap.set(sample.id, sample);
      });
      
      // Then add any newly found samples
      totalSamples.forEach(sample => {
        if (!samplesMap.has(sample.id)) {
          samplesMap.set(sample.id, sample);
        }
      });
      
      // Convert back to array
      const allSamples = Array.from(samplesMap.values());
      logger.info(`Loaded ${allSamples.length} total samples from file system`);
      
      return allSamples;
    } else {
      logger.info('No samples found in the file system');
      return [];
    }
  } catch (error) {
    logger.error('Error loading all samples:', error);
    throw error;
  }
}

module.exports = loadAllSamples;