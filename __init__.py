from .emprops_lora_loader import EmProps_Lora_Loader
from .emprops_s3_saver import EmProps_S3_Saver

NODE_CLASS_MAPPINGS = {
    "EmProps_Lora_Loader": EmProps_Lora_Loader,
    "EmProps_S3_Saver": EmProps_S3_Saver
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EmProps_Lora_Loader": "Load LoRA (EmProps)",
    "EmProps_S3_Saver": "Save to S3 (EmProps)"
}