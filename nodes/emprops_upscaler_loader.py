import os
import time
import traceback
from server import PromptServer
import folder_paths
import comfy.utils

# Added: 2025-05-13T16:58:00-04:00 - Custom Upscaler loader implementation
def log_debug(message):
    """Enhanced logging function with timestamp and stack info"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    caller = traceback.extract_stack()[-2]
    file = os.path.basename(caller.filename)
    line = caller.lineno
    print(f"[EmProps DEBUG {timestamp}] [{file}:{line}] {message}", flush=True)

class EmProps_Upscaler_Loader:
    """
    A custom upscaler loader that explicitly loads files by name,
    bypassing ComfyUI's selection mechanism. This ensures it can load
    files that were downloaded during the current execution.
    """
    RETURN_TYPES = ("UPSCALER",)
    RETURN_NAMES = ("UPSCALER",)
    OUTPUT_NODE = True
    FUNCTION = "load_upscaler"
    CATEGORY = "EmProps"
    
    @classmethod
    def INPUT_TYPES(cls):
        log_debug("EmProps_Upscaler_Loader.INPUT_TYPES called")
        return {
            "required": {
                "upscaler_name": ("STRING", {"multiline": False, "default": ""}),
            },
            "hidden": {
                "node_id": "UNIQUE_ID"
            }
        }

    def load_upscaler(self, upscaler_name, node_id=None):
        log_debug(f"EmProps_Upscaler_Loader.load_upscaler called with upscaler_name={upscaler_name}, node_id={node_id}")
        
        if not upscaler_name:
            log_debug("EmProps_Upscaler_Loader: No upscaler name provided")
            raise ValueError("No upscaler name provided")
        
        # Force refresh the cache to ensure we see the latest files
        log_debug("EmProps_Upscaler_Loader: Refreshing upscaler cache")
        if "upscale_models" in folder_paths.filename_list_cache:
            del folder_paths.filename_list_cache["upscale_models"]
        
        # Get the updated file list
        upscaler_files = folder_paths.get_filename_list("upscale_models")
        log_debug(f"EmProps_Upscaler_Loader: Available upscalers: {upscaler_files}")
        
        # Check if the file exists
        max_attempts = 5
        attempt = 0
        upscaler_path = None
        
        while attempt < max_attempts:
            try:
                log_debug(f"EmProps_Upscaler_Loader: Attempt {attempt+1} to get path for {upscaler_name}")
                upscaler_path = folder_paths.get_full_path("upscale_models", upscaler_name)
                if upscaler_path:
                    log_debug(f"EmProps_Upscaler_Loader: Found upscaler at {upscaler_path}")
                    break
            except Exception as e:
                log_debug(f"EmProps_Upscaler_Loader: Error getting path: {str(e)}")
                
            # If not found, wait a bit and try again (in case it's still being written)
            log_debug(f"EmProps_Upscaler_Loader: Upscaler {upscaler_name} not found, waiting...")
            time.sleep(1)
            
            # Refresh the cache again
            if "upscale_models" in folder_paths.filename_list_cache:
                del folder_paths.filename_list_cache["upscale_models"]
            folder_paths.get_filename_list("upscale_models")
            
            attempt += 1
        
        if not upscaler_path:
            log_debug(f"EmProps_Upscaler_Loader: Upscaler {upscaler_name} not found after {max_attempts} attempts")
            raise ValueError(f"Upscaler {upscaler_name} not found after {max_attempts} attempts")
        
        # Load the upscaler
        log_debug(f"EmProps_Upscaler_Loader: Loading upscaler from {upscaler_path}")
        try:
            # Send a progress update
            if node_id:
                PromptServer.instance.send_sync("progress", {
                    "node": node_id,
                    "value": 0,
                    "max": 100
                })
            
            # Load the upscaler model
            upscaler = comfy.utils.load_torch_file(upscaler_path)
            
            # Send completion progress
            if node_id:
                PromptServer.instance.send_sync("progress", {
                    "node": node_id,
                    "value": 100,
                    "max": 100
                })
            
            log_debug(f"EmProps_Upscaler_Loader: Successfully loaded upscaler {upscaler_name}")
            return (upscaler,)
            
        except Exception as e:
            log_debug(f"EmProps_Upscaler_Loader: Error loading upscaler: {str(e)}")
            raise e

# Node class mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "EmProps_Upscaler_Loader": EmProps_Upscaler_Loader,
}

# Human-readable names for the UI
NODE_DISPLAY_NAME_MAPPINGS = {
    "EmProps_Upscaler_Loader": "EmProps Upscaler Loader",
}
