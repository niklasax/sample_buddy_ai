import unittest
import os
import sys
import json
import tempfile
from flask import Flask
from werkzeug.datastructures import FileStorage
from io import BytesIO

# Add the root directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the app and route handlers
import app

class TestWebApp(unittest.TestCase):
    """
    Tests for the web application functionality.
    """
    
    def setUp(self):
        """Set up a test client before each test."""
        # Configure the app for testing
        app.app.config['TESTING'] = True
        app.app.config['WTF_CSRF_ENABLED'] = False
        
        # Create a test client
        self.client = app.app.test_client()
        
        # Create a temporary directory for uploads
        self.temp_dir = tempfile.mkdtemp()
        # Store the original upload folder
        self.original_upload_folder = app.app.config.get('UPLOAD_FOLDER')
        # Set the upload folder to our temporary directory
        app.app.config['UPLOAD_FOLDER'] = self.temp_dir
        
        # Create test samples directory if needed
        test_samples_dir = os.path.join(os.path.dirname(__file__), 'test_samples')
        if not os.path.exists(test_samples_dir):
            os.makedirs(test_samples_dir)
            
        self.test_sample_path = os.path.join(test_samples_dir, 'test_kick.wav')
        self.has_test_sample = os.path.exists(self.test_sample_path)
    
    def tearDown(self):
        """Clean up after each test."""
        # Restore original upload folder
        if self.original_upload_folder:
            app.app.config['UPLOAD_FOLDER'] = self.original_upload_folder
        
        # Clean up temporary directory
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
    
    def test_index_route(self):
        """Test that the index route returns the correct page."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Sample Buddy AI', response.data)
    
    def test_upload_without_file(self):
        """Test uploading without a file should return an error."""
        response = self.client.post('/upload', data={})
        self.assertIn(b'No file part', response.data)
    
    def test_upload_with_empty_file(self):
        """Test uploading with an empty file selection should return an error."""
        response = self.client.post('/upload', data={'file': (BytesIO(), '')})
        self.assertIn(b'No selected file', response.data)
    
    def test_upload_with_invalid_file(self):
        """Test uploading with an invalid file type should return an error."""
        data = {
            'file': (BytesIO(b'test data'), 'test.txt')
        }
        response = self.client.post('/upload', data=data, content_type='multipart/form-data')
        self.assertIn(b'File type not allowed', response.data)
    
    def test_upload_with_valid_file(self):
        """Test uploading with a valid audio file."""
        if not self.has_test_sample:
            self.skipTest("No test sample available")
        
        with open(self.test_sample_path, 'rb') as f:
            file_data = f.read()
        
        data = {
            'file': (BytesIO(file_data), 'test_kick.wav')
        }
        response = self.client.post('/upload', data=data, content_type='multipart/form-data')
        # Should redirect to the results page
        self.assertEqual(response.status_code, 302)
    
    def test_clear_samples_route(self):
        """Test that the clear_samples route works."""
        response = self.client.get('/clear')
        # Should redirect to the index page
        self.assertEqual(response.status_code, 302)
    
    def test_restart_route(self):
        """Test that the restart route works."""
        response = self.client.get('/restart')
        # Should redirect to the index page
        self.assertEqual(response.status_code, 302)

if __name__ == '__main__':
    unittest.main()