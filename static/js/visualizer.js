/**
 * Audio Sample Visualizer
 * 
 * This file contains functions for creating interactive visualizations
 * of audio samples based on their extracted features.
 */

/**
 * Creates a scatter plot visualization of audio samples
 * 
 * @param {string} containerId - ID of the container element
 * @param {Array} data - Array of sample data objects
 * @param {string} xKey - Feature key for X axis
 * @param {string} yKey - Feature key for Y axis
 * @param {string} colorKey - Key to determine point colors (category or mood)
 * @param {Object} tooltip - D3 tooltip object
 */
function createScatterPlot(containerId, data, xKey, yKey, colorKey, tooltip) {
    // Clear the container
    d3.select(`#${containerId}`).html('');
    
    // Set up dimensions
    const margin = {top: 20, right: 30, bottom: 50, left: 60};
    const width = document.getElementById(containerId).clientWidth - margin.left - margin.right;
    const height = 400 - margin.top - margin.bottom;
    
    // Create SVG
    const svg = d3.select(`#${containerId}`)
        .append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);
    
    // Define scales
    const x = d3.scaleLinear()
        .domain([0, d3.max(data, d => d[xKey] * 1.1) || 1])
        .nice()
        .range([0, width]);
    
    const y = d3.scaleLinear()
        .domain([0, d3.max(data, d => d[yKey] * 1.1) || 1])
        .nice()
        .range([height, 0]);
    
    // Create a map of unique categories/moods
    const categories = [...new Set(data.map(d => d[colorKey]))];
    
    // Color scale - using a colorblind-friendly palette
    const colorScale = d3.scaleOrdinal()
        .domain(categories)
        .range([
            '#1b9e77', '#d95f02', '#7570b3', '#e7298a', 
            '#66a61e', '#e6ab02', '#a6761d', '#666666',
            '#386cb0', '#f0027f', '#bf5b17', '#666666'
        ]);
    
    // Add grid lines
    svg.append('g')
        .attr('class', 'grid')
        .attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(x)
            .ticks(10)
            .tickSize(-height)
            .tickFormat('')
        );
    
    svg.append('g')
        .attr('class', 'grid')
        .call(d3.axisLeft(y)
            .ticks(10)
            .tickSize(-width)
            .tickFormat('')
        );
    
    // Add X axis
    svg.append('g')
        .attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(x))
        .selectAll('text')
        .style('fill', 'rgba(255, 255, 255, 0.7)');
    
    // Add Y axis
    svg.append('g')
        .call(d3.axisLeft(y))
        .selectAll('text')
        .style('fill', 'rgba(255, 255, 255, 0.7)');
    
    // Add axis labels
    svg.append('text')
        .attr('class', 'axis-label')
        .attr('text-anchor', 'middle')
        .attr('x', width / 2)
        .attr('y', height + margin.bottom - 5)
        .text(formatAxisLabel(xKey));
    
    svg.append('text')
        .attr('class', 'axis-label')
        .attr('text-anchor', 'middle')
        .attr('transform', 'rotate(-90)')
        .attr('x', -height / 2)
        .attr('y', -margin.left + 15)
        .text(formatAxisLabel(yKey));
    
    // Add dots
    svg.selectAll('dot')
        .data(data)
        .enter()
        .append('circle')
        .attr('cx', d => isNaN(d[xKey]) ? 0 : x(d[xKey]))
        .attr('cy', d => isNaN(d[yKey]) ? 0 : y(d[yKey]))
        .attr('r', 6)
        .style('fill', d => colorScale(d[colorKey]))
        .style('opacity', 0.7)
        .style('stroke', 'white')
        .style('stroke-width', 0.5)
        .on('mouseover', function(event, d) {
            d3.select(this)
                .transition()
                .duration(200)
                .attr('r', 8)
                .style('opacity', 1);
            
            tooltip.transition()
                .duration(200)
                .style('opacity', 0.9);
            
            tooltip.html(`
                <strong>${d.name}</strong><br/>
                Category: ${d.category}<br/>
                Mood: ${d.mood}<br/>
                ${formatAxisLabel(xKey)}: ${d[xKey].toFixed(2)}<br/>
                ${formatAxisLabel(yKey)}: ${d[yKey].toFixed(2)}
            `)
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 28) + 'px');
        })
        .on('mouseout', function() {
            d3.select(this)
                .transition()
                .duration(500)
                .attr('r', 6)
                .style('opacity', 0.7);
            
            tooltip.transition()
                .duration(500)
                .style('opacity', 0);
        });
}

/**
 * Creates a legend for the visualizations
 * 
 * @param {string} containerId - ID of the container element
 * @param {Array} data - Array of sample data objects
 * @param {string} colorKey - Key to determine colors (category or mood)
 */
function createLegend(containerId, data, colorKey) {
    // Clear the container
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    
    // Get unique categories/moods
    const categories = [...new Set(data.map(d => d[colorKey]))];
    
    // Color scale - using a colorblind-friendly palette
    const colorScale = d3.scaleOrdinal()
        .domain(categories)
        .range([
            '#1b9e77', '#d95f02', '#7570b3', '#e7298a', 
            '#66a61e', '#e6ab02', '#a6761d', '#666666',
            '#386cb0', '#f0027f', '#bf5b17', '#666666'
        ]);
    
    // Create legend items
    categories.forEach(category => {
        const legendItem = document.createElement('div');
        legendItem.className = 'd-flex align-items-center mb-2';
        
        const colorBox = document.createElement('div');
        colorBox.style.width = '15px';
        colorBox.style.height = '15px';
        colorBox.style.backgroundColor = colorScale(category);
        colorBox.style.marginRight = '8px';
        colorBox.style.borderRadius = '3px';
        
        const label = document.createElement('span');
        label.textContent = category;
        
        legendItem.appendChild(colorBox);
        legendItem.appendChild(label);
        container.appendChild(legendItem);
    });
}

/**
 * Formats an axis label for display
 * 
 * @param {string} key - Feature key
 * @returns {string} Formatted label
 */
function formatAxisLabel(key) {
    const labels = {
        'spectral_centroid': 'Spectral Centroid',
        'zero_crossing_rate': 'Zero Crossing Rate',
        'energy': 'Energy',
        'tempo': 'Tempo (BPM)',
        'duration': 'Duration (s)',
        'spectral_bandwidth': 'Spectral Bandwidth',
        'spectral_rolloff': 'Spectral Rolloff',
        'rms': 'RMS'
    };
    
    return labels[key] || key;
}
