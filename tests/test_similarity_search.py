import unittest
import os
import sys
import json
import shutil
import tempfile
import numpy as np
from pathlib import Path

# Add the root directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import our similarity search module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'electron-audio-manager', 'python')))
from find_similar_samples import load_sample_features, create_feature_vector, find_similar_samples

class TestSimilaritySearch(unittest.TestCase):
    """
    Tests for the audio similarity search functionality.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test resources that are used for all tests."""
        # Create a temporary directory for test outputs
        cls.temp_dir = tempfile.mkdtemp()
        
        # Create test feature files in this directory
        cls.sample_dir = os.path.join(cls.temp_dir, 'samples')
        os.makedirs(cls.sample_dir, exist_ok=True)
        
        # Create a few sample audio files and their matching feature files
        cls.create_test_feature_files(cls.sample_dir)
        
        # Choose one as our reference sample
        cls.reference_sample = os.path.join(cls.sample_dir, 'kick_drum_punchy.wav')
    
    @classmethod
    def tearDownClass(cls):
        """Clean up resources after all tests have run."""
        # Remove the temporary directory
        if os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir)
    
    @classmethod
    def create_test_feature_files(cls, directory):
        """Create test audio files and corresponding feature files."""
        # Create a few dummy audio files
        sample_files = [
            ('kick_drum_punchy.wav', {'category': 'drums', 'mood': 'punchy', 
                                     'spectral_centroid': 0.3, 'spectral_bandwidth': 0.5, 
                                     'spectral_rolloff': 0.7, 'zero_crossing_rate': 0.1,
                                     'energy': 0.9, 'tempo': 120.0,
                                     'mfcc': [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]}),
            
            ('kick_drum_soft.wav', {'category': 'drums', 'mood': 'soft', 
                                  'spectral_centroid': 0.25, 'spectral_bandwidth': 0.45, 
                                  'spectral_rolloff': 0.65, 'zero_crossing_rate': 0.08,
                                  'energy': 0.7, 'tempo': 110.0,
                                  'mfcc': [0.12, 0.22, 0.32, 0.42, 0.52, 0.62, 0.72, 0.82, 0.92, 1.02]}),
            
            ('hihat_closed.wav', {'category': 'drums', 'mood': 'bright', 
                                'spectral_centroid': 0.8, 'spectral_bandwidth': 0.9, 
                                'spectral_rolloff': 0.95, 'zero_crossing_rate': 0.6,
                                'energy': 0.5, 'tempo': 120.0,
                                'mfcc': [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4]}),
            
            ('synth_lead.wav', {'category': 'synth', 'mood': 'bright', 
                              'spectral_centroid': 0.7, 'spectral_bandwidth': 0.4, 
                              'spectral_rolloff': 0.8, 'zero_crossing_rate': 0.3,
                              'energy': 0.6, 'tempo': 130.0,
                              'mfcc': [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2]})
        ]
        
        # Create empty audio files and save feature JSON files
        for filename, features in sample_files:
            audio_path = os.path.join(directory, filename)
            json_path = os.path.join(directory, filename.rsplit('.', 1)[0] + '.json')
            
            # Create an empty audio file
            with open(audio_path, 'wb') as f:
                f.write(b'RIFF\x00\x00\x00\x00WAVEfmt \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00data\x00\x00\x00\x00')
            
            # Save the features as a JSON file
            with open(json_path, 'w') as f:
                json.dump(features, f)
    
    def test_load_sample_features(self):
        """Test loading sample features from a JSON file."""
        # Load features for our test reference sample
        features = load_sample_features(self.reference_sample)
        
        # Check that features were loaded correctly
        self.assertIsNotNone(features)
        self.assertIn('category', features)
        self.assertIn('spectral_centroid', features)
    
    def test_create_feature_vector(self):
        """Test creating a feature vector from a features dictionary."""
        # Load features for our test reference sample
        features = load_sample_features(self.reference_sample)
        
        # Create a feature vector
        vector = create_feature_vector(features)
        
        # Check that the vector has the expected shape
        self.assertEqual(len(vector), 16)  # 6 basic features + 10 MFCCs
    
    def test_find_similar_samples(self):
        """Test finding similar samples based on a reference sample."""
        # Find similar samples
        similar_samples = find_similar_samples(self.reference_sample, self.sample_dir, max_results=3)
        
        # We should get similar samples back
        self.assertGreater(len(similar_samples), 0)
        
        # The first similar sample should be the most similar
        self.assertGreaterEqual(similar_samples[0]['similarity'], similar_samples[-1]['similarity'])
        
        # Check that the similar samples have the expected fields
        expected_fields = ['path', 'name', 'similarity', 'category', 'mood']
        for field in expected_fields:
            self.assertIn(field, similar_samples[0])
    
    def test_similarity_ranking(self):
        """Test that samples are ranked correctly by similarity."""
        # Find similar samples
        similar_samples = find_similar_samples(self.reference_sample, self.sample_dir)
        
        # The kick_drum_soft should be more similar to kick_drum_punchy than hihat_closed
        kick_soft_idx = -1
        hihat_idx = -1
        
        for i, sample in enumerate(similar_samples):
            if 'kick_drum_soft' in sample['name']:
                kick_soft_idx = i
            elif 'hihat_closed' in sample['name']:
                hihat_idx = i
        
        # If both samples were found, verify their ordering
        if kick_soft_idx != -1 and hihat_idx != -1:
            self.assertLess(kick_soft_idx, hihat_idx)

if __name__ == '__main__':
    unittest.main()