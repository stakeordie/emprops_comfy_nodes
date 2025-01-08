import os
import folder_paths
from .emprops_lora_loader import EmProps_Lora_Loader
from .emprops_s3_video_combine import EmProps_S3_Video_Combine

# Import VHS package first to ensure initialization
print("[EmProps] Importing VHS package")
from .deps import VHS_VideoHelperSuite
print("[EmProps] Importing VHS nodes")
from .deps.VHS_VideoHelperSuite.videohelpersuite import nodes as vhs_nodes

print("[EmProps] Loading EmProps nodes")
print(f"[EmProps] Current directory: {os.path.dirname(os.path.abspath(__file__))}")

# Register VHS formats path
vhs_formats_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deps", "VHS_VideoHelperSuite", "video_formats")
if os.path.exists(vhs_formats_path):
    print(f"[EmProps] Found VHS formats at: {vhs_formats_path}")
    folder_paths.folder_names_and_paths["VHS_video_formats"] = ([vhs_formats_path], [".json"])
    print(f"[EmProps] Registered VHS formats in folder_paths: {folder_paths.folder_names_and_paths['VHS_video_formats']}")

# Merge VHS nodes with our nodes
NODE_CLASS_MAPPINGS = {
    "EmProps_Lora_Loader": EmProps_Lora_Loader,
    "EmProps_S3_Video_Combine": EmProps_S3_Video_Combine,
    **vhs_nodes.NODE_CLASS_MAPPINGS
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EmProps_Lora_Loader": "EmProps Lora Loader",
    "EmProps_S3_Video_Combine": "EmProps S3 Video Combine",
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']