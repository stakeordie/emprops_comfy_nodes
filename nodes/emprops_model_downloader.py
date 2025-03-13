import os
import folder_paths
import json
import requests
import boto3
import botocore
from ..utils import S3Handler
import tqdm

# Clear caches before class definition
folder_paths.cache_helper.clear()
folder_paths.filename_list_cache.clear()


class EmpropsModelDownloader:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source_type": (["url", "s3"],),
                "filename": ("STRING", {"default": "", "placeholder": "model.safetensors"}),
                # URL input
                "url": ("STRING", {
                    "default": "",
                    "placeholder": "https://example.com/model.safetensors"
                }),
                # S3 input
                "s3_bucket": ("STRING", {
                    "default": "emprops-share"
                }),
                "target_directory": ("STRING", {"default": ""})
            }
        }

    @classmethod
    def IS_CHANGED(cls, source_type, **kwargs):
        return float("NaN")  # So it always updates

    RETURN_TYPES = (folder_paths.get_filename_list("text_encoders").__class__,)
    RETURN_NAMES = ("FILENAME",)
    FUNCTION = "run"
    CATEGORY = "EmProps/Loaders"

    def run(self, source_type, filename, url, s3_bucket, target_directory=None):
        print("*********************RETURN TYPE =")
        if not target_directory:
            raise ValueError("Must specify target_directory")
            
        # Hide fields based on source type
        if source_type == "url":
            if not url:
                raise ValueError("URL is required when using URL source type")
            s3_bucket = None  # Hide s3 field
        else:  # s3
            if not filename:
                raise ValueError("Filename is required when using S3 source type")
            url = None  # Hide url field
            
        # Get the base models directory by getting any model path and going up two levels
        model_type_path = folder_paths.get_folder_paths("checkpoints")[0]  # Get first checkpoint path
        base_models_dir = os.path.dirname(os.path.dirname(model_type_path))  # Go up two levels to get base models dir
        print(f"[EmProps] Base models dir: {base_models_dir}")
        
        # Construct the output path
        output_dir = os.path.join(base_models_dir, target_directory)
        print(f"[EmProps] Output dir: {output_dir}")
        output_path = os.path.join(output_dir, filename)
        
        # Check if file exists in target directory
        if os.path.exists(output_path):
            print(f"File {filename} already exists in {output_dir}")
            return [filename]
        
        # Create directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Download based on source type
        if source_type == "s3":
            try:
                print(f"[EmProps] Preparing to download from S3 bucket: {s3_bucket}")
                # Initialize S3 handler with proper credential management
                s3_handler = S3Handler(s3_bucket)
                
                # Construct and verify the S3 key
                s3_key = f"models/{target_directory}/{filename}"
                
                # Check if the object exists before attempting download
                if not s3_handler.object_exists(s3_key):
                    # Try without models/ prefix as fallback
                    s3_key = f"{target_directory}/{filename}"
                    if not s3_handler.object_exists(s3_key):
                        raise ValueError(f"File not found in S3. Tried:\n1. s3://{s3_bucket}/models/{target_directory}/{filename}\n2. s3://{s3_bucket}/{target_directory}/{filename}")
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                print(f"[EmProps] Found file in S3, downloading to: {output_path}")
                success, error = s3_handler.download_file(s3_key, output_path)
                if not success:
                    raise ValueError(f"Download failed: {error}")
                
                if not os.path.exists(output_path):
                    raise ValueError("File was not downloaded successfully")
                    
                print(f"[EmProps] Successfully downloaded model to: {output_path}")
            except Exception as e:
                raise ValueError(f"S3 download failed: {str(e)}")
        else:  # url
            print(f"[EmProps] Downloading model from URL: {url}")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # Download with progress bar
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024
            progress_bar = tqdm.total(total_size, unit='iB', unit_scale=True)
            
            with open(output_path, 'wb') as f:
                for data in response.iter_content(block_size):
                    progress_bar.update(len(data))
                    f.write(data)
            
            progress_bar.close()
            print(f"[EmProps] Successfully downloaded model to: {output_path}")

        return [filename]
