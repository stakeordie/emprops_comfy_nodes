import os
import time
import traceback
from server import PromptServer
import sys
import folder_paths
import comfy.sd
import torch

# [2025-05-30T10:38:56-04:00] Custom Diffusion Model loader implementation (UNETLoader)
def log_debug(message):
    """Enhanced logging function with timestamp and stack info"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    caller = traceback.extract_stack()[-2]
    file = os.path.basename(caller.filename)
    line = caller.lineno
    print(f"[EmProps DEBUG {timestamp}] [{file}:{line}] {message}", flush=True)

class EmProps_Diffusion_Model_Loader:
    """
    A custom diffusion model loader that matches the ComfyUI UNETLoader structure
    but with EmProps' custom downloading and offloading capabilities.
    """
    RETURN_TYPES = ("MODEL",)
    RETURN_NAMES = ("MODEL",)
    OUTPUT_NODE = True
    FUNCTION = "load_unet"
    CATEGORY = "EmProps"
    
    DESCRIPTION = "Loads a diffusion model with EmProps' custom downloading and offloading capabilities."
    
    @classmethod
    def INPUT_TYPES(cls):
        log_debug("EmProps_Diffusion_Model_Loader.INPUT_TYPES called")
        return {
            "required": {
                "unet_name": ("STRING", {"multiline": False, "default": ""}),
                "weight_dtype": ([
                    "default", 
                    "fp8_e4m3fn", 
                    "fp8_e4m3fn_fast", 
                    "fp8_e5m2"
                ], {"default": "default"}),
            },
            "hidden": {
                "node_id": "UNIQUE_ID"
            }
        }

    def load_unet(self, unet_name, weight_dtype="default", node_id=None):
        log_debug(f"EmProps_Diffusion_Model_Loader.load_unet called with unet_name={unet_name}, weight_dtype={weight_dtype}, node_id={node_id}")
        
        if not unet_name:
            log_debug("EmProps_Diffusion_Model_Loader: No model name provided")
            raise ValueError("No model name provided")
        
        # Set model options based on weight_dtype
        model_options = {}
        if weight_dtype == "fp8_e4m3fn":
            model_options["dtype"] = torch.float8_e4m3fn
        elif weight_dtype == "fp8_e4m3fn_fast":
            model_options["dtype"] = torch.float8_e4m3fn
            model_options["fp8_optimizations"] = True
        elif weight_dtype == "fp8_e5m2":
            model_options["dtype"] = torch.float8_e5m2
        
        # Force refresh the cache to ensure we see the latest files
        log_debug("EmProps_Diffusion_Model_Loader: Refreshing diffusion_models cache")
        if "diffusion_models" in folder_paths.filename_list_cache:
            del folder_paths.filename_list_cache["diffusion_models"]
        
        # Get the updated file list
        model_files = folder_paths.get_filename_list("diffusion_models")
        log_debug(f"EmProps_Diffusion_Model_Loader: Available diffusion models: {model_files}")
        
        # Check if the file exists
        max_attempts = 5
        attempt = 0
        model_path = None
        
        while attempt < max_attempts:
            try:
                log_debug(f"EmProps_Diffusion_Model_Loader: Attempt {attempt+1} to get path for {unet_name}")
                model_path = folder_paths.get_full_path("diffusion_models", unet_name)
                if model_path:
                    log_debug(f"EmProps_Diffusion_Model_Loader: Found model at {model_path}")
                    break
            except Exception as e:
                log_debug(f"EmProps_Diffusion_Model_Loader: Error getting path: {str(e)}")
                
            # If not found, wait a bit and try again (in case it's still being written)
            log_debug(f"EmProps_Diffusion_Model_Loader: Model {unet_name} not found, waiting...")
            time.sleep(1)
            
            # Refresh the cache again
            if "diffusion_models" in folder_paths.filename_list_cache:
                del folder_paths.filename_list_cache["diffusion_models"]
            folder_paths.get_filename_list("diffusion_models")
            
            attempt += 1
        
        if not model_path:
            log_debug(f"EmProps_Diffusion_Model_Loader: Model {unet_name} not found after {max_attempts} attempts")
            raise ValueError(f"Model {unet_name} not found after {max_attempts} attempts")
        
        # Load the model
        log_debug(f"EmProps_Diffusion_Model_Loader: Loading model from {model_path} with options {model_options}")
        try:
            # Send a progress update
            if node_id:
                PromptServer.instance.send_sync("progress", {
                    "node": node_id,
                    "value": 0,
                    "max": 100
                })
            
            # Load the model using the same function as UNETLoader
            model = comfy.sd.load_diffusion_model(model_path, model_options=model_options)
            
            # Send completion progress
            if node_id:
                PromptServer.instance.send_sync("progress", {
                    "node": node_id,
                    "value": 100,
                    "max": 100
                })
            
            log_debug(f"EmProps_Diffusion_Model_Loader: Successfully loaded model {unet_name}")
            return (model,)
            
        except Exception as e:
            log_debug(f"EmProps_Diffusion_Model_Loader: Error loading model: {str(e)}")
            raise e

# Node class mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "EmProps_Diffusion_Model_Loader": EmProps_Diffusion_Model_Loader,
}

# Human-readable names for the UI
NODE_DISPLAY_NAME_MAPPINGS = {
    "EmProps_Diffusion_Model_Loader": "EmProps Load Diffusion Model",
}
