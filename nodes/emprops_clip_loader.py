import os
import time
import traceback
from server import PromptServer
import sys
import folder_paths
import comfy.sd
import torch

# [2025-05-30T10:38:56-04:00] Custom CLIP loader implementation (CLIPLoader)
def log_debug(message):
    """Enhanced logging function with timestamp and stack info"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    caller = traceback.extract_stack()[-2]
    file = os.path.basename(caller.filename)
    line = caller.lineno
    print(f"[EmProps DEBUG {timestamp}] [{file}:{line}] {message}", flush=True)

class EmProps_CLIP_Loader:
    """
    A custom CLIP loader that matches the ComfyUI CLIPLoader structure
    but with EmProps' custom downloading and offloading capabilities.
    """
    RETURN_TYPES = ("CLIP",)
    RETURN_NAMES = ("CLIP",)
    OUTPUT_NODE = True
    FUNCTION = "load_clip"
    CATEGORY = "EmProps"
    
    DESCRIPTION = """Loads a CLIP model with EmProps' custom downloading and offloading capabilities.

[Recipes]
stable_diffusion: clip-l
stable_cascade: clip-g
sd3: t5 xxl/ clip-g / clip-l
stable_audio: t5 base
mochi: t5 xxl
cosmos: old t5 xxl
lumina2: gemma 2 2B
wan: umt5 xxl
hidream: llama-3.1 (Recommend) or t5"""
    
    @classmethod
    def INPUT_TYPES(cls):
        log_debug("EmProps_CLIP_Loader.INPUT_TYPES called")
        return {
            "required": {
                "clip_name": ("STRING", {"multiline": False, "default": ""}),
                "type": ([
                    "stable_diffusion", 
                    "stable_cascade", 
                    "sd3", 
                    "stable_audio", 
                    "mochi", 
                    "ltxv", 
                    "pixart", 
                    "cosmos", 
                    "lumina2", 
                    "wan", 
                    "hidream", 
                    "chroma", 
                    "ace"
                ], {"default": "stable_diffusion"}),
            },
            "optional": {
                "device": (["default", "cpu"], {"default": "default", "advanced": True}),
            },
            "hidden": {
                "node_id": "UNIQUE_ID"
            }
        }

    def load_clip(self, clip_name, type="stable_diffusion", device="default", node_id=None):
        log_debug(f"EmProps_CLIP_Loader.load_clip called with clip_name={clip_name}, type={type}, device={device}, node_id={node_id}")
        
        if not clip_name:
            log_debug("EmProps_CLIP_Loader: No CLIP name provided")
            raise ValueError("No CLIP name provided")
        
        # Set clip type
        clip_type = getattr(comfy.sd.CLIPType, type.upper(), comfy.sd.CLIPType.STABLE_DIFFUSION)
        
        # Set model options based on device
        model_options = {}
        if device == "cpu":
            model_options["load_device"] = model_options["offload_device"] = torch.device("cpu")
        
        # Force refresh the cache to ensure we see the latest files
        log_debug("EmProps_CLIP_Loader: Refreshing text_encoders cache")
        if "text_encoders" in folder_paths.filename_list_cache:
            del folder_paths.filename_list_cache["text_encoders"]
        
        # Get the updated file list
        clip_files = folder_paths.get_filename_list("text_encoders")
        log_debug(f"EmProps_CLIP_Loader: Available CLIP models: {clip_files}")
        
        # Check if the file exists
        max_attempts = 5
        attempt = 0
        clip_path = None
        
        while attempt < max_attempts:
            try:
                log_debug(f"EmProps_CLIP_Loader: Attempt {attempt+1} to get path for {clip_name}")
                clip_path = folder_paths.get_full_path("text_encoders", clip_name)
                if clip_path:
                    log_debug(f"EmProps_CLIP_Loader: Found CLIP at {clip_path}")
                    break
            except Exception as e:
                log_debug(f"EmProps_CLIP_Loader: Error getting path: {str(e)}")
                
            # If not found, wait a bit and try again (in case it's still being written)
            log_debug(f"EmProps_CLIP_Loader: CLIP {clip_name} not found, waiting...")
            time.sleep(1)
            
            # Refresh the cache again
            if "text_encoders" in folder_paths.filename_list_cache:
                del folder_paths.filename_list_cache["text_encoders"]
            folder_paths.get_filename_list("text_encoders")
            
            attempt += 1
        
        if not clip_path:
            log_debug(f"EmProps_CLIP_Loader: CLIP {clip_name} not found after {max_attempts} attempts")
            raise ValueError(f"CLIP {clip_name} not found after {max_attempts} attempts")
        
        # Load the model
        log_debug(f"EmProps_CLIP_Loader: Loading CLIP from {clip_path} with type {clip_type} and options {model_options}")
        try:
            # Send a progress update
            if node_id:
                PromptServer.instance.send_sync("progress", {
                    "node": node_id,
                    "value": 0,
                    "max": 100
                })
            
            # Load the CLIP model using the same function as CLIPLoader
            clip = comfy.sd.load_clip(
                ckpt_paths=[clip_path], 
                embedding_directory=folder_paths.get_folder_paths("embeddings"), 
                clip_type=clip_type, 
                model_options=model_options
            )
            
            # Send completion progress
            if node_id:
                PromptServer.instance.send_sync("progress", {
                    "node": node_id,
                    "value": 100,
                    "max": 100
                })
            
            log_debug(f"EmProps_CLIP_Loader: Successfully loaded CLIP {clip_name}")
            return (clip,)
            
        except Exception as e:
            log_debug(f"EmProps_CLIP_Loader: Error loading CLIP: {str(e)}")
            raise e

# Node class mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "EmProps_CLIP_Loader": EmProps_CLIP_Loader,
}

# Human-readable names for the UI
NODE_DISPLAY_NAME_MAPPINGS = {
    "EmProps_CLIP_Loader": "EmProps Load CLIP",
}
