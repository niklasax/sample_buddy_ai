import os
import logging
import json
from audio_processor import process_audio_folder
from feature_extractor import extract_audio_features
from classifier import classify_audio_samples

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Process the test files
upload_folder = os.path.join('tmp', 'audio_classifier_uploads')
samples = process_audio_folder(upload_folder)
print(f'Processed {len(samples)} samples')

# Extract features
samples = extract_audio_features(samples)
print('Features extracted')

# Classify samples
classified_samples = classify_audio_samples(samples)
print('Samples classified')

# Print results
for sample_id, sample_data in classified_samples.items():
    print(f'Sample: {sample_data.get("name")}')
    print(f'  Category: {sample_data.get("category")}')
    print(f'  Mood: {sample_data.get("mood")}')