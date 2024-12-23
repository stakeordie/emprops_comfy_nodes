import os
import requests
import sys
import time
from tqdm import tqdm
import boto3
import folder_paths
from nodes import LoraLoader

def unescape_env_value(value):
    """Unescape _SLASH_ in environment variables"""
    return value.replace('_SLASH_', '/')

class EmProps_Lora_Loader:
    """
    EmProps LoRA loader that checks local storage first, then downloads from S3 if needed
    """
    def __init__(self):
        self.lora_loader = None
        self.s3_bucket = "edenartlab-lfs"
        self.s3_prefix = "comfyui/models2/loras/"
        
        # Get and unescape AWS credentials from environment
        self.aws_secret_key = unescape_env_value(os.getenv('AWS_SECRET_ACCESS_KEY_ENCODED', ''))
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID', '')
        self.aws_region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "lora_name": ("STRING", {
                    "default": "", 
                    "multiline": False,
                    "tooltip": "Name of the LoRA file (e.g. my_lora.safetensors)"
                }),
                "strength_model": ("FLOAT", {
                    "default": 1.0, 
                    "min": -10.0, 
                    "max": 10.0, 
                    "step": 0.01,
                    "tooltip": "Weight of the LoRA for the model"
                }),
                "strength_clip": ("FLOAT", {
                    "default": 1.0, 
                    "min": -10.0, 
                    "max": 10.0, 
                    "step": 0.01,
                    "tooltip": "Weight of the LoRA for CLIP"
                }),
            }
        }

    RETURN_TYPES = ("MODEL", "CLIP")
    FUNCTION = "load_lora"
    CATEGORY = "loaders/emprops"

    def download_from_s3(self, lora_name):
        """Download LoRA from S3 if not found locally"""
        local_path = folder_paths.get_full_path("loras", lora_name)
        
        # Return if file exists locally
        if local_path is not None:
            return local_path
            
        # Get the first loras directory path
        lora_path = folder_paths.folder_names_and_paths["loras"][0][0]
        local_path = os.path.join(lora_path, lora_name)
        
        # Download from S3
        try:
            print(f"[EmProps] Downloading LoRA {lora_name} from S3...")
            
            # Initialize S3 client with unescaped credentials
            s3 = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.aws_region
            )
            
            # Download with progress bar
            s3_path = f"{self.s3_prefix}{lora_name}"
            response = s3.get_object(Bucket=self.s3_bucket, Key=s3_path)
            total_size = response['ContentLength']
            
            with tqdm(total=total_size, unit='B', unit_scale=True) as pbar:
                def callback(chunk):
                    pbar.update(len(chunk))
                
                s3.download_file(
                    self.s3_bucket,
                    s3_path,
                    local_path,
                    Callback=callback
                )
                
            print(f"[EmProps] Successfully downloaded {lora_name}")
            return local_path
            
        except Exception as e:
            print(f"[EmProps] Error downloading LoRA from S3: {str(e)}")
            return None

    def load_lora(self, model, clip, lora_name, strength_model, strength_clip):
        """Load LoRA, downloading from S3 if necessary"""
        if not self.lora_loader:
            self.lora_loader = LoraLoader()
            
        try:
            # Try to download if not found locally
            lora_path = self.download_from_s3(lora_name)
            
            if lora_path is None:
                print(f"[EmProps] Could not find or download LoRA: {lora_name}")
                return (model, clip)
                
            # Load the LoRA using the base loader
            print(f"[EmProps] Loading LoRA: {lora_name}")
            model_lora, clip_lora = self.lora_loader.load_lora(
                model, 
                clip, 
                lora_name,
                strength_model,
                strength_clip
            )
            
            return (model_lora, clip_lora)
            
        except Exception as e:
            print(f"[EmProps] Error loading LoRA: {str(e)}")
            return (model, clip)