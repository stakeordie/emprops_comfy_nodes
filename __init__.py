import os
import sys
import folder_paths
from .emprops_lora_loader import EmProps_Lora_Loader
from .emprops_s3_saver import EmProps_S3_Saver

print("[EmProps] Starting EmProps initialization")
print(f"[EmProps] Python path: {sys.path}")
print(f"[EmProps] Current working directory: {os.getcwd()}")
print(f"[EmProps] Module directory: {os.path.dirname(os.path.abspath(__file__))}")

print("[EmProps] Loading EmProps nodes")
print(f"[EmProps] Current directory: {os.path.dirname(os.path.abspath(__file__))}")

NODE_CLASS_MAPPINGS = {
    "EmProps_Lora_Loader": EmProps_Lora_Loader,
    "EmProps_S3_Saver": EmProps_S3_Saver,
}
print(f"[EmProps] Total nodes: {len(NODE_CLASS_MAPPINGS)}")

NODE_DISPLAY_NAME_MAPPINGS = {
    "EmProps_Lora_Loader": "EmProps Lora Loader",
    "EmProps_S3_Saver": "Save to S3 (EmProps)",
}
print(f"[EmProps] Display names registered: {len(NODE_DISPLAY_NAME_MAPPINGS)}")

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']