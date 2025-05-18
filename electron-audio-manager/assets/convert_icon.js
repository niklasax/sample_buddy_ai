const fs = require('fs');
const { createCanvas, loadImage } = require('canvas');
const sharp = require('sharp');
const path = require('path');

// Create a PNG from SVG
async function createPng() {
  try {
    const svgBuffer = fs.readFileSync(path.join(__dirname, 'icon.svg'));
    
    // Use sharp to convert SVG to PNG
    await sharp(svgBuffer)
      .resize(256, 256)
      .png()
      .toFile(path.join(__dirname, 'icon.png'));
    
    console.log('Icon converted successfully!');
  } catch (err) {
    console.error('Error converting icon:', err);
  }
}

createPng();