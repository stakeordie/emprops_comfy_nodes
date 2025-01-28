import os
import json
import unittest
from unittest.mock import patch, mock_open, MagicMock
from datetime import datetime
import sys
from unittest.mock import patch

# Create mock folder_paths
mock_folder_paths = MagicMock()
mock_folder_paths.get_folder_paths.return_value = ["/workspace/shared/models"]

# Mock folder_paths before importing EmpropsModelDownloader
sys.modules['folder_paths'] = mock_folder_paths

# Now we can safely import EmpropsModelDownloader
from nodes.emprops_model_downloader import EmpropsModelDownloader

class TestEmpropsModelDownloader(unittest.TestCase):
    @patch('os.makedirs')  # Mock makedirs for all tests
    @patch('os.path.exists')  # Mock exists for all tests
    def setUp(self, mock_exists, mock_makedirs):
        self.model_path = "checkpoints/model.safetensors"
        self.download_url = "http://example.com/model/file"
        self.downloader = EmpropsModelDownloader()
        # Use mocked path for metadata
        self.metadata_path = os.path.join("/workspace/shared/models", "model_metadata.json")
        
        # Store the paths in the downloader but don't run download yet
        self.downloader.model_path = self.model_path
        self.downloader.download_url = self.download_url
        
        # Mock file existence checks
        mock_exists.return_value = False
        # Mock makedirs to do nothing
        mock_makedirs.return_value = None

    @patch('os.path.exists')
    @patch('requests.get')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    def test_download_model(self, mock_makedirs, mock_file, mock_get, mock_exists):
        # Mock the model file not existing
        mock_exists.return_value = False
        # Mock the response from the download URL
        mock_response = mock_get.return_value
        mock_response.content = b'model data'

        self.downloader.download_model()

        # Assert that the model was downloaded and saved
        expected_path = os.path.join("/workspace/shared/models", self.model_path)
        mock_file.assert_called_with(expected_path, 'wb')
        mock_file().write.assert_called_with(b'model data')
        # Verify makedirs was called with the right path
        mock_makedirs.assert_called_with(os.path.dirname(expected_path), exist_ok=True)

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    def test_update_last_used(self, mock_makedirs, mock_file, mock_exists):
        # Mock the metadata file not existing
        mock_exists.return_value = False
        
        self.downloader.update_last_used()
        
        # Assert that the metadata was written
        mock_file.assert_called_with(self.metadata_path, 'w')
        # The actual write call will contain a timestamp that changes, so just verify it was called
        assert mock_file().write.called
        # Verify makedirs was called for metadata directory
        mock_makedirs.assert_called_with(os.path.dirname(self.metadata_path), exist_ok=True)

    @patch('os.makedirs')
    @patch('requests.get')
    @patch('builtins.open', new_callable=mock_open)
    def test_run(self, mock_file, mock_get, mock_makedirs):
        # Mock the download response
        mock_response = mock_get.return_value
        mock_response.content = b'model data'
        
        result = self.downloader.run(self.model_path, self.download_url)
        
        # Assert we get back just the model name
        self.assertEqual(result, ("model.safetensors",))
        
        # Verify the model was downloaded
        expected_path = os.path.join("/workspace/shared/models", self.model_path)
        mock_file.assert_any_call(expected_path, 'wb')
        # Verify the metadata was updated
        mock_file.assert_any_call(self.metadata_path, 'w')

if __name__ == '__main__':
    unittest.main()
