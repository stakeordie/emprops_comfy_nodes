# [2025-06-02T16:30:00-04:00] Added GGUF Unet Loader for EmProps
import os
import sys
import torch
import logging
from server import PromptServer
import folder_paths
import comfy.sd

# Add GGUF nodes to path
gguf_nodes_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'ComfyUI-GGUF')
if gguf_nodes_path not in sys.path:
    sys.path.append(gguf_nodes_path)

try:
    from nodes import GGUFModelPatcher
    from loader import gguf_sd_loader
    from ops import GGMLOps
except ImportError as e:
    print(f"[EmProps GGUF ERROR] Failed to import GGUF components: {str(e)}")
    print(f"[EmProps GGUF ERROR] Tried to import from: {gguf_nodes_path}")
    GGUFModelPatcher = None
    gguf_sd_loader = None
    GGMLOps = None

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

    def load_unet(self, unet_name, device="cuda"):
        """
        Load a GGUF UNet model
        
        Args:
            unet_name (str): Name or full path of the GGUF model file
            device (str): Device to load the model on (default: 'cuda')
            
        Returns:
            tuple: (model_patcher, clip, vae)
        """
        # Check if unet_name is already a full path
        if os.path.isfile(unet_name):
            unet_path = unet_name
        else:
            # Try to get the full path using folder_paths
            unet_path = folder_paths.get_full_path("unet_gguf", unet_name)
            if unet_path is None:
                # Check in the default models directory
                models_dir = os.path.join(folder_paths.models_dir, "unet")
                potential_path = os.path.join(models_dir, unet_name)
                if os.path.isfile(potential_path):
                    unet_path = potential_path
                else:
                    raise ValueError(f"GGUF model file not found: {unet_name}\n"
                                 f"Searched in:\n"
                                 f"- folder_paths.get_full_path('unet_gguf')\n"
                                 f"- {models_dir}")
        
        if not os.path.isfile(unet_path):
            raise ValueError(f"GGUF model file not found: {unet_path}")
            
        print(f"[EmProps] Loading GGUF model from: {unet_path}")
        
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
