import os
import sys
import folder_paths
from .nodes.emprops_lora_loader import EmProps_Lora_Loader
from .nodes.emprops_s3_saver import EmProps_S3_Saver
from .nodes.emprops_image_loader import EmpropsImageLoader
from .nodes.emprops_model_downloader import EmpropsModelDownloader

print("[EmProps] Starting EmProps initialization")
print(f"[EmProps] Python path: {sys.path}")
print(f"[EmProps] Current working directory: {os.getcwd()}")
print(f"[EmProps] Module directory: {os.path.dirname(os.path.abspath(__file__))}")

print("[EmProps] Loading EmProps nodes")
print(f"[EmProps] Current directory: {os.path.dirname(os.path.abspath(__file__))}")

# Debug: Print node class details
for name, cls in [(name, globals()[name]) for name in ['EmProps_Lora_Loader', 'EmProps_S3_Saver', 'EmpropsImageLoader', 'EmpropsModelDownloader']]:
    print(f"[EmProps] Node class {name}:")
    print(f"  - RETURN_TYPES: {getattr(cls, 'RETURN_TYPES', None)}")
    print(f"  - INPUT_TYPES: {getattr(cls, 'INPUT_TYPES', None)}")

NODE_CLASS_MAPPINGS = {
    "EmProps_Lora_Loader": EmProps_Lora_Loader,
    "EmProps_S3_Saver": EmProps_S3_Saver,
    "EmProps_Image_Loader": EmpropsImageLoader,
    "EmpropsModelDownloader": EmpropsModelDownloader,
}
print(f"[EmProps] Total nodes: {len(NODE_CLASS_MAPPINGS)}")

NODE_DISPLAY_NAME_MAPPINGS = {
    "EmProps_Lora_Loader": "EmProps LoRA Loader",
    "EmProps_S3_Saver": "EmProps S3 Saver",
    "EmProps_Image_Loader": "EmProps Image Loader",
    "EmpropsModelDownloader": "Emprops Model Downloader",
}
print(f"[EmProps] Display names registered: {len(NODE_DISPLAY_NAME_MAPPINGS)}")

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
