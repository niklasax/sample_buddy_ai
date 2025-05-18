/**
 * Natural Language Search Module
 * 
 * This file contains functions for searching audio samples using natural language
 */

/**
 * Perform a natural language search of audio samples
 * 
 * @param {string} query - Natural language search query
 * @param {function} callback - Callback function to handle search results
 */
function performSearch(query, callback) {
    if (!query || !query.trim()) {
        callback({ error: 'Please enter a search query' });
        return;
    }
    
    // Perform AJAX request to search API
    fetch('/api/search', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query: query })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        callback(null, data);
    })
    .catch(error => {
        console.error('Error:', error);
        callback({ error: 'Error performing search. Please try again later.' });
    });
}

/**
 * Format search results for display
 * 
 * @param {Array} results - Array of search result objects
 * @param {HTMLElement} container - Container element for results
 */
function displaySearchResults(results, container) {
    if (!results || results.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted">
                <i class="fas fa-search fa-3x mb-3"></i>
                <p>No matching samples found. Try a different search query.</p>
            </div>
        `;
        return;
    }
    
    // Create HTML for results
    let resultsHtml = `
        <h4><i class="fas fa-list"></i> Search Results (${results.length})</h4>
        <div class="row">
    `;
    
    results.forEach(sample => {
        resultsHtml += `
            <div class="col-md-4 mb-4">
                <div class="card sample-card h-100">
                    <div class="card-body">
                        <h5 class="card-title">${sample.name}</h5>
                        <div class="mb-2">
                            ${sample.category ? `<span class="badge bg-primary">${sample.category}</span>` : ''}
                            ${sample.mood ? `<span class="badge bg-secondary">${sample.mood}</span>` : ''}
                        </div>
                        <p class="card-text">
                            <small>
                                ${sample.features && sample.features.duration ? `Duration: ${sample.features.duration.toFixed(2)}s<br>` : ''}
                                ${sample.features && sample.features.tempo ? `Tempo: ${sample.features.tempo.toFixed(1)} BPM` : ''}
                            </small>
                        </p>
                    </div>
                    <div class="card-footer bg-transparent border-top-0">
                        <button class="btn btn-sm btn-outline-primary play-btn" data-path="${sample.path}">
                            <i class="fas fa-play"></i> Play
                        </button>
                        <button class="btn btn-sm btn-outline-info sample-details-btn" data-id="${sample.id}">
                            <i class="fas fa-info-circle"></i> Details
                        </button>
                    </div>
                </div>
            </div>
        `;
    });
    
    resultsHtml += '</div>';
    container.innerHTML = resultsHtml;
}

/**
 * Get search query examples based on available samples
 * 
 * @param {Array} samples - Array of sample objects
 * @returns {Array} Array of example queries
 */
function getSearchExamples(samples) {
    // Get unique categories and moods
    const categories = [...new Set(samples.map(s => s.category).filter(Boolean))];
    const moods = [...new Set(samples.map(s => s.mood).filter(Boolean))];
    
    // Generate example queries
    const examples = [];
    
    // Category-based queries
    categories.forEach(category => {
        examples.push(`${category} samples`);
        examples.push(`${category} with high energy`);
    });
    
    // Mood-based queries
    moods.forEach(mood => {
        examples.push(`${mood} sounds`);
        examples.push(`${mood} ${categories[Math.floor(Math.random() * categories.length)]} samples`);
    });
    
    // Feature-based queries
    examples.push('short percussion samples');
    examples.push('long ambient sounds');
    examples.push('high-pitched synth sounds');
    examples.push('low frequency bass samples');
    examples.push('fast tempo drum loops');
    examples.push('slow atmospheric pads');
    
    // Shuffle and return limited set
    return shuffleArray(examples).slice(0, 6);
}

/**
 * Shuffle an array using Fisher-Yates algorithm
 * 
 * @param {Array} array - Array to shuffle
 * @returns {Array} Shuffled array
 */
function shuffleArray(array) {
    const newArray = [...array];
    for (let i = newArray.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [newArray[i], newArray[j]] = [newArray[j], newArray[i]];
    }
    return newArray;
}
