import os
import json
import requests
from datetime import datetime
from .helpers.paths import get_model_metadata_path, ensure_dir_exists, folder_paths

class EmpropsModelDownloader:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "local_save_path": ("STRING", {
                    "default": "checkpoints/model.safetensors", 
                    "multiline": False,
                    "placeholder": "checkpoints/model.safetensors",
                    "tooltip": "Path relative to models directory where the model will be saved"
                }),
                "model_url": ("STRING", {
                    "default": "", 
                    "multiline": False,
                    "placeholder": "https://example.com/model.safetensors",
                    "tooltip": "URL to download the model from"
                }),
            },
        }
    
    CATEGORY = "EmProps"
    RETURN_TYPES = ("STRING",)  
    RETURN_NAMES = ("model_name",)  
    FUNCTION = "run"

    def __init__(self):
        self.model_path = None
        self.download_url = None
        # Get the metadata path from the paths module
        self.metadata_path = get_model_metadata_path()

    def download_model(self):
        # Get the full path in the models directory
        full_path = os.path.join(folder_paths["models"], self.model_path)
        
        # Check if the model file exists
        if not os.path.exists(full_path):
            print(f"Model not found at {full_path}. Downloading from {self.download_url}...")
            response = requests.get(self.download_url)
            
            # Ensure the parent directories exist
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Save the downloaded model to the specified path
            with open(full_path, 'wb') as f:
                f.write(response.content)
            print(f"Model downloaded and saved to {full_path}")
        else:
            print(f"Model already exists at {full_path}")

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

    def run(self, local_save_path, model_url):
        # Store the paths
        self.model_path = local_save_path
        self.download_url = model_url
        
        # Download the model if it doesn't exist
        self.download_model()
        # Update the last used timestamp
        self.update_last_used()
        # Return just the model filename without the path
        return (os.path.basename(self.model_path),)

    @classmethod
    def IS_CHANGED(s, **kwargs):
        # This method is used to determine if the node's inputs have changed
        # If the inputs have changed, the node will be re-evaluated
        return False

    @classmethod
    def VALIDATE_INPUTS(s, **kwargs):
        if not kwargs["local_save_path"]:
            return "Model path cannot be empty"
        if not kwargs["model_url"]:
            return "Download URL cannot be empty"
        
        # Check if path is trying to go outside models directory
        if ".." in kwargs["local_save_path"]:
            return "Path cannot contain '..'"
        
        # Check if path has an extension
        if not os.path.splitext(kwargs["local_save_path"])[1]:
            return "Path must include a file extension (e.g. .safetensors)"
            
        return True

# Example usage
if __name__ == "__main__":
    # Define the model path and download URL
    # These variables specify the location where the model will be saved and the URL from which it will be downloaded
    model_path = "path/to/model/file"
    download_url = "http://example.com/model/file"
    # Create an instance of the EmpropsModelDownloader class
    # This instance will be used to download the model and update the last used timestamp
    downloader = EmpropsModelDownloader()
    # Run the downloader
    # This method will download the model if it doesn't exist and update the last used timestamp
    downloader.run(model_path, download_url)
