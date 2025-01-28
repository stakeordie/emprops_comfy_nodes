import os
import json
import unittest
from unittest.mock import patch, mock_open
from datetime import datetime
from nodes.emprops_model_downloader import EmpropsModelDownloader
from nodes.helpers.paths import folder_paths
from nodes.helpers.paths import get_model_metadata_path

class TestEmpropsModelDownloader(unittest.TestCase):
    def setUp(self):
        self.model_path = "path/to/model/file"
        self.download_url = "http://example.com/model/file"
        self.metadata_path = get_model_metadata_path()
        self.downloader = EmpropsModelDownloader(self.model_path, self.download_url)

    @patch('os.path.exists')
    @patch('requests.get')
    @patch('builtins.open', new_callable=mock_open)
    def test_download_model(self, mock_file, mock_get, mock_exists):
        # Mock the model file not existing
        mock_exists.return_value = False
        # Mock the response from the download URL
        mock_response = mock_get.return_value
        mock_response.content = b'model data'
        # Mock the file write operation
        mock_file.return_value.write.return_value = None

        self.downloader.download_model()

        # Assert that the model was downloaded and saved
        mock_get.assert_called_once_with(self.download_url)
        mock_file.assert_called_once_with(self.model_path, 'wb')
        mock_file.return_value.write.assert_called_once_with(b'model data')

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_update_last_used(self, mock_file, mock_exists):
        # Mock the metadata file existing
        mock_exists.return_value = True
        # Mock the metadata file contents
        mock_file.return_value.read.return_value = json.dumps({self.model_path: '2023-01-01T00:00:00Z'})

        # Create a fixed datetime for testing
        fixed_datetime = datetime(2025, 1, 1, 12, 0, 0)
        with patch('nodes.emprops_model_downloader.datetime') as mock_datetime:
            # Mock the datetime to return a fixed timestamp
            mock_datetime.now.return_value = fixed_datetime
            
            self.downloader.update_last_used()

            # Assert that the last used timestamp was updated
            mock_file.assert_called_with(self.metadata_path, 'w')
            expected_json = json.dumps({self.model_path: fixed_datetime.isoformat()}, indent=4)
            mock_file.return_value.write.assert_called_once_with(expected_json)

    @patch('nodes.emprops_model_downloader.EmpropsModelDownloader.download_model')
    @patch('nodes.emprops_model_downloader.EmpropsModelDownloader.update_last_used')
    def test_run(self, mock_update_last_used, mock_download_model):
        self.downloader.run()

        # Assert that the download and update methods were called
        mock_download_model.assert_called_once()
        mock_update_last_used.assert_called_once()

if __name__ == '__main__':
    unittest.main()
