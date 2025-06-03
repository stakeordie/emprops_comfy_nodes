# [2025-06-02T16:30:00-04:00] Added GGUF Unet Loader for EmProps
import os
import torch
import logging
from server import PromptServer
import folder_paths
import comfy.sd

# Import GGUF components
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ComfyUI/custom_nodes/ComfyUI-GGUF'))
from nodes import GGUFModelPatcher
from loader import gguf_sd_loader
from ops import GGMLOps

class EmProps_GGUF_Unet_Loader:
    """
    EmProps GGUF Unet Loader - Loads a UNet model from a GGUF file.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "unet_path": ("STRING", {"multiline": False, "default": ""}),
            },
            "hidden": {
                "node_id": "UNIQUE_ID"
            }
        }

    RETURN_TYPES = ("MODEL",)
    RETURN_NAMES = ("model",)
    FUNCTION = "load_unet"
    CATEGORY = "EmProps/Loaders"
    TITLE = "Unet Loader (GGUF)"

    def load_unet(self, unet_path, node_id=None):
        if not unet_path or not os.path.exists(unet_path):
            raise ValueError(f"GGUF model file not found: {unet_path}")

        # Initialize GGML operations
        ops = GGMLOps()
        
        try:
            # Load the model state dict from GGUF file
            sd = gguf_sd_loader(unet_path)
            
            # Load the diffusion model using ComfyUI's loader
            model = comfy.sd.load_diffusion_model_state_dict(
                sd, 
                model_options={"custom_operations": ops}
            )
            
            if model is None:
                raise RuntimeError(f"Failed to load GGUF model: {unet_path}")
                
            # Wrap in GGUF model patcher
            model = GGUFModelPatcher.clone(model)
            model.patch_on_device = False
            
            return (model,)
            
        except Exception as e:
            raise RuntimeError(f"Error loading GGUF model {unet_path}: {str(e)}")

# Node class mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "EmProps_GGUF_Unet_Loader": EmProps_GGUF_Unet_Loader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EmProps_GGUF_Unet_Loader": "Unet Loader (GGUF)",
}
