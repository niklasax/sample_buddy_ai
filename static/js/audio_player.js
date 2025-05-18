/**
 * Audio Player Module
 * 
 * This file contains functions for audio playback using Howler.js
 */

// Global variable to store currently playing sound
let currentSound = null;

/**
 * Play an audio file
 * 
 * @param {string} path - Path to the audio file
 * @param {HTMLElement} [button] - Optional button element to update UI
 */
function playAudio(path, button = null) {
    // Stop currently playing sound if any
    if (currentSound) {
        currentSound.stop();
        
        // Reset all play buttons if no specific button was provided
        if (!button) {
            document.querySelectorAll('.play-btn').forEach(btn => {
                btn.innerHTML = '<i class="fas fa-play"></i>';
                if (btn.classList.contains('btn-outline-danger')) {
                    btn.classList.remove('btn-outline-danger');
                    btn.classList.add('btn-outline-primary');
                }
            });
        }
    }
    
    // Create new Howl instance
    currentSound = new Howl({
        src: [path],
        html5: true,
        onplay: function() {
            // Update button UI if provided
            if (button) {
                button.innerHTML = '<i class="fas fa-pause"></i>';
                if (button.classList.contains('btn-outline-primary')) {
                    button.classList.remove('btn-outline-primary');
                    button.classList.add('btn-outline-danger');
                }
            }
        },
        onend: function() {
            // Reset button UI when playback ends
            if (button) {
                button.innerHTML = '<i class="fas fa-play"></i>';
                if (button.classList.contains('btn-outline-danger')) {
                    button.classList.remove('btn-outline-danger');
                    button.classList.add('btn-outline-primary');
                }
            }
        },
        onstop: function() {
            // Reset button UI when playback stops
            if (button) {
                button.innerHTML = '<i class="fas fa-play"></i>';
                if (button.classList.contains('btn-outline-danger')) {
                    button.classList.remove('btn-outline-danger');
                    button.classList.add('btn-outline-primary');
                }
            }
        }
    });
    
    // Handle errors
    currentSound.on('loaderror', function() {
        console.error('Error loading audio file:', path);
        if (button) {
            button.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
            setTimeout(() => {
                button.innerHTML = '<i class="fas fa-play"></i>';
            }, 2000);
        }
    });
    
    // Start playback
    currentSound.play();
    
    return currentSound;
}

/**
 * Toggle play/pause of an audio file
 * 
 * @param {string} path - Path to the audio file
 * @param {HTMLElement} button - Button element to update UI
 */
function toggleAudio(path, button) {
    // If no sound is playing or a different sound is playing, play this one
    if (!currentSound || currentSound._src !== path) {
        playAudio(path, button);
    } else {
        // If this sound is already playing, toggle play/pause
        if (currentSound.playing()) {
            currentSound.pause();
            button.innerHTML = '<i class="fas fa-play"></i>';
            if (button.classList.contains('btn-outline-danger')) {
                button.classList.remove('btn-outline-danger');
                button.classList.add('btn-outline-primary');
            }
        } else {
            currentSound.play();
            button.innerHTML = '<i class="fas fa-pause"></i>';
            if (button.classList.contains('btn-outline-primary')) {
                button.classList.remove('btn-outline-primary');
                button.classList.add('btn-outline-danger');
            }
        }
    }
}

/**
 * Stop all audio playback
 */
function stopAllAudio() {
    if (currentSound) {
        currentSound.stop();
        currentSound = null;
    }
    
    // Reset all play buttons
    document.querySelectorAll('.play-btn').forEach(btn => {
        btn.innerHTML = '<i class="fas fa-play"></i>';
        if (btn.classList.contains('btn-outline-danger')) {
            btn.classList.remove('btn-outline-danger');
            btn.classList.add('btn-outline-primary');
        }
    });
}
