/**
 * Simple, standalone logger with no external dependencies
 * This version avoids circular dependencies that can crash the application
 */

const fs = require('fs');
const path = require('path');

// Get user's home directory for log storage
const homeDir = process.env.HOME || process.env.USERPROFILE || '.';
const APP_NAME = 'sample-buddy-ai';
const LOG_DIR = path.join(homeDir, '.logs', APP_NAME);
const LOG_FILE = path.join(LOG_DIR, 'app.log');

// Create log directory if it doesn't exist
try {
  fs.mkdirSync(LOG_DIR, { recursive: true });
} catch (err) {
  // Ignore error if directory exists
}

// Original console methods
const originalConsole = {
  log: console.log,
  warn: console.warn,
  error: console.error
};

/**
 * Write a log entry
 * @param {string} level - Log level (info, warn, error)
 * @param {string} message - Message to log
 * @param {Object} [data] - Optional data to include
 */
function log(level, message, data = null) {
  // Prevent circular references and logging loops
  if (message && message.toString().includes('[LOGGER')) {
    return; // Prevent recursive logging
  }
  
  const timestamp = new Date().toISOString();
  const logEntry = `[${timestamp}] [${level.toUpperCase()}] ${message}`;
  
  try {
    // Write to console (using original methods to avoid recursion)
    const consoleMethod = level === 'error' ? originalConsole.error : 
                         level === 'warn' ? originalConsole.warn : 
                         originalConsole.log;
    
    consoleMethod(logEntry);
    
    // Only log data if it's a primitive type or simple object (not DOM elements, etc.)
    if (data !== null && data !== undefined) {
      if (typeof data === 'string' || typeof data === 'number' || typeof data === 'boolean') {
        consoleMethod(data);
      } else if (typeof data === 'object') {
        try {
          // Try to stringify the object first to check for circular references
          const dataStr = JSON.stringify(data, null, 2);
          consoleMethod(dataStr.length > 1000 ? dataStr.substring(0, 1000) + '... (truncated)' : dataStr);
        } catch (circularErr) {
          consoleMethod('[Circular reference or unserializable object detected]');
        }
      }
    }
    
    // Write to file
    fs.appendFileSync(LOG_FILE, logEntry + '\n');
    if (data !== null && data !== undefined) {
      try {
        const dataStr = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
        fs.appendFileSync(LOG_FILE, dataStr.length > 1000 ? dataStr.substring(0, 1000) + '... (truncated)' : dataStr + '\n');
      } catch (fileErr) {
        fs.appendFileSync(LOG_FILE, '[Circular reference or unserializable object detected]\n');
      }
    }
  } catch (err) {
    // Use a direct console method to avoid any possible loops
    try {
      originalConsole.error('[LOGGER ERROR]', err.message);
    } catch (fatalError) {
      // Last resort - nothing else we can do
    }
  }
}

// Export logger functions
module.exports = {
  info: (message, data) => log('info', message, data),
  warn: (message, data) => log('warn', message, data),
  error: (message, data) => log('error', message, data),
  getLogPath: () => LOG_FILE
};