import os
import time
import traceback
from server import PromptServer
import sys
import folder_paths
import comfy.sd
import torch

# [2025-06-23T14:45:00-08:00] Custom QuadrupleCLIP loader implementation
def log_debug(message):
    """Enhanced logging function with timestamp and stack info"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    caller = traceback.extract_stack()[-2]
    file = os.path.basename(caller.filename)
    line = caller.lineno
    print(f"[EmProps DEBUG {timestamp}] [{file}:{line}] {message}", flush=True)

class EmProps_QuadrupleCLIP_Loader:
    """
    A custom QuadrupleCLIP loader that explicitly loads files by name,
    bypassing ComfyUI's selection mechanism. This ensures it can load
    files that were downloaded during the current execution.
    """
    RETURN_TYPES = ("CLIP",)
    RETURN_NAMES = ("CLIP",)
    OUTPUT_NODE = True
    FUNCTION = "load_clip"
    CATEGORY = "EmProps"
    
    DESCRIPTION = "[Recipes]\n\nhidream: long clip-l, long clip-g, t5xxl, llama_8b_3.1_instruct"
    
    @classmethod
    def INPUT_TYPES(cls):
        log_debug("EmProps_QuadrupleCLIP_Loader.INPUT_TYPES called")
        return {
            "required": {
                "clip_name1": ("STRING", {"multiline": False, "default": ""}),
                "clip_name2": ("STRING", {"multiline": False, "default": ""}),
                "clip_name3": ("STRING", {"multiline": False, "default": ""}),
                "clip_name4": ("STRING", {"multiline": False, "default": ""}),
            },
            "optional": {
                "device": (["default", "cpu"], {"default": "default", "advanced": True}),
            },
            "hidden": {
                "node_id": "UNIQUE_ID"
            }
        }

    def load_clip(self, clip_name1, clip_name2, clip_name3, clip_name4, device="default", node_id=None):
        log_debug(f"EmProps_QuadrupleCLIP_Loader.load_clip called with clip_name1={clip_name1}, clip_name2={clip_name2}, clip_name3={clip_name3}, clip_name4={clip_name4}, device={device}, node_id={node_id}")
        
        if not clip_name1 or not clip_name2 or not clip_name3 or not clip_name4:
            log_debug("EmProps_QuadrupleCLIP_Loader: Missing clip names")
            raise ValueError("All four clip names must be provided")
        
        # Force refresh the cache to ensure we see the latest files
        log_debug("EmProps_QuadrupleCLIP_Loader: Refreshing text_encoders cache")
        if "text_encoders" in folder_paths.filename_list_cache:
            del folder_paths.filename_list_cache["text_encoders"]
        
        # Get the updated file list
        text_encoder_files = folder_paths.get_filename_list("text_encoders")
        log_debug(f"EmProps_QuadrupleCLIP_Loader: Available text encoders: {text_encoder_files}")
        
        # Check if the files exist with retry logic
        max_attempts = 5
        clip_paths = [None, None, None, None]
        clip_names = [clip_name1, clip_name2, clip_name3, clip_name4]
        
        for i, clip_name in enumerate(clip_names):
            attempt = 0
            while attempt < max_attempts:
                try:
                    log_debug(f"EmProps_QuadrupleCLIP_Loader: Attempt {attempt+1} to get path for {clip_name}")
                    clip_paths[i] = folder_paths.get_full_path("text_encoders", clip_name)
                    if clip_paths[i]:
                        log_debug(f"EmProps_QuadrupleCLIP_Loader: Found text encoder at {clip_paths[i]}")
                        break
                except Exception as e:
                    log_debug(f"EmProps_QuadrupleCLIP_Loader: Error getting path: {str(e)}")
                
                # If not found, wait a bit and try again (in case it's still being written)
                log_debug(f"EmProps_QuadrupleCLIP_Loader: Text encoder {clip_name} not found, waiting...")
                time.sleep(1)
                
                # Refresh the cache again
                if "text_encoders" in folder_paths.filename_list_cache:
                    del folder_paths.filename_list_cache["text_encoders"]
                folder_paths.get_filename_list("text_encoders")
                
                attempt += 1
            
            if not clip_paths[i]:
                log_debug(f"EmProps_QuadrupleCLIP_Loader: Text encoder {clip_name} not found after {max_attempts} attempts")
                raise ValueError(f"Text encoder {clip_name} not found after {max_attempts} attempts")
        
        # Load the clip models
        log_debug(f"EmProps_QuadrupleCLIP_Loader: Loading text encoders from {clip_paths}")
        try:
            # Send a progress update
            if node_id:
                PromptServer.instance.send_sync("progress", {
                    "node": node_id,
                    "value": 0,
                    "max": 100
                })
            
            # Set device options if needed
            model_options = {}
            if device == "cpu":
                model_options["load_device"] = model_options["offload_device"] = torch.device("cpu")
            
            # Load the clip models
            clip = comfy.sd.load_clip(
                ckpt_paths=[clip_paths[0], clip_paths[1], clip_paths[2], clip_paths[3]], 
                embedding_directory=folder_paths.get_folder_paths("embeddings"),
                model_options=model_options
            )
            
            # Send completion progress
            if node_id:
                PromptServer.instance.send_sync("progress", {
                    "node": node_id,
                    "value": 100,
                    "max": 100
                })
            
            log_debug(f"EmProps_QuadrupleCLIP_Loader: Successfully loaded text encoders {clip_name1}, {clip_name2}, {clip_name3}, and {clip_name4}")
            return (clip,)
            
        except Exception as e:
            log_debug(f"EmProps_QuadrupleCLIP_Loader: Error loading text encoders: {str(e)}")
            raise e

# Node class mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "EmProps_QuadrupleCLIP_Loader": EmProps_QuadrupleCLIP_Loader,
}

# Human-readable names for the UI
NODE_DISPLAY_NAME_MAPPINGS = {
    "EmProps_QuadrupleCLIP_Loader": "EmProps QuadrupleCLIP Loader",
}