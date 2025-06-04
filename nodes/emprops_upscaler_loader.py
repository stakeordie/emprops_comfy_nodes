import os
import time
import traceback
import logging
from server import PromptServer
import folder_paths
import comfy.utils
import torch
from comfy import model_management

# Flag: 2025-06-04 18:55 - Added spandrel imports for proper upscaler loading
try:
    from spandrel import ModelLoader, ImageModelDescriptor
    from spandrel import MAIN_REGISTRY
    try:
        from spandrel_extra_arches import EXTRA_REGISTRY
        MAIN_REGISTRY.add(*EXTRA_REGISTRY)
        logging.info("Successfully imported spandrel_extra_arches: support for non commercial upscale models.")
    except ImportError:
        logging.info("spandrel_extra_arches not found. Only standard upscale models will be supported.")
    SPANDREL_AVAILABLE = True
except ImportError:
    logging.warning("spandrel not found. Upscaler loading will use fallback method.")
    SPANDREL_AVAILABLE = False

# Added: 2025-05-13T16:58:00-04:00 - Custom Upscaler loader implementation
def log_debug(message):
    """Enhanced logging function with timestamp and stack info"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    caller = traceback.extract_stack()[-2]
    file = os.path.basename(caller.filename)
    line = caller.lineno
    print(f"[EmProps DEBUG {timestamp}] [{file}:{line}] {message}", flush=True)

class EmProps_Load_Upscale_Model:
    """
    A custom upscaler loader that explicitly loads files by name,
    bypassing ComfyUI's selection mechanism. This ensures it can load
    files that were downloaded during the current execution.
    
    Updated: 2025-06-04 18:55 - Changed to match ComfyUI's UpscaleModelLoader output type
    Updated: 2025-06-04 18:56 - Renamed to EmProps_Load_Upscale_Model for consistency
    """
    RETURN_TYPES = ("UPSCALE_MODEL",)
    RETURN_NAMES = ("upscale_model",)
    OUTPUT_NODE = True
    FUNCTION = "load_upscaler"
    CATEGORY = "EmProps"
    
    @classmethod
    def INPUT_TYPES(cls):
        log_debug("EmProps_Load_Upscale_Model.INPUT_TYPES called")
        return {
            "required": {
                "upscaler_name": ("STRING", {"multiline": False, "default": ""}),
            },
            "hidden": {
                "node_id": "UNIQUE_ID"
            }
        }

    def load_upscaler(self, upscaler_name, node_id=None):
        log_debug(f"EmProps_Load_Upscale_Model.load_upscaler called with upscaler_name={upscaler_name}, node_id={node_id}")
        
        if not upscaler_name:
            log_debug("EmProps_Load_Upscale_Model: No upscaler name provided")
            raise ValueError("No upscaler name provided")
        
        # Force refresh the cache to ensure we see the latest files
        log_debug("EmProps_Load_Upscale_Model: Refreshing upscaler cache")
        if "upscale_models" in folder_paths.filename_list_cache:
            del folder_paths.filename_list_cache["upscale_models"]
        
        # Get the updated file list
        upscaler_files = folder_paths.get_filename_list("upscale_models")
        log_debug(f"EmProps_Load_Upscale_Model: Available upscalers: {upscaler_files}")
        
        # Check if the file exists
        max_attempts = 5
        attempt = 0
        upscaler_path = None
        
        while attempt < max_attempts:
            try:
                log_debug(f"EmProps_Load_Upscale_Model: Attempt {attempt+1} to get path for {upscaler_name}")
                upscaler_path = folder_paths.get_full_path("upscale_models", upscaler_name)
                if upscaler_path and os.path.exists(upscaler_path):
                    log_debug(f"EmProps_Load_Upscale_Model: Found upscaler at {upscaler_path}")
                    break
            except Exception as e:
                log_debug(f"EmProps_Load_Upscale_Model: Error getting path: {str(e)}")
                
            # If not found, wait a bit and try again (in case it's still being written)
            log_debug(f"EmProps_Load_Upscale_Model: Upscaler {upscaler_name} not found, waiting...")
            time.sleep(1)
            
            # Refresh the cache again
            if "upscale_models" in folder_paths.filename_list_cache:
                del folder_paths.filename_list_cache["upscale_models"]
            folder_paths.get_filename_list("upscale_models")
            
            attempt += 1
        
        if not upscaler_path or not os.path.exists(upscaler_path):
            log_debug(f"EmProps_Load_Upscale_Model: Upscaler {upscaler_name} not found after {max_attempts} attempts")
            raise ValueError(f"Upscaler {upscaler_name} not found after {max_attempts} attempts")
        
        # Load the upscaler
        log_debug(f"EmProps_Load_Upscale_Model: Loading upscaler from {upscaler_path}")
        try:
            # Send a progress update
            if node_id:
                PromptServer.instance.send_sync("progress", {
                    "node": node_id,
                    "value": 0,
                    "max": 100
                })
            
            # Flag: 2025-06-04 18:55 - Updated to match ComfyUI's upscaler loading logic
            # Load the upscaler model state dict
            sd = comfy.utils.load_torch_file(upscaler_path, safe_load=True)
            
            # Process state dict - same as in ComfyUI's UpscaleModelLoader
            if "module.layers.0.residual_group.blocks.0.norm1.weight" in sd:
                log_debug("EmProps_Load_Upscale_Model: Applying prefix replacement to state dict")
                sd = comfy.utils.state_dict_prefix_replace(sd, {"module.":""})
            
            # Use spandrel if available (preferred method)
            if SPANDREL_AVAILABLE:
                log_debug("EmProps_Load_Upscale_Model: Loading with spandrel ModelLoader")
                out = ModelLoader().load_from_state_dict(sd).eval()
                
                # Validate model type
                if not isinstance(out, ImageModelDescriptor):
                    log_debug("EmProps_Load_Upscale_Model: Model is not an ImageModelDescriptor")
                    raise Exception("Upscale model must be a single-image model.")
            else:
                # Fallback method if spandrel is not available
                log_debug("EmProps_Load_Upscale_Model: Using fallback loading method (spandrel not available)")
                out = sd
            
            # Send completion progress
            if node_id:
                PromptServer.instance.send_sync("progress", {
                    "node": node_id,
                    "value": 100,
                    "max": 100
                })
            
            log_debug(f"EmProps_Load_Upscale_Model: Successfully loaded upscaler {upscaler_name}")
            return (out, )
            
        except Exception as e:
            log_debug(f"EmProps_Load_Upscale_Model: Error loading upscaler: {str(e)}")
            raise e

# Flag: 2025-06-04 18:55 - Added ImageUpscaleWithModel node for convenience
class EmProps_ImageUpscaleWithModel:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": { "upscale_model": ("UPSCALE_MODEL",),
                              "image": ("IMAGE",),
                              }}
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "upscale"
    CATEGORY = "EmProps/image"

    def upscale(self, upscale_model, image):
        device = model_management.get_torch_device()

        memory_required = model_management.module_size(upscale_model.model)
        memory_required += (512 * 512 * 3) * image.element_size() * max(upscale_model.scale, 1.0) * 384.0 
        memory_required += image.nelement() * image.element_size()
        model_management.free_memory(memory_required, device)

        upscale_model.to(device)
        in_img = image.movedim(-1,-3).to(device)

        tile = 512
        overlap = 32

        oom = True
        while oom:
            try:
                steps = in_img.shape[0] * comfy.utils.get_tiled_scale_steps(in_img.shape[3], in_img.shape[2], tile_x=tile, tile_y=tile, overlap=overlap)
                pbar = comfy.utils.ProgressBar(steps)
                s = comfy.utils.tiled_scale(in_img, lambda a: upscale_model(a), tile_x=tile, tile_y=tile, overlap=overlap, upscale_amount=upscale_model.scale, pbar=pbar)
                oom = False
            except model_management.OOM_EXCEPTION as e:
                tile //= 2
                if tile < 128:
                    raise e

        upscale_model.to("cpu")
        s = torch.clamp(s.movedim(-3,-1), min=0, max=1.0)
        return (s,)

# Flag: 2025-06-04 18:56 - Updated class names for consistency with ComfyUI
# Node class mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "EmProps_Load_Upscale_Model": EmProps_Load_Upscale_Model,
    "EmProps_ImageUpscaleWithModel": EmProps_ImageUpscaleWithModel,
}

# Human-readable names for the UI
NODE_DISPLAY_NAME_MAPPINGS = {
    "EmProps_Load_Upscale_Model": "EmProps Load Upscale Model",
    "EmProps_ImageUpscaleWithModel": "EmProps Image Upscale With Model",
}
