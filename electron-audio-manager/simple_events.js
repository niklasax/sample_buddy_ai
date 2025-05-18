/**
 * Simple event handling utilities without circular dependencies
 * This ensures buttons and UI elements work properly
 */

/**
 * Adds an event listener with logging but without circular dependencies
 * @param {HTMLElement} element - DOM element to attach listener to
 * @param {string} eventType - Type of event (click, etc)
 * @param {Function} handler - Event handler function
 */
function addSafeEventListener(element, eventType, handler) {
  if (!element) {
    console.error(`Cannot add ${eventType} listener to null element`);
    return;
  }
  
  const elementId = element.id || element.tagName || 'unknown';
  console.log(`Adding ${eventType} listener to ${elementId}`);
  
  const wrappedHandler = function(event) {
    console.log(`Event ${eventType} triggered on ${elementId}`);
    try {
      // Call the original handler
      handler.call(this, event);
    } catch (error) {
      console.error(`Error in ${eventType} handler for ${elementId}:`, error);
    }
  };
  
  // Add the event listener
  element.addEventListener(eventType, wrappedHandler);
}

/**
 * Check if an element exists in the DOM
 * @param {string} id - Element ID to check
 * @param {string} description - Description of element (for logging)
 * @returns {HTMLElement|null} - Element if found, null otherwise
 */
function checkElement(id, description) {
  const element = document.getElementById(id);
  if (element) {
    console.log(`Found element: ${id} (${description})`);
    return element;
  } else {
    console.error(`Missing element: ${id} (${description})`);
    return null;
  }
}

module.exports = {
  addSafeEventListener,
  checkElement
};