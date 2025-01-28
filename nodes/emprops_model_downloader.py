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
    def INPUT_TYPES(s):
        # Get all registered nodes that are in our NODE_MODEL_TYPES mapping
        available_nodes = []
        for node_name in NODE_CLASS_MAPPINGS:
            if node_name in NODE_MODEL_TYPES:
                available_nodes.append(node_name)
        
        if not available_nodes:
            print("Warning: No compatible model loader nodes found!")
            available_nodes = list(NODE_MODEL_TYPES.keys())  # Fallback to our mapping
        
        # Get all possible fields across all nodes
        all_fields = set()
        for node_name in available_nodes:
            if node_name in NODE_MODEL_TYPES:
                all_fields.update(NODE_MODEL_TYPES[node_name].keys())
        
        return {
            "required": {
                "url": ("STRING", {"default": ""}),
                "filename": ("STRING", {"default": ""}),
            },
            "optional": {
                # Let users either specify model_type directly or use target_node + target_field
                "model_type": (list(set(type for fields in NODE_MODEL_TYPES.values() for type in fields.values())), {"default": "checkpoints"}),
                "target_node": (available_nodes, {
                    "default": "CheckpointLoaderSimple", 
                    "tooltip": "Node to download for. For API use, you can also specify the node ID (e.g. '11' for DualCLIPLoader)"
                }),
                "target_field": (list(all_fields), {
                    "default": "ckpt_name",
                    "tooltip": "Which input field in the target node to download for"
                }),
                "target_directory": ("STRING", {
                    "default": "",
                    "tooltip": "Optional: Directly specify output directory (e.g. 'checkpoints' or custom path). If empty, will use model_type or target_node to determine directory."
                }),
            }
        }

    RETURN_TYPES = ()
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
        # Priority 1: Use target_directory if specified
        if target_directory:
            if os.path.isabs(target_directory):
                output_dir = target_directory
            else:
                base_models_dir = os.path.dirname(folder_paths.get_folder_paths("checkpoints")[0])
                output_dir = os.path.join(base_models_dir, target_directory)
        
        # Priority 2: Use target_node and target_field if both specified
        elif target_node and target_field:
            node_type = self.get_node_type(target_node)
            if node_type not in NODE_MODEL_TYPES or target_field not in NODE_MODEL_TYPES[node_type]:
                raise ValueError(f"Invalid node type ({node_type}) or target_field ({target_field})")
            
            model_type = NODE_MODEL_TYPES[node_type][target_field]
            output_dirs = folder_paths.get_folder_paths(model_type)
            if not output_dirs:
                raise ValueError(f"No output directory found for model type: {model_type}")
            output_dir = output_dirs[0]
        
        # Priority 3: Use model_type
        elif model_type:
            output_dirs = folder_paths.get_folder_paths(model_type)
            if not output_dirs:
                raise ValueError(f"No output directory found for model type: {model_type}")
            output_dir = output_dirs[0]
        
        # No valid input provided
        else:
            raise ValueError("Must specify either target_directory, target_node+target_field, or model_type")

        # Ensure directory exists and get output path
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
        progress_bar = tqdm(total=total_size, unit='iB', unit_scale=True)
        
        with open(output_path, 'wb') as f:
            for data in response.iter_content(block_size):
                progress_bar.update(len(data))
                f.write(data)
        
        progress_bar.close()
        print(f"Downloaded {filename}")
        return {}
