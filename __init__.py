import os
import folder_paths
from .emprops_lora_loader import EmProps_Lora_Loader
from .emprops_s3_saver import EmProps_S3_Saver
from .emprops_s3_video_combine import EmProps_S3_Video_Combine

# Register video formats directory from VideoHelperSuite
vhs_formats_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deps", "VHS_VideoHelperSuite", "video_formats")
if os.path.exists(vhs_formats_path):
    folder_paths.folder_names_and_paths["VHS_video_formats"] = ([vhs_formats_path], [".json"])

NODE_CLASS_MAPPINGS = {
    "EmProps_Lora_Loader": EmProps_Lora_Loader,
    "EmProps_S3_Saver": EmProps_S3_Saver,
    "EmProps_S3_Video_Combine": EmProps_S3_Video_Combine
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EmProps_Lora_Loader": "Load LoRA (EmProps)",
    "EmProps_S3_Saver": "Save to S3 (EmProps)",
    "EmProps_S3_Video_Combine": "Combine Videos S3 (EmProps)"
}