import os
import json
import folder_paths
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import numpy as np
from ..utils import S3Handler

class EmProps_S3_Saver:
    def __init__(self):
        self.type = "output"
        self.output_dir = folder_paths.get_output_directory()
        self.compress_level = 4

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "prefix": ("STRING", {"default": "ComfyUI"}),
                "filename": ("STRING", {"default": ""}),
                "bucket": ("STRING", {"default": "emprops-share"}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ()
    FUNCTION = "save_to_s3"
    OUTPUT_NODE = True
    CATEGORY = "image"

    def save_to_s3(self, images, prefix, filename, bucket, prompt=None, extra_pnginfo=None):
        s3_handler = S3Handler(bucket)
        
        # Get full output folder path and create if it doesn't exist
        full_output_folder = os.path.join(self.output_dir, prefix)
        os.makedirs(full_output_folder, exist_ok=True)
        
        results = []
        for i, image in enumerate(images):
            local_filename = filename if filename else f"{prefix}_{i:05}.png"
            local_filepath = os.path.join(full_output_folder, local_filename)
            
            # Convert image to PIL format
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            
            # Add metadata if enabled
            metadata = None
            if prompt is not None or extra_pnginfo is not None:
                metadata = PngInfo()
                if prompt is not None:
                    metadata.add_text("prompt", json.dumps(prompt))
                if extra_pnginfo is not None:
                    for x in extra_pnginfo:
                        metadata.add_text(x, json.dumps(extra_pnginfo[x]))
            
            # Save locally first
            img.save(local_filepath, pnginfo=metadata, compress_level=self.compress_level)
            
            # Upload to S3
            s3_key = f"{prefix}/{local_filename}"
            success, error = s3_handler.upload_file(local_filepath, s3_key)
            if not success:
                raise Exception(f"Failed to upload to S3: {error}")
            
            results.append({
                "filename": local_filename,
                "subfolder": prefix,
                "type": self.type,
                "url": f"s3://{bucket}/{s3_key}"
            })

        return {"images": results}
