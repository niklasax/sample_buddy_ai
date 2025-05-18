import unittest
import os
import sys
import json
import shutil
import tempfile
from pathlib import Path

# Add the root directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the necessary modules
import quick_classifier
import deep_classifier
from electron_audio_manager.python.find_similar_samples import load_sample_features, create_feature_vector, find_similar_samples

class TestBasicFunctionality(unittest.TestCase):
    """
    Tests for basic functionality of the audio sample manager.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test resources that are used for all tests."""
        # Create a temporary directory for test outputs
        cls.temp_dir = tempfile.mkdtemp()
        
        # Find a sample audio file for testing
        test_samples_dir = os.path.join(os.path.dirname(__file__), 'test_samples')
        if not os.path.exists(test_samples_dir):
            os.makedirs(test_samples_dir)
            
        cls.test_sample_path = os.path.join(test_samples_dir, 'test_kick.wav')
        
        # If no test sample exists, we'll note this and skip certain tests
        cls.has_test_sample = os.path.exists(cls.test_sample_path)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up resources after all tests have run."""
        # Remove the temporary directory
        if os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir)
    
    def test_quick_classifier_filename_parsing(self):
        """Test the quick classifier's ability to extract information from filenames."""
        # Test with various filename patterns
        test_cases = [
            ('kick_drum_punchy_120bpm.wav', {'category': 'drums', 'subcategory': 'kick', 'mood': 'punchy'}),
            ('synth_lead_bright_Cmaj.wav', {'category': 'synth', 'subcategory': 'lead', 'mood': 'bright'}),
            ('guitar_acoustic_warm_Gmaj.wav', {'category': 'guitar', 'subcategory': 'acoustic', 'mood': 'warm'}),
            ('fx_impact_dark_reverb.wav', {'category': 'fx', 'subcategory': 'impact', 'mood': 'dark'}),
            ('unknown_file.wav', {'category': 'unknown', 'subcategory': '', 'mood': ''})
        ]
        
        for filename, expected in test_cases:
            result = quick_classifier.classify_by_filename(filename)
            self.assertEqual(result.get('category', '').lower(), expected['category'])
            # Check if mood was extracted correctly (if available in the result)
            if 'mood' in result and expected['mood']:
                self.assertEqual(result['mood'].lower(), expected['mood'])
    
    def test_quick_classifier_process_sample(self):
        """Test that the quick classifier can process a file without errors."""
        if not self.has_test_sample:
            self.skipTest("No test sample available")
        
        # Process a single file
        result = quick_classifier.process_single_file(
            self.test_sample_path, 
            output_dir=self.temp_dir
        )
        
        # Check that the result contains the expected keys
        self.assertIn('id', result)
        self.assertIn('name', result)
        self.assertIn('path', result)
        self.assertIn('category', result)
    
    def test_deep_classifier_feature_extraction(self):
        """Test that the deep classifier can extract features from an audio file."""
        if not self.has_test_sample:
            self.skipTest("No test sample available")
        
        # Extract features
        features = deep_classifier.extract_audio_features(self.test_sample_path)
        
        # Check that the function returns a dictionary with some expected keys
        self.assertIsInstance(features, dict)
        
        # We should at least have some basic spectral features
        expected_keys = ['spectral_centroid', 'spectral_bandwidth', 'spectral_rolloff', 'zero_crossing_rate']
        for key in expected_keys:
            self.assertIn(key, features)
    
    def test_similarity_search_feature_vector(self):
        """Test the creation of feature vectors for similarity search."""
        # Create a sample features dictionary
        features = {
            'spectral_centroid': 0.5,
            'spectral_bandwidth': 0.7,
            'spectral_rolloff': 0.3,
            'zero_crossing_rate': 0.2,
            'energy': 0.8,
            'tempo': 120.0,
            'mfcc': [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        }
        
        # Create a feature vector
        vector = create_feature_vector(features)
        
        # The vector should be a numpy array with the expected length
        self.assertEqual(len(vector), 16)  # 6 basic features + 10 MFCCs
    
    def test_classification_pipeline(self):
        """
        Test the full classification pipeline on a single file.
        This ensures the classifiers can run end-to-end without errors.
        """
        if not self.has_test_sample:
            self.skipTest("No test sample available")
        
        # Create an output directory for this test
        output_dir = os.path.join(self.temp_dir, 'classification_test')
        os.makedirs(output_dir, exist_ok=True)
        
        # First with quick classifier
        quick_result = quick_classifier.process_files(
            [self.test_sample_path], 
            output_dir=output_dir
        )
        
        self.assertIsInstance(quick_result, dict)
        self.assertIn('samples', quick_result)
        self.assertTrue(len(quick_result['samples']) > 0)
        
        # Then with deep classifier
        deep_result = deep_classifier.process_files(
            [self.test_sample_path], 
            output_dir=output_dir, 
            deep_analysis=True
        )
        
        self.assertIsInstance(deep_result, dict)
        self.assertIn('samples', deep_result)
        self.assertTrue(len(deep_result['samples']) > 0)
        
        # Check that the output directory contains the classified file
        classified_files = list(Path(output_dir).glob('**/*.wav'))
        self.assertTrue(len(classified_files) > 0)

if __name__ == '__main__':
    unittest.main()