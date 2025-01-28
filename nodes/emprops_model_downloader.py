import os
import json
import requests
from datetime import datetime
import folder_paths
import tqdm

# Mapping of nodes and their fields to model types
NODE_MODEL_TYPES = {
    "CheckpointLoader": {
        "ckpt_name": "checkpoints",
        "config_name": "configs"
    },
    "CheckpointLoaderSimple": {
        "ckpt_name": "checkpoints"
    },
    "LoraLoader": {
        "lora_name": "loras"
    },
    "VAELoader": {
        "vae_name": "vae"
    },
    "CLIPLoader": {
        "clip_name": "text_encoders"
    },
    "ControlNetLoader": {
        "control_net_name": "controlnet"
    },
    "UNETLoader": {
        "unet_name": "diffusion_models"
    },
    "StyleModelLoader": {
        "style_model_name": "style_models"
    }
}

class EmpropsModelDownloader:
    @classmethod
    def INPUT_TYPES(s):
        # Get all available nodes that can load models
        nodes = list(NODE_MODEL_TYPES.keys())
        
        return {
            "required": {
                "model_type": (["checkpoints", "loras", "vae", "embeddings", "diffusion_models", "clip_vision", "style_models"], {
                    "default": "checkpoints",
                    "tooltip": "Type of model being downloaded"
                }),
                "local_save_path": ("STRING", {
                    "default": "model.safetensors", 
                    "multiline": False,
                    "placeholder": "model.safetensors",
                    "tooltip": "Path relative to selected model type directory where the model will be saved"
                }),
                "model_url": ("STRING", {
                    "default": "", 
                    "multiline": False,
                    "placeholder": "https://example.com/model.safetensors",
                    "tooltip": "URL to download the model from"
                }),
            },
            "optional": {
                "target_node": (nodes, {"default": "CheckpointLoaderSimple"}),
                "target_field": ("STRING", {"default": "ckpt_name"}),
            }
        }
    
    CATEGORY = "EmProps"
    RETURN_TYPES = ("STRING",)  
    RETURN_NAMES = ("model_name",)  
    FUNCTION = "run"

    def __init__(self):
        self.model_path = None
        self.download_url = None
        self.model_type = None
        # Store metadata in the models directory
        self.metadata_path = os.path.join(folder_paths.get_folder_paths("models")[0], "model_metadata.json")

    def download_model(self):
        # Get the models root directory from ComfyUI for this model type
        models_dir = folder_paths.get_folder_paths("models")[0]
        model_type_dir = os.path.join(models_dir, self.model_type)
        
        # Get the full path in the models directory
        full_path = os.path.join(model_type_dir, self.model_path)
        
        # Check if the model file exists
        if not os.path.exists(full_path):
            print(f"[EmProps] Model not found at {full_path}. Downloading from {self.download_url}...")
            response = requests.get(self.download_url)
            
            # Ensure the parent directories exist
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Save the model file
            with open(full_path, 'wb') as f:
                f.write(response.content)
            print(f"[EmProps] Model downloaded successfully to {full_path}")
        else:
            print(f"[EmProps] Model already exists at {full_path}")

    def update_last_used(self):
        # Initialize an empty metadata dictionary
        metadata = {}
        
        # Load existing metadata if it exists
        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, 'r') as f:
                    metadata = json.load(f)
            except json.JSONDecodeError:
                print(f"[EmProps] Warning: Could not parse metadata file at {self.metadata_path}")
        
        # Update the last used timestamp for this model
        metadata[self.model_path] = {
            "last_used": datetime.now().isoformat()
        }
        
        # Save the updated metadata
        os.makedirs(os.path.dirname(self.metadata_path), exist_ok=True)
        json_str = json.dumps(metadata, indent=2)
        with open(self.metadata_path, 'w') as f:
            f.write(json_str)
        print(f"[EmProps] Updated last used timestamp for {self.model_path}")

    def run(self, model_type, local_save_path, model_url, target_node=None, target_field=None):
        # If model_type not specified, try to get it from target_node and target_field
        if not model_type and target_node and target_field:
            if target_node in NODE_MODEL_TYPES and target_field in NODE_MODEL_TYPES[target_node]:
                model_type = NODE_MODEL_TYPES[target_node][target_field]
            else:
                raise ValueError(f"Invalid target_node ({target_node}) or target_field ({target_field})")
        
        if not model_type:
            raise ValueError("Must specify either model_type or both target_node and target_field")

        # Store the paths
        self.model_path = local_save_path
        self.download_url = model_url
        self.model_type = model_type

        print(f"[EmProps] Downloading {model_type} model to {self.model_path}")

        # Download the model if needed
        self.download_model()
        
        # Update the last used timestamp
        self.update_last_used()
        
        # Return just the model filename
        return (os.path.basename(self.model_path),)

    @classmethod
    def IS_CHANGED(s, **kwargs):
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
    model_type = "checkpoints"
    # Create an instance of the EmpropsModelDownloader class
    # This instance will be used to download the model and update the last used timestamp
    downloader = EmpropsModelDownloader()
    # Run the downloader
    # This method will download the model if it doesn't exist and update the last used timestamp
    downloader.run(model_type, model_path, download_url)
