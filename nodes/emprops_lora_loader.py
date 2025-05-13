import os
import requests
import sys
import time
import traceback
from tqdm import tqdm
import folder_paths  # type: ignore # Custom module without stubs
from nodes import LoraLoader
from dotenv import load_dotenv
# 2025-04-27 21:05: Updated imports to support multiple cloud providers
from ..utils import unescape_env_value, S3Handler, GCSHandler, AzureHandler, GCS_AVAILABLE, AZURE_AVAILABLE
# Added: 2025-05-13T17:21:00-04:00 - Import model cache database
from ..db.model_cache import model_cache_db

# Added: 2025-05-13T17:22:00-04:00 - Debug logging function
def log_debug(message):
    """Enhanced logging function with timestamp and stack info"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    caller = traceback.extract_stack()[-2]
    file = os.path.basename(caller.filename)
    line = caller.lineno
    print(f"[EmProps DEBUG {timestamp}] [{file}:{line}] {message}", flush=True)

class EmProps_Lora_Loader:
    """
    EmProps LoRA loader that checks local storage first, then downloads from cloud storage if needed
    """
    def __init__(self):
        self.lora_loader = None
        self.cloud_prefix = "models/loras/"

        # Load environment variables from .env.local
        current_dir = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(current_dir, '.env.local')
        load_dotenv(env_path)
        
        # 2025-04-27 21:05: Get default cloud provider from environment
        self.default_provider = os.getenv('CLOUD_PROVIDER', 'aws')
        self.default_bucket = "emprops-share"
        
        # Check if test mode is enabled
        self.test_mode = os.getenv('STORAGE_TEST_MODE', 'false').lower() == 'true'
        if self.test_mode:
            self.default_bucket = "emprops-share-test"
            
        # Get and unescape AWS credentials from environment
        self.aws_secret_key = unescape_env_value(os.getenv('AWS_SECRET_ACCESS_KEY_ENCODED', ''))
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID', '')
        self.aws_region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')

        if not self.aws_secret_key or not self.aws_access_key:
            print("[EmProps] Warning: AWS credentials not found in .env.local")

    @classmethod
    def INPUT_TYPES(cls):
        # 2025-04-27 21:05: Determine available providers based on imports
        providers = ["aws"]
        if GCS_AVAILABLE:
            providers.append("google")
        if AZURE_AVAILABLE:
            providers.append("azure")
            
        # Get default provider from environment
        default_provider = os.getenv('CLOUD_PROVIDER', 'aws')
        if default_provider not in providers:
            default_provider = providers[0]
            
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "lora_name": ("STRING", {
                    "default": "", 
                    "multiline": False,
                    "tooltip": "Name of the LoRA file (e.g. my_lora.safetensors)"
                }),
                "provider": (providers, {
                    "default": default_provider,
                    "tooltip": "Cloud provider to download from if LoRA is not found locally"
                }),
                "bucket": ("STRING", {
                    "default": "emprops-share",
                    "tooltip": "Bucket/container name to download from"
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

    def download_from_cloud(self, lora_name, provider=None, bucket=None): 
        """Download LoRA from cloud storage if not found locally"""
        # 2025-04-27 21:05: Updated to support multiple cloud providers
        provider = provider or self.default_provider
        bucket = bucket or self.default_bucket
        
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
                
        # Construct cloud path
        cloud_path = f"{self.cloud_prefix}{lora_name}"
        
        try:
            # Select the appropriate cloud handler based on provider
            if provider == 'aws':
                print(f"[EmProps] Attempting AWS S3 download:")
                print(f"  FROM: s3://{bucket}/{cloud_path}")
                print(f"    TO: {local_path}")
                
                # Initialize S3 client with unescaped credentials
                handler = S3Handler(
                    bucket,
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_key,
                    region_name=self.aws_region
                )
                
                # Check if object exists
                if not handler.object_exists(cloud_path):
                    print(f"[EmProps] S3 object not found: s3://{bucket}/{cloud_path}")
                    return None
                    
            elif provider == 'google':
                print(f"[EmProps] Attempting Google Cloud Storage download:")
                print(f"  FROM: gs://{bucket}/{cloud_path}")
                print(f"    TO: {local_path}")
                
                # Initialize GCS client
                handler = GCSHandler(bucket)
                
                # Check if object exists
                if not handler.object_exists(cloud_path):
                    print(f"[EmProps] GCS object not found: gs://{bucket}/{cloud_path}")
                    return None
                    
            elif provider == 'azure':
                print(f"[EmProps] Attempting Azure Blob Storage download:")
                print(f"  FROM: {bucket}/{cloud_path}")
                print(f"    TO: {local_path}")
                
                # Initialize Azure client
                handler = AzureHandler(bucket)
                
                # Check if object exists
                if not handler.object_exists(cloud_path):
                    print(f"[EmProps] Azure blob not found: {bucket}/{cloud_path}")
                    return None
                    
            else:
                print(f"[EmProps] Error: Unsupported cloud provider: {provider}")
                return None
            
            # Download the file
            success, error = handler.download_file(cloud_path, local_path)
            if not success:
                print(f"[EmProps] Error downloading LoRA from {provider}: {error}")
                return None
                
            print(f"[EmProps] Successfully downloaded {lora_name} from {provider}")
            return local_path
            
        except Exception as e:
            print(f"[EmProps] Error downloading LoRA from {provider}: {str(e)}")
            return None

    def load_lora(self, model, clip, lora_name, provider, bucket, strength_model, strength_clip):
        """Load LoRA, downloading from cloud storage if necessary"""
        # 2025-04-27 21:05: Updated to support multiple cloud providers
        if not self.lora_loader:
            self.lora_loader = LoraLoader()
            
        try:
            # Try to download if not found locally
            lora_path = self.download_from_cloud(lora_name, provider, bucket)
            
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
            
            # Added: 2025-05-13T17:25:00-04:00 - Update model usage in cache database
            try:
                # Get the full path to the LoRA file
                lora_full_path = folder_paths.get_full_path("loras", lora_name)
                if lora_full_path:
                    model_cache_db.update_model_usage(lora_full_path)
                    log_debug(f"Updated model usage in cache database: {lora_full_path}")
            except Exception as e:
                log_debug(f"Error updating model usage in cache database: {str(e)}")
                # Non-critical error, continue with loading
            
            return (model_lora, clip_lora)
            
        except Exception as e:
            print(f"[EmProps] Error loading LoRA: {str(e)}")
            return (model, clip)