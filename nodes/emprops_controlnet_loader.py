import os
import time
import traceback
from server import PromptServer
import folder_paths
import comfy.controlnet
# Added: 2025-05-13T17:20:00-04:00 - Import model cache database
from ..db.model_cache import model_cache_db

# Added: 2025-05-13T16:59:30-04:00 - Custom ControlNet loader implementation
def log_debug(message):
    """Enhanced logging function with timestamp and stack info"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    caller = traceback.extract_stack()[-2]
    file = os.path.basename(caller.filename)
    line = caller.lineno
    print(f"[EmProps DEBUG {timestamp}] [{file}:{line}] {message}", flush=True)

class EmProps_ControlNet_Loader:
    """
    A custom ControlNet loader that explicitly loads files by name,
    bypassing ComfyUI's selection mechanism. This ensures it can load
    files that were downloaded during the current execution.
    """
    RETURN_TYPES = ("CONTROL_NET",)
    RETURN_NAMES = ("CONTROL_NET",)
    OUTPUT_NODE = True
    FUNCTION = "load_controlnet"
    CATEGORY = "EmProps"
    
    @classmethod
    def INPUT_TYPES(cls):
        log_debug("EmProps_ControlNet_Loader.INPUT_TYPES called")
        return {
            "required": {
                "controlnet_name": ("STRING", {"multiline": False, "default": ""}),
            },
            "hidden": {
                "node_id": "UNIQUE_ID"
            }
        }

    def load_controlnet(self, controlnet_name, node_id=None):
        log_debug(f"EmProps_ControlNet_Loader.load_controlnet called with controlnet_name={controlnet_name}, node_id={node_id}")
        
        if not controlnet_name:
            log_debug("EmProps_ControlNet_Loader: No ControlNet name provided")
            raise ValueError("No ControlNet name provided")
        
        # Force refresh the cache to ensure we see the latest files
        log_debug("EmProps_ControlNet_Loader: Refreshing ControlNet cache")
        if "controlnet" in folder_paths.filename_list_cache:
            del folder_paths.filename_list_cache["controlnet"]
        
        # Get the updated file list
        controlnet_files = folder_paths.get_filename_list("controlnet")
        log_debug(f"EmProps_ControlNet_Loader: Available ControlNets: {controlnet_files}")
        
        # Check if the file exists
        max_attempts = 5
        attempt = 0
        controlnet_path = None
        
        while attempt < max_attempts:
            try:
                log_debug(f"EmProps_ControlNet_Loader: Attempt {attempt+1} to get path for {controlnet_name}")
                controlnet_path = folder_paths.get_full_path("controlnet", controlnet_name)
                if controlnet_path:
                    log_debug(f"EmProps_ControlNet_Loader: Found ControlNet at {controlnet_path}")
                    break
            except Exception as e:
                log_debug(f"EmProps_ControlNet_Loader: Error getting path: {str(e)}")
                
            # If not found, wait a bit and try again (in case it's still being written)
            log_debug(f"EmProps_ControlNet_Loader: ControlNet {controlnet_name} not found, waiting...")
            time.sleep(1)
            
            # Refresh the cache again
            if "controlnet" in folder_paths.filename_list_cache:
                del folder_paths.filename_list_cache["controlnet"]
            folder_paths.get_filename_list("controlnet")
            
            attempt += 1
        
        if not controlnet_path:
            log_debug(f"EmProps_ControlNet_Loader: ControlNet {controlnet_name} not found after {max_attempts} attempts")
            raise ValueError(f"ControlNet {controlnet_name} not found after {max_attempts} attempts")
        
        # Load the ControlNet
        log_debug(f"EmProps_ControlNet_Loader: Loading ControlNet from {controlnet_path}")
        try:
            # Send a progress update
            if node_id:
                PromptServer.instance.send_sync("progress", {
                    "node": node_id,
                    "value": 0,
                    "max": 100
                })
            
            # Load the ControlNet model
            controlnet = comfy.controlnet.load_controlnet(controlnet_path)
            
            # Added: 2025-05-13T17:20:00-04:00 - Update model usage in cache database
            try:
                model_cache_db.update_model_usage(controlnet_path)
                log_debug(f"Updated model usage in cache database: {controlnet_path}")
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
            
            log_debug(f"EmProps_ControlNet_Loader: Successfully loaded ControlNet {controlnet_name}")
            return (controlnet,)
            
        except Exception as e:
            log_debug(f"EmProps_ControlNet_Loader: Error loading ControlNet: {str(e)}")
            raise e

# Node class mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "EmProps_ControlNet_Loader": EmProps_ControlNet_Loader,
}

# Human-readable names for the UI
NODE_DISPLAY_NAME_MAPPINGS = {
    "EmProps_ControlNet_Loader": "EmProps ControlNet Loader",
}
