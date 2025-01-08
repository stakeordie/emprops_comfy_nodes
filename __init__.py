import os
import folder_paths
from .emprops_lora_loader import EmProps_Lora_Loader
from .emprops_s3_saver import EmProps_S3_Saver
from .emprops_s3_video_combine import EmProps_S3_Video_Combine

# Register video formats directory from VideoHelperSuite
vhs_path = os.path.join(os.path.dirname(__file__), 'deps', 'VHS_VideoHelperSuite')
video_formats_path = os.path.join(vhs_path, 'video_formats')
if os.path.exists(video_formats_path):
    folder_paths.add_model_folder_path("VHS_video_formats", video_formats_path)

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