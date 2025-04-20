import os
import sys
import folder_paths
from .nodes.emprops_lora_loader import EmProps_Lora_Loader
from .nodes.emprops_cloud_storage_saver import EmpropsCloudStorageSaver
from .nodes.emprops_image_loader import EmpropsImageLoader
from .nodes.emprops_model_downloader import EmpropsModelDownloader
from .nodes.emprops_model_downloader_checkpoint import EmpropsModelDownloaderCheckpoint
from .nodes.emprops_model_downloader_clip import EmpropsModelDownloaderClip
from .nodes.emprops_model_downloader_clip_vision import EmpropsModelDownloaderClipVision
from .nodes.emprops_text_s3_saver import EmProps_Text_S3_Saver

print("[EmProps] Starting EmProps initialization")
print(f"[EmProps] Python path: {sys.path}")
print(f"[EmProps] Current working directory: {os.getcwd()}")
print(f"[EmProps] Module directory: {os.path.dirname(os.path.abspath(__file__))}")

print("[EmProps] Loading EmProps nodes")
print(f"[EmProps] Current directory: {os.path.dirname(os.path.abspath(__file__))}")

# Debug: Print node class details
# Updated: 2025-04-20T19:41:30-04:00 - Updated to use new class name
for name, cls in [(name, globals()[name]) for name in ['EmProps_Lora_Loader', 'EmpropsCloudStorageSaver', 'EmpropsImageLoader', 'EmpropsModelDownloader']]:
    print(f"[EmProps] Node class {name}:")
    print(f"  - RETURN_TYPES: {getattr(cls, 'RETURN_TYPES', None)}")
    print(f"  - INPUT_TYPES: {getattr(cls, 'INPUT_TYPES', None)}")

# Updated: 2025-04-20T19:41:30-04:00 - Added backward compatibility for old node name
NODE_CLASS_MAPPINGS = {
    "EmProps_Lora_Loader": EmProps_Lora_Loader,
    "EmProps_Cloud_Storage_Saver": EmpropsCloudStorageSaver,
    "EmProps_S3_Saver": EmpropsCloudStorageSaver,  # Backward compatibility
    "EmProps_Image_Loader": EmpropsImageLoader,
    "EmpropsModelDownloader": EmpropsModelDownloader,
    "EmpropsModelDownloaderCheckpoint": EmpropsModelDownloaderCheckpoint,
    "EmpropsModelDownloaderClip": EmpropsModelDownloaderClip,
    "EmpropsModelDownloaderClipVision": EmpropsModelDownloaderClipVision,
    "EmProps_Text_S3_Saver": EmProps_Text_S3_Saver,
}
print(f"[EmProps] Total nodes: {len(NODE_CLASS_MAPPINGS)}")

NODE_DISPLAY_NAME_MAPPINGS = {
    "EmProps_Lora_Loader": "EmProps LoRA Loader",
    "EmProps_Cloud_Storage_Saver": "EmProps Cloud Storage Saver",
    "EmProps_S3_Saver": "EmProps S3 Saver (Legacy)",  # Backward compatibility
    "EmProps_Image_Loader": "EmProps Image Loader",
    "EmpropsModelDownloader": "Emprops Model Downloader",
    "EmpropsModelDownloaderCheckpoint": "Emprops Checkpoint Downloader",
    "EmpropsModelDownloaderClip": "Emprops Clip Downloader",
    "EmpropsModelDownloaderClipVision": "Emprops ClipVision Downloader",
    "EmProps_Text_S3_Saver": "EmProps Text S3 Saver",
}
print(f"[EmProps] Display names registered: {len(NODE_DISPLAY_NAME_MAPPINGS)}")

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
