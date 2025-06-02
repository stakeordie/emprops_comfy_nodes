import os
import torch
import folder_paths
import comfy.sd
from ..utils import log_debug
from comfy.cli_args import args
from server import PromptServer

class EmProps_Style_Model_Loader:
    """
    A custom Style Model loader that explicitly loads files by name,
    bypassing ComfyUI's selection mechanism. This ensures it can load
    files that were downloaded during the current execution.
    """
    RETURN_TYPES = ("STYLE_MODEL",)
    RETURN_NAMES = ("STYLE_MODEL",)
    OUTPUT_NODE = True
    FUNCTION = "load_style_model"
    CATEGORY = "EmProps"
    
    @classmethod
    def INPUT_TYPES(cls):
        log_debug("EmProps_Style_Model_Loader.INPUT_TYPES called")
        return {
            "required": {
                "style_model_name": ("STRING", {"multiline": False, "default": ""}),
            },
            "hidden": {
                "node_id": "UNIQUE_ID"
            }
        }

    def load_style_model(self, style_model_name, node_id=None):
        log_debug(f"EmProps_Style_Model_Loader.load_style_model called with style_model_name={style_model_name}")
        
        if not style_model_name:
            raise ValueError("Style model name cannot be empty")
            
        try:
            # Send progress update
            if node_id:
                PromptServer.instance.send_sync("progress", {
                    "node": node_id,
                    "value": 0,
                    "max": 100
                })
            
            # Get the full path to the style model
            style_model_path = folder_paths.get_full_path_or_raise("style_models", style_model_name)
            
            # Send loading progress
            if node_id:
                PromptServer.instance.send_sync("progress", {
                    "node": node_id,
                    "value": 50,
                    "max": 100
                })
            
            # Load the style model
            style_model = comfy.sd.load_style_model(style_model_path)
            
            # Send completion progress
            if node_id:
                PromptServer.instance.send_sync("progress", {
                    "node": node_id,
                    "value": 100,
                    "max": 100
                })
            
            log_debug(f"EmProps_Style_Model_Loader: Successfully loaded style model {style_model_name}")
            return (style_model,)
            
        except Exception as e:
            log_debug(f"EmProps_Style_Model_Loader: Error loading style model: {str(e)}")
            raise e

# For backwards compatibility with some workflows
EmPropsLoadStyleModel = EmProps_Style_Model_Loader
