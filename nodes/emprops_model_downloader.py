import os
import folder_paths
import requests
from tqdm import tqdm
from nodes import NODE_CLASS_MAPPINGS

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
    def INPUT_TYPES(cls):
        print("[EmProps DEBUG] Getting INPUT_TYPES for EmpropsModelDownloader")
        print("[EmProps DEBUG] RETURN_TYPES =", cls.RETURN_TYPES)
        print("[EmProps DEBUG] Type of RETURN_TYPES =", type(cls.RETURN_TYPES))
        
        # Add debug logs for DualCLIPLoader's expected type
        print("[EmProps DEBUG] DualCLIPLoader text_encoders list:", folder_paths.get_filename_list("text_encoders"))
        print("[EmProps DEBUG] DualCLIPLoader input type:", type(folder_paths.get_filename_list("text_encoders")))
        print("[EmProps DEBUG] DualCLIPLoader input type tuple format:", (folder_paths.get_filename_list("text_encoders"),))
        
        # Get all registered nodes that are in our NODE_MODEL_TYPES mapping
        available_nodes = []
        for node_name in NODE_CLASS_MAPPINGS:
            if node_name in NODE_MODEL_TYPES:
                available_nodes.append(node_name)
        
        NODE_TYPES = available_nodes if available_nodes else ["CheckpointLoaderSimple"]
        print("[EmProps DEBUG] Available node types:", NODE_TYPES)
        
        return_val = {
            "required": {
                "url": ("STRING", {"default": ""}),
                "filename": ("STRING", {"default": ""}),
            },
            "optional": {
                "model_type": ([k for k in folder_paths.folder_names_and_paths.keys()], {"default": "checkpoints"}),
                "target_node": (NODE_TYPES, {"default": "CheckpointLoaderSimple"}),
                "target_field": (["ckpt_name"], {"default": "ckpt_name"}),
                "target_directory": ("STRING", {"default": "checkpoints"})
            }
        }
        print("[EmProps DEBUG] INPUT_TYPES returning:", return_val)
        return return_val

    @classmethod
    def get_available_filenames(cls, model_type="checkpoints"):
        try:
            filenames = folder_paths.get_filename_list(model_type)
            print("[EmProps DEBUG] Available filenames for", model_type, ":", filenames)
            print("[EmProps DEBUG] Type of filenames:", type(filenames))
            return filenames
        except Exception as e:
            print("[EmProps DEBUG] Error getting filenames:", str(e))
            return []

    RETURN_TYPES = ("LIST",)
    RETURN_NAMES = ("FILENAME",)
    FUNCTION = "run"
    OUTPUT_NODE = True
    CATEGORY = "Emprops"

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

    def run(self, url, filename, model_type=None, target_node=None, target_field=None, target_directory=None):
        print("[EmProps DEBUG] Run called with:")
        print("  - url:", url)
        print("  - filename:", filename)
        print("  - model_type:", model_type)
        print("  - target_node:", target_node)
        print("  - target_field:", target_field)
        print("  - target_directory:", target_directory)
        # Debug: Print all available paths and model type info
        print("DEBUG: Model type:", model_type)
        print("DEBUG: Target node:", target_node)
        print("DEBUG: Target field:", target_field)
        if target_node and target_field:
            node_type = self.get_node_type(target_node)
            print("DEBUG: Node type:", node_type)
            if node_type in NODE_MODEL_TYPES:
                print("DEBUG: Node model types:", NODE_MODEL_TYPES[node_type])
                if target_field in NODE_MODEL_TYPES[node_type]:
                    determined_type = NODE_MODEL_TYPES[node_type][target_field]
                    print("DEBUG: Determined model type:", determined_type)
                    print("DEBUG: Available files:", folder_paths.get_filename_list(determined_type))
        
        # Debug: Print all available paths
        print("DEBUG: Available paths for checkpoints:", folder_paths.get_folder_paths("checkpoints"))
        print("DEBUG: Base path from folder_paths:", folder_paths.base_path)
        
        # If we have target_directory, that's all we need
        if target_directory:
            if os.path.isabs(target_directory):
                output_dir = target_directory
            else:
                # Find the shared path in the available paths
                checkpoint_paths = folder_paths.get_folder_paths("checkpoints")
                shared_path = None
                
                # First try to find exact match for shared/models/checkpoints
                for path in checkpoint_paths:
                    if path.endswith("/shared/models/checkpoints") or path.endswith("/shared/models/checkpoints/"):
                        shared_path = path
                        break
                
                # If not found, look for any path containing shared/models
                if not shared_path:
                    for path in checkpoint_paths:
                        if "/shared/models" in path:
                            shared_path = path
                            break
                
                # If still not found, use first path
                if not shared_path:
                    print("WARNING: Could not find shared models path, using first available path")
                    shared_path = checkpoint_paths[0]
                
                print("DEBUG: Using shared path:", shared_path)
                
                if target_directory == "checkpoints":
                    output_dir = shared_path
                else:
                    # Get models directory and append target_directory
                    models_dir = os.path.dirname(shared_path)  # Remove 'checkpoints'
                    output_dir = os.path.join(models_dir, target_directory)
                
                print("DEBUG: Final output directory:", output_dir)
            
            # Check if file exists in target directory
            output_path = os.path.join(output_dir, filename)
            print("DEBUG: Final output path:", output_path)
            if os.path.exists(output_path):
                print(f"File {filename} already exists in {output_dir}")
                print("[EmProps DEBUG] Returning filename as list:", [filename])
                print("[EmProps DEBUG] Return type:", type([filename]))
                return [filename]
            
            # Download to target directory
            os.makedirs(output_dir, exist_ok=True)
            print(f"Downloading {filename} to {output_dir}")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # Download with progress bar
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024
            progress_bar = tqdm(total=total_size, unit='iB', unit_scale=True)
            
            with open(output_path, 'wb') as f:
                for data in response.iter_content(block_size):
                    progress_bar.update(len(data))
                    f.write(data)
            
            progress_bar.close()
            print(f"Downloaded {filename}")
            print("[EmProps DEBUG] Returning filename as list:", [filename])
            print("[EmProps DEBUG] Return type:", type([filename]))
            return [filename]
            
        # If no target_directory, try other methods
        try:
            # Try to get output directory from model_type or target_node
            if target_node and target_field:
                node_type = self.get_node_type(target_node)
                if node_type in NODE_MODEL_TYPES and target_field in NODE_MODEL_TYPES[node_type]:
                    model_type = NODE_MODEL_TYPES[node_type][target_field]
            
            if model_type:
                output_dirs = folder_paths.get_folder_paths(model_type)
                if output_dirs:
                    output_dir = output_dirs[0]
                    output_path = os.path.join(output_dir, filename)
                    
                    # Check if file already exists
                    if os.path.exists(output_path):
                        print(f"File {filename} already exists in {output_dir}")
                        print("[EmProps DEBUG] Returning filename as list:", [filename])
                        print("[EmProps DEBUG] Return type:", type([filename]))
                        return [filename]
                    
                    # Download the model
                    os.makedirs(output_dir, exist_ok=True)
                    print(f"Downloading {filename} to {output_dir}")
                    response = requests.get(url, stream=True)
                    response.raise_for_status()
                    
                    # Download with progress bar
                    total_size = int(response.headers.get('content-length', 0))
                    block_size = 1024
                    progress_bar = tqdm(total=total_size, unit='iB', unit_scale=True)
                    
                    with open(output_path, 'wb') as f:
                        for data in response.iter_content(block_size):
                            progress_bar.update(len(data))
                            f.write(data)
                    
                    progress_bar.close()
                    print(f"Downloaded {filename}")
                    print("[EmProps DEBUG] Returning filename as list:", [filename])
                    print("[EmProps DEBUG] Return type:", type([filename]))
                    return [filename]
            
            raise ValueError("Must specify target_directory if model_type and target_node+field are not provided or invalid")
        except Exception as e:
            print(f"Error downloading model: {str(e)}")
            raise e
