import os
import time
import traceback
from server import PromptServer
import sys
import folder_paths
import comfy.sd

# [2025-05-30T10:20:00-04:00] Custom Diffusion Model loader implementation
def log_debug(message):
    """Enhanced logging function with timestamp and stack info"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    caller = traceback.extract_stack()[-2]
    file = os.path.basename(caller.filename)
    line = caller.lineno
    print(f"[EmProps DEBUG {timestamp}] [{file}:{line}] {message}", flush=True)

class EmProps_Diffusion_Model_Loader:
    """
    A custom diffusion model loader that explicitly loads files by name,
    bypassing ComfyUI's selection mechanism. This ensures it can load
    files that were downloaded during the current execution.
    """
    RETURN_TYPES = ("MODEL", "CLIP", "VAE")
    RETURN_NAMES = ("MODEL", "CLIP", "VAE")
    OUTPUT_NODE = True
    FUNCTION = "load_model"
    CATEGORY = "EmProps"
    
    DESCRIPTION = "Loads a diffusion model checkpoint with EmProps' custom downloading and offloading capabilities."
    
    @classmethod
    def INPUT_TYPES(cls):
        log_debug("EmProps_Diffusion_Model_Loader.INPUT_TYPES called")
        return {
            "required": {
                "model_name": ("STRING", {"multiline": False, "default": ""}),
            },
            "hidden": {
                "node_id": "UNIQUE_ID"
            }
        }

    def load_model(self, model_name, node_id=None):
        log_debug(f"EmProps_Diffusion_Model_Loader.load_model called with model_name={model_name}, node_id={node_id}")
        
        if not model_name:
            log_debug("EmProps_Diffusion_Model_Loader: No model name provided")
            raise ValueError("No model name provided")
        
        # Force refresh the cache to ensure we see the latest files
        log_debug("EmProps_Diffusion_Model_Loader: Refreshing checkpoints cache")
        if "checkpoints" in folder_paths.filename_list_cache:
            del folder_paths.filename_list_cache["checkpoints"]
        
        # Get the updated file list
        checkpoint_files = folder_paths.get_filename_list("checkpoints")
        log_debug(f"EmProps_Diffusion_Model_Loader: Available checkpoints: {checkpoint_files}")
        
        # Check if the file exists
        max_attempts = 5
        attempt = 0
        model_path = None
        
        while attempt < max_attempts:
            try:
                log_debug(f"EmProps_Diffusion_Model_Loader: Attempt {attempt+1} to get path for {model_name}")
                model_path = folder_paths.get_full_path("checkpoints", model_name)
                if model_path:
                    log_debug(f"EmProps_Diffusion_Model_Loader: Found checkpoint at {model_path}")
                    break
            except Exception as e:
                log_debug(f"EmProps_Diffusion_Model_Loader: Error getting path: {str(e)}")
                
            # If not found, wait a bit and try again (in case it's still being written)
            log_debug(f"EmProps_Diffusion_Model_Loader: Checkpoint {model_name} not found, waiting...")
            time.sleep(1)
            
            # Refresh the cache again
            if "checkpoints" in folder_paths.filename_list_cache:
                del folder_paths.filename_list_cache["checkpoints"]
            folder_paths.get_filename_list("checkpoints")
            
            attempt += 1
        
        if not model_path:
            log_debug(f"EmProps_Diffusion_Model_Loader: Checkpoint {model_name} not found after {max_attempts} attempts")
            raise ValueError(f"Checkpoint {model_name} not found after {max_attempts} attempts")
        
        # Load the model
        log_debug(f"EmProps_Diffusion_Model_Loader: Loading model from {model_path}")
        try:
            # Send a progress update
            if node_id:
                PromptServer.instance.send_sync("progress", {
                    "node": node_id,
                    "value": 0,
                    "max": 100
                })
            
            # Load the model
            out = comfy.sd.load_checkpoint_guess_config(
                model_path, 
                output_vae=True, 
                output_clip=True, 
                embedding_directory=folder_paths.get_folder_paths("embeddings")
            )
            
            # Send completion progress
            if node_id:
                PromptServer.instance.send_sync("progress", {
                    "node": node_id,
                    "value": 100,
                    "max": 100
                })
            
            log_debug(f"EmProps_Diffusion_Model_Loader: Successfully loaded model {model_name}")
            return out[:3]
            
        except Exception as e:
            log_debug(f"EmProps_Diffusion_Model_Loader: Error loading model: {str(e)}")
            raise e

# Node class mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "EmProps_Diffusion_Model_Loader": EmProps_Diffusion_Model_Loader,
}

# Human-readable names for the UI
NODE_DISPLAY_NAME_MAPPINGS = {
    "EmProps_Diffusion_Model_Loader": "EmProps Diffusion Model Loader",
}
