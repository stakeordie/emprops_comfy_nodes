# [2025-06-02T16:30:00-04:00] Added Advanced GGUF Unet Loader for EmProps
# [2025-06-02T18:28:00-04:00] Updated to better match original implementation
import os
import sys
import torch
import logging
import folder_paths
import comfy.sd

# Add GGUF nodes to path
gguf_nodes_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'ComfyUI-GGUF')
if gguf_nodes_path not in sys.path:
    sys.path.append(gguf_nodes_path)

try:
    from ComfyUI_GGUF.nodes import GGUFModelPatcher
    from ComfyUI_GGUF.loader import gguf_sd_loader
    from ComfyUI_GGUF.ops import GGMLOps
except ImportError as e:
    logger.error(f"[EmProps GGUF ADVANCED ERROR] Failed to import GGUF components: {str(e)}")
    logger.error("[EmProps GGUF ADVANCED ERROR] Make sure ComfyUI-GGUF is installed in your custom_nodes directory")
    GGUFModelPatcher = None
    gguf_sd_loader = None
    GGMLOps = None

# Initialize logging
logger = logging.getLogger(__name__)

class EmProps_GGUF_Unet_Loader_Advanced:
    """
    EmProps Advanced GGUF Unet Loader - Loads a UNet model from a GGUF file with advanced options.
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "unet_name": ("STRING", {"default": ""}),  # Accept string input for asset downloader compatibility
                "dequant_dtype": (["default", "target", "float32", "float16", "bfloat16"], {"default": "default"}),
                "patch_dtype": (["default", "target", "float32", "float16", "bfloat16"], {"default": "default"}),
                "patch_on_device": (["false", "true"], {"default": "false"}),
            },
            "hidden": {
                "node_id": "UNIQUE_ID"
            }
        }

    RETURN_TYPES = ("MODEL",)
    RETURN_NAMES = ("model",)
    FUNCTION = "load_unet"
    CATEGORY = "EmProps/Loaders"
    TITLE = "Unet Loader (GGUF/Advanced)"

    def load_unet(self, unet_name, dequant_dtype="default", patch_dtype="default", patch_on_device="false", node_id=None):
        """
        Load a GGUF UNet model with advanced options
        
        Args:
            unet_name (str): Name of the GGUF model file
            dequant_dtype (str): Dtype for dequantization (default: "default")
            patch_dtype (str): Dtype for patching (default: "default")
            patch_on_device (str): Whether to patch on device (default: "false")
            node_id (str): Optional node ID for logging
            
        Returns:
            tuple: (model,)
        """
        logger.info(f"[EmProps] Loading GGUF model (Advanced): {unet_name}")
        
        # Convert string boolean to actual boolean
        patch_on_device = patch_on_device.lower() == "true"
        
        # Initialize GGML operations
        ops = GGMLOps()
        
        # Configure dequantization dtype
        if dequant_dtype not in ("default", None):
            if dequant_dtype == "target":
                logger.debug(f"[EmProps] Setting dequant_dtype to target")
                ops.Linear.dequant_dtype = dequant_dtype
            else:
                logger.debug(f"[EmProps] Setting dequant_dtype to {dequant_dtype}")
                ops.Linear.dequant_dtype = getattr(torch, dequant_dtype)
        
        # Configure patch dtype
        if patch_dtype not in ("default", None):
            if patch_dtype == "target":
                logger.debug("[EmProps] Setting patch_dtype to target")
                ops.Linear.patch_dtype = patch_dtype
            else:
                logger.debug(f"[EmProps] Setting patch_dtype to {patch_dtype}")
                ops.Linear.patch_dtype = getattr(torch, patch_dtype)
        
        try:
            # First try to get the full path directly (for absolute paths or files in search paths)
            unet_path = folder_paths.get_full_path("unet_gguf", unet_name)
            
            # If not found, try to find the file in the unet_gguf directory
            if not unet_path or not os.path.isfile(unet_path):
                # Check if the file exists directly
                if os.path.isfile(unet_name):
                    unet_path = unet_name
                else:
                    # Try to find the file in the unet_gguf directory
                    unet_dir = folder_paths.get_folder_paths("unet_gguf")[0]
                    possible_path = os.path.join(unet_dir, unet_name)
                    if os.path.isfile(possible_path):
                        unet_path = possible_path
                    else:
                        raise FileNotFoundError(
                            f"GGUF model file not found: {unet_name}\n"
                            f"Searched in: {unet_dir}"
                        )
            
            logger.info(f"[EmProps] Loading GGUF model from: {unet_path}")
            
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
            model.patch_on_device = patch_on_device
            
            logger.info(f"[EmProps] Successfully loaded GGUF model (Advanced): {unet_name}")
            return (model,)
            
        except Exception as e:
            logger.error(f"[EmProps] Error loading GGUF model {unet_name}: {str(e)}")
            raise

# Node class mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "EmProps_GGUF_Unet_Loader_Advanced": EmProps_GGUF_Unet_Loader_Advanced,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EmProps_GGUF_Unet_Loader_Advanced": "Unet Loader (GGUF/Advanced)",
}
