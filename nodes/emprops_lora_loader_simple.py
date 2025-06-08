import os
import time
import traceback
import folder_paths
from server import PromptServer
from nodes import LoraLoader
import comfy.sd

def log_debug(message):
    """Enhanced logging function with timestamp and stack info"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    caller = traceback.extract_stack()[-2]
    file = os.path.basename(caller.filename)
    line = caller.lineno
    print(f"[EmProps DEBUG {timestamp}] [{file}:{line}] {message}", flush=True)

class EmProps_Lora_Loader_Simple:
    """
    A simplified LoRA loader that accepts a string input for the LoRA name,
    making it compatible with the asset uploader and other string-based inputs.
    """
    RETURN_TYPES = ("MODEL", "CLIP")
    RETURN_NAMES = ("MODEL", "CLIP")
    FUNCTION = "load_lora"
    CATEGORY = "EmProps"
    
    def __init__(self):
        self.lora_loader = LoraLoader()
    
    @classmethod
    def INPUT_TYPES(cls):
        log_debug("EmProps_Lora_Loader_Simple.INPUT_TYPES called")
        return {
            "required": {
                "model": ("MODEL", {"tooltip": "The diffusion model the LoRA will be applied to."}),
                "clip": ("CLIP", {"tooltip": "The CLIP model the LoRA will be applied to."}),
                "lora_name": ("STRING", {"multiline": False, "default": ""}),
                "strength_model": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01, 
                                           "tooltip": "How strongly to modify the diffusion model. This value can be negative."}),
                "strength_clip": ("FLOAT", {"default": 1.0, "min": -10.0, "max": 10.0, "step": 0.01,
                                          "tooltip": "How strongly to modify the CLIP model. This value can be negative."}),
            },
            "hidden": {
                "node_id": "UNIQUE_ID"
            }
        }

    def load_lora(self, model, clip, lora_name, strength_model, strength_clip, node_id=None):
        log_debug(f"EmProps_Lora_Loader_Simple.load_lora called with lora_name={lora_name}, node_id={node_id}")
        
        if not lora_name:
            log_debug("EmProps_Lora_Loader_Simple: No LoRA name provided")
            return (model, clip)
        
        # Force refresh the cache to ensure we see the latest files
        log_debug("EmProps_Lora_Loader_Simple: Refreshing LoRA cache")
        if "loras" in folder_paths.filename_list_cache:
            del folder_paths.filename_list_cache["loras"]
        
        # Get the updated file list
        lora_files = folder_paths.get_filename_list("loras")
        log_debug(f"EmProps_Lora_Loader_Simple: Available LoRAs: {lora_files}")
        
        # Check if the file exists
        max_attempts = 5
        attempt = 0
        lora_path = None
        
        while attempt < max_attempts:
            try:
                log_debug(f"EmProps_Lora_Loader_Simple: Attempt {attempt+1} to get path for {lora_name}")
                lora_path = folder_paths.get_full_path("loras", lora_name)
                if lora_path:
                    log_debug(f"EmProps_Lora_Loader_Simple: Found LoRA at {lora_path}")
                    break
            except Exception as e:
                log_debug(f"EmProps_Lora_Loader_Simple: Error getting path: {str(e)}")
                
            # If not found, wait a bit and try again (in case it's still being written)
            log_debug(f"EmProps_Lora_Loader_Simple: LoRA {lora_name} not found, waiting...")
            time.sleep(1)
            
            # Refresh the cache again
            if "loras" in folder_paths.filename_list_cache:
                del folder_paths.filename_list_cache["loras"]
            folder_paths.get_filename_list("loras")
            
            attempt += 1
        
        if not lora_path:
            log_debug(f"EmProps_Lora_Loader_Simple: LoRA {lora_name} not found after {max_attempts} attempts")
            return (model, clip)
        
        # Load the LoRA
        log_debug(f"EmProps_Lora_Loader_Simple: Loading LoRA from {lora_path}")
        try:
            # Send a progress update
            if node_id:
                PromptServer.instance.send_sync("progress", {
                    "node": node_id,
                    "value": 0,
                    "max": 100
                })
            
            # Load the LoRA using the base loader
            model_lora, clip_lora = self.lora_loader.load_lora(
                model, 
                clip, 
                os.path.basename(lora_path),
                strength_model,
                strength_clip
            )
            
            # Send completion progress
            if node_id:
                PromptServer.instance.send_sync("progress", {
                    "node": node_id,
                    "value": 100,
                    "max": 100
                })
            
            log_debug(f"EmProps_Lora_Loader_Simple: Successfully loaded LoRA {lora_name}")
            return (model_lora, clip_lora)
            
        except Exception as e:
            log_debug(f"EmProps_Lora_Loader_Simple: Error loading LoRA: {str(e)}")
            return (model, clip)

# Node class mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "EmProps_Lora_Loader_Simple": EmProps_Lora_Loader_Simple,
}

# Human-readable names for the UI
NODE_DISPLAY_NAME_MAPPINGS = {
    "EmProps_Lora_Loader_Simple": "EmProps LoRA Loader",
}
