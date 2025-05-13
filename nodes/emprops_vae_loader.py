import os
import time
import traceback
from server import PromptServer
import folder_paths
import comfy.sd
# Added: 2025-05-13T17:18:00-04:00 - Import model cache database
from ..db.model_cache import model_cache_db

# Added: 2025-05-13T16:56:15-04:00 - Custom VAE loader implementation
def log_debug(message):
    """Enhanced logging function with timestamp and stack info"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    caller = traceback.extract_stack()[-2]
    file = os.path.basename(caller.filename)
    line = caller.lineno
    print(f"[EmProps DEBUG {timestamp}] [{file}:{line}] {message}", flush=True)

class EmProps_VAE_Loader:
    """
    A custom VAE loader that explicitly loads files by name,
    bypassing ComfyUI's selection mechanism. This ensures it can load
    files that were downloaded during the current execution.
    """
    RETURN_TYPES = ("VAE",)
    RETURN_NAMES = ("VAE",)
    OUTPUT_NODE = True
    FUNCTION = "load_vae"
    CATEGORY = "EmProps"
    
    @classmethod
    def INPUT_TYPES(cls):
        log_debug("EmProps_VAE_Loader.INPUT_TYPES called")
        return {
            "required": {
                "vae_name": ("STRING", {"multiline": False, "default": ""}),
            },
            "hidden": {
                "node_id": "UNIQUE_ID"
            }
        }

    def load_vae(self, vae_name, node_id=None):
        log_debug(f"EmProps_VAE_Loader.load_vae called with vae_name={vae_name}, node_id={node_id}")
        
        if not vae_name:
            log_debug("EmProps_VAE_Loader: No VAE name provided")
            raise ValueError("No VAE name provided")
        
        # Force refresh the cache to ensure we see the latest files
        log_debug("EmProps_VAE_Loader: Refreshing VAE cache")
        if "vae" in folder_paths.filename_list_cache:
            del folder_paths.filename_list_cache["vae"]
        
        # Get the updated file list
        vae_files = folder_paths.get_filename_list("vae")
        log_debug(f"EmProps_VAE_Loader: Available VAEs: {vae_files}")
        
        # Check if the file exists
        max_attempts = 5
        attempt = 0
        vae_path = None
        
        while attempt < max_attempts:
            try:
                log_debug(f"EmProps_VAE_Loader: Attempt {attempt+1} to get path for {vae_name}")
                vae_path = folder_paths.get_full_path("vae", vae_name)
                if vae_path:
                    log_debug(f"EmProps_VAE_Loader: Found VAE at {vae_path}")
                    break
            except Exception as e:
                log_debug(f"EmProps_VAE_Loader: Error getting path: {str(e)}")
                
            # If not found, wait a bit and try again (in case it's still being written)
            log_debug(f"EmProps_VAE_Loader: VAE {vae_name} not found, waiting...")
            time.sleep(1)
            
            # Refresh the cache again
            if "vae" in folder_paths.filename_list_cache:
                del folder_paths.filename_list_cache["vae"]
            folder_paths.get_filename_list("vae")
            
            attempt += 1
        
        if not vae_path:
            log_debug(f"EmProps_VAE_Loader: VAE {vae_name} not found after {max_attempts} attempts")
            raise ValueError(f"VAE {vae_name} not found after {max_attempts} attempts")
        
        # Load the VAE
        log_debug(f"EmProps_VAE_Loader: Loading VAE from {vae_path}")
        try:
            # Send a progress update
            if node_id:
                PromptServer.instance.send_sync("progress", {
                    "node": node_id,
                    "value": 0,
                    "max": 100
                })
            
            # Load the VAE
            vae = comfy.sd.VAE(vae_path)
            
            # Added: 2025-05-13T17:18:00-04:00 - Update model usage in cache database
            try:
                model_cache_db.update_model_usage(vae_path)
                log_debug(f"Updated model usage in cache database: {vae_path}")
            except Exception as e:
                log_debug(f"Error updating model usage in cache database: {str(e)}")
                # Non-critical error, continue with loading
            
            # Send completion progress
            if node_id:
                PromptServer.instance.send_sync("progress", {
                    "node": node_id,
                    "value": 100,
                    "max": 100
                })
            
            log_debug(f"EmProps_VAE_Loader: Successfully loaded VAE {vae_name}")
            return (vae,)
            
        except Exception as e:
            log_debug(f"EmProps_VAE_Loader: Error loading VAE: {str(e)}")
            raise e

# Node class mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "EmProps_VAE_Loader": EmProps_VAE_Loader,
}

# Human-readable names for the UI
NODE_DISPLAY_NAME_MAPPINGS = {
    "EmProps_VAE_Loader": "EmProps VAE Loader",
}
