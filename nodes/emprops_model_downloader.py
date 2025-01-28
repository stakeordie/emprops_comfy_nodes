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
    },
    "DualCLIPLoader": {
        "clip_name1": "text_encoders",
        "clip_name2": "text_encoders"
    }
}

class EmpropsModelDownloader:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "url": ("STRING", {"default": ""}),
                "filename": ("STRING", {"default": ""}),
            },
            "optional": {
                # Let users either specify model_type directly or use target_node + target_field
                "model_type": (list(set(type for fields in NODE_MODEL_TYPES.values() for type in fields.values())), {"default": "checkpoints"}),
                "target_node": ("STRING", {
                    "default": "CheckpointLoaderSimple", 
                    "tooltip": "Node name or ID to download for. For API use, specify the node ID (e.g. '11' for DualCLIPLoader)"
                }),
                "target_field": ("STRING", {"default": "ckpt_name"}),
                "target_directory": ("STRING", {
                    "default": "",
                    "tooltip": "Optional: Directly specify output directory (e.g. 'checkpoints' or custom path). If empty, will use model_type or target_node to determine directory."
                }),
            }
        }
    
    CATEGORY = "EmProps"
    RETURN_TYPES = ("STRING",)  
    RETURN_NAMES = ("model_name",)  
    FUNCTION = "run"

    def get_node_type(self, target_node):
        """Convert node ID or name to node type"""
        # If target_node is a number (as string), it's a node ID
        # We'd need to get the actual node type from the workflow
        # For now, assume it's DualCLIPLoader if ID is 11
        if target_node.isdigit():
            if target_node == "11":
                return "DualCLIPLoader"
            raise ValueError(f"Unknown node ID: {target_node}")
        
        # Otherwise treat it as a node type name
        if target_node in NODE_MODEL_TYPES:
            return target_node
        
        raise ValueError(f"Unknown node type: {target_node}")

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

    def run(self, url, filename, model_type=None, target_node=None, target_field=None, target_directory=None):
        # If target_directory is specified, use it directly
        if target_directory:
            # Handle both relative (to ComfyUI models dir) and absolute paths
            if os.path.isabs(target_directory):
                output_dir = target_directory
            else:
                # Get ComfyUI models dir and join with target_directory
                models_dir = os.path.dirname(folder_paths.get_folder_paths("checkpoints")[0])
                output_dir = os.path.join(models_dir, target_directory)
            
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, filename)
            
            print(f"Using custom directory: {output_dir}")
        
        else:
            # Original logic using model_type or target_node
            if not model_type and target_node and target_field:
                # Convert node ID/name to type
                node_type = self.get_node_type(target_node)
                
                if node_type in NODE_MODEL_TYPES and target_field in NODE_MODEL_TYPES[node_type]:
                    model_type = NODE_MODEL_TYPES[node_type][target_field]
                else:
                    raise ValueError(f"Invalid node type ({node_type}) or target_field ({target_field})")
            
            if not model_type:
                raise ValueError("Must specify either model_type, target_node+target_field, or target_directory")

            # Get the output directory for this model type
            output_dirs = folder_paths.get_folder_paths(model_type)
            if not output_dirs:
                raise ValueError(f"No output directory found for model type: {model_type}")
            
            output_dir = output_dirs[0]
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, filename)

        # Check if file already exists
        if os.path.exists(output_path):
            print(f"File {filename} already exists in {output_dir}")
            return {}
            
        # Download the model
        print(f"Downloading {filename} to {output_dir}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Download with progress bar
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024
        progress_bar = tqdm.tqdm(total=total_size, unit='iB', unit_scale=True)
        
        with open(output_path, 'wb') as f:
            for data in response.iter_content(block_size):
                progress_bar.update(len(data))
                f.write(data)
        
        progress_bar.close()
        print(f"Downloaded {filename}")
        return {}

    @classmethod
    def IS_CHANGED(s, **kwargs):
        return False

    @classmethod
    def VALIDATE_INPUTS(s, **kwargs):
        if not kwargs["filename"]:
            return "Model path cannot be empty"
        if not kwargs["url"]:
            return "Download URL cannot be empty"
        
        # Check if path is trying to go outside models directory
        if ".." in kwargs["filename"]:
            return "Path cannot contain '..'"
        
        # Check if path has an extension
        if not os.path.splitext(kwargs["filename"])[1]:
            return "Path must include a file extension (e.g. .safetensors)"
            
        return True

# Example usage
if __name__ == "__main__":
    # Define the model path and download URL
    # These variables specify the location where the model will be saved and the URL from which it will be downloaded
    filename = "path/to/model/file"
    download_url = "http://example.com/model/file"
    model_type = "checkpoints"
    # Create an instance of the EmpropsModelDownloader class
    # This instance will be used to download the model and update the last used timestamp
    downloader = EmpropsModelDownloader()
    # Run the downloader
    # This method will download the model if it doesn't exist and update the last used timestamp
    downloader.run(download_url, filename, model_type)
