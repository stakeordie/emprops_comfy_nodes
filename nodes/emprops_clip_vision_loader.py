import os
import torch
import folder_paths
import comfy.clip_vision
from ..utils import log_debug
from comfy.cli_args import args
from server import PromptServer

class EmProps_CLIP_Vision_Loader:
    """
    A custom CLIP Vision loader that explicitly loads files by name,
    bypassing ComfyUI's selection mechanism. This ensures it can load
    files that were downloaded during the current execution.
    """
    RETURN_TYPES = ("CLIP_VISION",)
    RETURN_NAMES = ("CLIP_VISION",)
    OUTPUT_NODE = True
    FUNCTION = "load_clip_vision"
    CATEGORY = "EmProps"
    
    @classmethod
    def INPUT_TYPES(cls):
        log_debug("EmProps_CLIP_Vision_Loader.INPUT_TYPES called")
        return {
            "required": {
                "clip_vision_name": ("STRING", {"multiline": False, "default": ""}),
            },
            "hidden": {
                "node_id": "UNIQUE_ID"
            }
        }

    def load_clip_vision(self, clip_vision_name, node_id=None):
        log_debug(f"EmProps_CLIP_Vision_Loader.load_clip_vision called with clip_vision_name={clip_vision_name}")
        
        if not clip_vision_name:
            raise ValueError("CLIP vision model name cannot be empty")
            
        try:
            # Send progress update
            if node_id:
                PromptServer.instance.send_sync("progress", {
                    "node": node_id,
                    "value": 0,
                    "max": 100
                })
            
            # Get the full path to the CLIP vision model
            clip_vision_path = folder_paths.get_full_path_or_raise("clip_vision", clip_vision_name)
            
            # Send loading progress
            if node_id:
                PromptServer.instance.send_sync("progress", {
                    "node": node_id,
                    "value": 50,
                    "max": 100
                })
            
            # Load the CLIP vision model
            clip_vision = comfy.clip_vision.load(clip_vision_path)
            
            if clip_vision is None:
                raise RuntimeError("ERROR: CLIP vision file is invalid and does not contain a valid vision model.")
            
            # Send completion progress
            if node_id:
                PromptServer.instance.send_sync("progress", {
                    "node": node_id,
                    "value": 100,
                    "max": 100
                })
            
            log_debug(f"EmProps_CLIP_Vision_Loader: Successfully loaded CLIP vision model {clip_vision_name}")
            return (clip_vision,)
            
        except Exception as e:
            log_debug(f"EmProps_CLIP_Vision_Loader: Error loading CLIP vision model: {str(e)}")
            raise e

# For backwards compatibility with some workflows
EmPropsLoadCLIPVision = EmProps_CLIP_Vision_Loader
