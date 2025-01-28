import os
import json
import requests
from datetime import datetime
from .helpers.paths import get_model_metadata_path, ensure_dir_exists

class EmpropsModelDownloader:
    @classmethod
    def INPUT_TYPES(s):
        # Define the input types for the node
        # This method is used to specify the types of inputs the node expects
        return {
            "required": {
                "model_path": ("STRING", {"default": "", "multiline": False}),
                "download_url": ("STRING", {"default": "", "multiline": False}),
            },
        }

    def __init__(self, model_path, download_url):
        # Initialize the downloader with the model path and download URL
        self.model_path = model_path
        self.download_url = download_url
        # Get the metadata path from the paths module
        self.metadata_path = get_model_metadata_path()

    def download_model(self):
        # Check if the model file exists
        # If the model file does not exist, download it from the specified URL
        if not os.path.exists(self.model_path):
            print(f"Model not found at {self.model_path}. Downloading from {self.download_url}...")
            response = requests.get(self.download_url)
            # Save the downloaded model to the specified path
            with open(self.model_path, 'wb') as f:
                f.write(response.content)
            print(f"Model downloaded and saved to {self.model_path}")
        else:
            # If the model file already exists, print a message
            print(f"Model already exists at {self.model_path}")

    def update_last_used(self):
        # Initialize an empty metadata dictionary
        metadata = {}
        # If the metadata file exists, load its contents
        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, 'r') as f:
                metadata = json.load(f)

        # Update the last used timestamp for the model
        metadata[self.model_path] = datetime.now().isoformat()
        # Save the updated metadata to the metadata file
        json_str = json.dumps(metadata, indent=4)  # First convert to string
        with open(self.metadata_path, 'w') as f:
            f.write(json_str)  # Then write the entire string at once
        print(f"Updated last used timestamp for {self.model_path}")

    def run(self):
        # Download the model if it doesn't exist
        # This method ensures that the model is available before it is used
        self.download_model()
        # Update the last used timestamp for the model
        # This method keeps track of when the model was last used
        self.update_last_used()

    @classmethod
    def IS_CHANGED(s, **kwargs):
        # This method is used to determine if the node's inputs have changed
        # If the inputs have changed, the node will be re-evaluated
        return False

    @classmethod
    def VALIDATE_INPUTS(s, **kwargs):
        # This method is used to validate the node's inputs
        # If the inputs are valid, the node will be executed
        return True

# Example usage
if __name__ == "__main__":
    # Define the model path and download URL
    # These variables specify the location where the model will be saved and the URL from which it will be downloaded
    model_path = "path/to/model/file"
    download_url = "http://example.com/model/file"
    # Create an instance of the EmpropsModelDownloader class
    # This instance will be used to download the model and update the last used timestamp
    downloader = EmpropsModelDownloader(model_path, download_url)
    # Run the downloader
    # This method will download the model if it doesn't exist and update the last used timestamp
    downloader.run()
