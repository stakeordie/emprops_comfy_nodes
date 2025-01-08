import os
import sys
import folder_paths
from .emprops_lora_loader import EmProps_Lora_Loader
from .emprops_s3_video_combine import EmProps_S3_Video_Combine

print("[EmProps] Starting EmProps initialization")
print(f"[EmProps] Python path: {sys.path}")
print(f"[EmProps] Current working directory: {os.getcwd()}")
print(f"[EmProps] Module directory: {os.path.dirname(os.path.abspath(__file__))}")

# Import VHS package first to ensure initialization
print("[EmProps] Importing VHS package")
print(f"[EmProps] VHS package location: {os.path.abspath(os.path.join(os.path.dirname(__file__), 'deps', 'VHS_VideoHelperSuite'))}")
from .deps import VHS_VideoHelperSuite
print("[EmProps] Importing VHS nodes")
from .deps.VHS_VideoHelperSuite.videohelpersuite import nodes as vhs_nodes
print(f"[EmProps] VHS nodes imported. Available nodes: {len(vhs_nodes.NODE_CLASS_MAPPINGS)}")

print("[EmProps] Loading EmProps nodes")
print(f"[EmProps] Current directory: {os.path.dirname(os.path.abspath(__file__))}")

# Register VHS formats path
vhs_formats_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deps", "VHS_VideoHelperSuite", "video_formats")
if os.path.exists(vhs_formats_path):
    print(f"[EmProps] Found VHS formats at: {vhs_formats_path}")
    folder_paths.folder_names_and_paths["VHS_video_formats"] = ([vhs_formats_path], [".json"])
    print(f"[EmProps] Registered VHS formats in folder_paths: {folder_paths.folder_names_and_paths['VHS_video_formats']}")

# Merge VHS nodes with our nodes
print("[EmProps] Starting node merge")
print(f"[EmProps] VHS nodes count before merge: {len(vhs_nodes.NODE_CLASS_MAPPINGS)}")
NODE_CLASS_MAPPINGS = {
    "EmProps_Lora_Loader": EmProps_Lora_Loader,
    "EmProps_S3_Video_Combine": EmProps_S3_Video_Combine,
    **vhs_nodes.NODE_CLASS_MAPPINGS
}
print(f"[EmProps] Total nodes after merge: {len(NODE_CLASS_MAPPINGS)}")

NODE_DISPLAY_NAME_MAPPINGS = {
    "EmProps_Lora_Loader": "EmProps Lora Loader",
    "EmProps_S3_Video_Combine": "EmProps S3 Video Combine",
    **vhs_nodes.NODE_DISPLAY_NAME_MAPPINGS
}
print(f"[EmProps] Display names registered: {len(NODE_DISPLAY_NAME_MAPPINGS)}")

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']