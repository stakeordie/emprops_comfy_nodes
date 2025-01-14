import os
import requests
import sys
import time
from tqdm import tqdm
import folder_paths
from nodes import LoraLoader
from dotenv import load_dotenv
from ..utils import unescape_env_value, S3Handler

class EmProps_Lora_Loader:
    """
    EmProps LoRA loader that checks local storage first, then downloads from S3 if needed
    """
    def __init__(self):
        self.lora_loader = None
        self.s3_bucket = "emprops-share"
        self.s3_prefix = "models/loras/"

        # Load environment variables from .env.local
        current_dir = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(current_dir, '.env.local')
        load_dotenv(env_path)
        
       # Get and unescape AWS credentials from environment
        self.aws_secret_key = unescape_env_value(os.getenv('AWS_SECRET_ACCESS_KEY_ENCODED', ''))
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID', '')
        self.aws_region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')

        if not self.aws_secret_key or not self.aws_access_key:
            print("[EmProps] Warning: AWS credentials not found in .env.local")

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
        # First try to get the full path if the file exists
        local_path = folder_paths.get_full_path("loras", lora_name)
        
        # If file doesn't exist, we need to get the loras directory to save to
        if local_path is None:
            # Get the first loras directory from ComfyUI's configuration
            lora_paths = folder_paths.folder_names_and_paths["loras"][0]
            if not lora_paths:
                print("[EmProps] Error: No LoRA directory configured in ComfyUI")
                return None
                
            # Use the first configured loras directory
            local_path = os.path.join(lora_paths[0], lora_name)
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        print(f"[EmProps] LoRA will be saved to: {local_path}")
        
        # Return if file already exists
        if os.path.exists(local_path):
            print(f"[EmProps] LoRA already exists at: {local_path}")
            return local_path
                
        # Download from S3
        try:
                        # Construct S3 path
            s3_path = f"{self.s3_prefix}{lora_name}"
            print(f"[EmProps] Attempting S3 download:")
            print(f"  FROM: s3://{self.s3_bucket}/{s3_path}")
            print(f"    TO: {local_path}")
            
            # Initialize S3 client with unescaped credentials
            s3 = S3Handler(
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.aws_region
            )
            
            try:
                # First check if the object exists
                s3.head_object(Bucket=self.s3_bucket, Key=s3_path)
            except Exception as e:
                print(f"[EmProps] S3 object not found: s3://{self.s3_bucket}/{s3_path}")
                print(f"[EmProps] Error details: {str(e)}")
                return None
                
            # Get object size for progress bar
            response = s3.get_object(Bucket=self.s3_bucket, Key=s3_path)
            total_size = response['ContentLength']
            
            with tqdm(total=total_size, unit='B', unit_scale=True) as pbar:
                def callback(chunk):
                    if isinstance(chunk, (int, float)):
                        pbar.update(chunk)
                    else:
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