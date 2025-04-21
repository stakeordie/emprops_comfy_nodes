import os
import folder_paths  # type: ignore # Custom module without stubs
import json
import requests  # type: ignore # Will be fixed with types-requests
import boto3  # type: ignore # Will be fixed with types-boto3
import botocore  # type: ignore # Will be fixed with types-boto3
# Added: 2025-04-13T21:35:00-04:00 - Azure Blob Storage support
from ..utils import S3Handler, GCSHandler, GCS_AVAILABLE, AzureHandler, AZURE_AVAILABLE
import tqdm  # type: ignore # Will be fixed with types-tqdm

# Clear caches before class definition
folder_paths.cache_helper.clear()
folder_paths.filename_list_cache.clear()

# Helper function to debug filename lists
def debug_filename_lists():
    """Debug helper to check available filename lists and their types"""
    print("\n[EmProps] DEBUG FILENAME LISTS:")
    # Check different model types
    model_types = ["checkpoints", "text_encoders", "loras", "vae"]
    
    for model_type in model_types:
        try:
            filenames = folder_paths.get_filename_list(model_type)
            print(f"[EmProps] {model_type} filenames type: {type(filenames)}")
            print(f"[EmProps] {model_type} filenames class: {filenames.__class__}")
            print(f"[EmProps] {model_type} first few items: {filenames[:3] if len(filenames) > 0 else []}")
            
            # Check if it's a custom type with special methods
            if hasattr(filenames, "__iter__") and not isinstance(filenames, list):
                print(f"[EmProps] {model_type} has custom __iter__ method")
                
            if hasattr(filenames, "__getitem__") and not isinstance(filenames, list):
                print(f"[EmProps] {model_type} has custom __getitem__ method")
        except Exception as e:
            print(f"[EmProps] Error checking {model_type}: {str(e)}")
    print("\n")

# Run the debug function at module load time
debug_filename_lists()


class EmpropsModelDownloader:
    @classmethod
    def INPUT_TYPES(cls):
        # Determine available source types based on imports
        source_types = ["url", "s3"]
        if GCS_AVAILABLE:
            source_types.append("gcs")
        # Added: 2025-04-13T21:36:00-04:00 - Azure Blob Storage support
        if AZURE_AVAILABLE:
            source_types.append("azure")
        
        # Log INPUT_TYPES for debugging
        input_types = {
            "required": {
                "source_type": (source_types,),
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
                # GCS input
                "gcs_bucket": ("STRING", {
                    "default": "emprops-share"
                }),
                # Azure input
                "azure_container": ("STRING", {
                    "default": os.getenv('AZURE_STORAGE_CONTAINER', 'test')
                }),
                "target_directory": ("STRING", {"default": ""})
            }
        }
        
        print(f"[EmProps] INPUT_TYPES return value: {input_types}")
        print(f"[EmProps] INPUT_TYPES source_type type: {type(input_types['required']['source_type'])}")
        return input_types

    @classmethod
    def IS_CHANGED(cls, source_type, **kwargs):
        return float("NaN")  # So it always updates

    # Added: 2025-04-20T21:47:57-04:00 - Fixed return types to use string type instead of dynamic class
    # This must be a string type, not a function call or object
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("FILENAME",)
    FUNCTION = "run"
    CATEGORY = "EmProps/Loaders"
    
    # Added: 2025-04-20T21:52:16-04:00 - Updated debugging logs
    print(f"[EmProps MODEL_DOWNLOADER] RETURN_TYPES: {RETURN_TYPES}")
    print(f"[EmProps MODEL_DOWNLOADER] Example return value type: {type(folder_paths.get_filename_list('text_encoders'))}")
    print(f"[EmProps MODEL_DOWNLOADER] Example return value count: {len(folder_paths.get_filename_list('text_encoders'))}")

    # Updated: 2025-04-13T21:40:00-04:00 - Added Azure Blob Storage support
    def run(self, source_type, filename, url, s3_bucket, gcs_bucket=None, azure_container=None, target_directory=None):
        print("*********************RETURN TYPE DEBUGGING*********************")
        print(f"[EmProps] Expected return type: {self.RETURN_TYPES}")
        if not target_directory:
            raise ValueError("Must specify target_directory")
            
        # Hide fields based on source type
        # Updated: 2025-04-13T21:42:00-04:00 - Added Azure Blob Storage support
        if source_type == "url":
            if not url:
                raise ValueError("URL is required when using URL source type")
            s3_bucket = None  # Hide s3 field
            gcs_bucket = None  # Hide gcs field
            azure_container = None  # Hide azure field
        elif source_type == "s3":
            if not filename:
                raise ValueError("Filename is required when using S3 source type")
            url = None  # Hide url field
            gcs_bucket = None  # Hide gcs field
            azure_container = None  # Hide azure field
        elif source_type == "gcs":
            if not filename:
                raise ValueError("Filename is required when using GCS source type")
            url = None  # Hide url field
            s3_bucket = None  # Hide s3 field
            azure_container = None  # Hide azure field
        elif source_type == "azure":
            if not filename:
                raise ValueError("Filename is required when using Azure source type")
            url = None  # Hide url field
            s3_bucket = None  # Hide s3 field
            gcs_bucket = None  # Hide gcs field
            
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
            
            # Added: 2025-04-20T21:47:57-04:00 - Return as tuple for consistency
            print(f"[EmProps MODEL_DOWNLOADER] Returning existing filename: {filename}")
            # Return as a tuple to match RETURN_TYPES = ("STRING",)
            return (filename,)
        
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
        elif source_type == "gcs":
            try:
                if not GCS_AVAILABLE:
                    raise ValueError("Google Cloud Storage is not available. Install with 'pip install google-cloud-storage'")
                    
                print(f"[EmProps] Preparing to download from GCS bucket: {gcs_bucket}")
                # Initialize GCS handler with proper credential management
                gcs_handler = GCSHandler(gcs_bucket)
                
                # Construct and verify the GCS key
                gcs_key = f"models/{target_directory}/{filename}"
                
                # Check if the object exists before attempting download
                if not gcs_handler.object_exists(gcs_key):
                    # Try without models/ prefix as fallback
                    gcs_key = f"{target_directory}/{filename}"
                    if not gcs_handler.object_exists(gcs_key):
                        raise ValueError(f"File not found in GCS. Tried:\n1. gs://{gcs_bucket}/models/{target_directory}/{filename}\n2. gs://{gcs_bucket}/{target_directory}/{filename}")
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                print(f"[EmProps] Found file in GCS, downloading to: {output_path}")
                success, error = gcs_handler.download_file(gcs_key, output_path)
                if not success:
                    raise ValueError(f"Download failed: {error}")
                
                if not os.path.exists(output_path):
                    raise ValueError("File was not downloaded successfully")
                    
                print(f"[EmProps] Successfully downloaded model to: {output_path}")
            except Exception as e:
                raise ValueError(f"GCS download failed: {str(e)}")
        # Added: 2025-04-13T21:45:00-04:00 - Azure Blob Storage download implementation
        elif source_type == "azure":
            try:
                if not AZURE_AVAILABLE:
                    raise ValueError("Azure Blob Storage is not available. Install with 'pip install azure-storage-blob'")
                    
                print(f"[EmProps] Preparing to download from Azure container: {azure_container}")
                # Initialize Azure handler with proper credential management
                azure_handler = AzureHandler(azure_container)
                
                # Construct and verify the Azure blob name
                azure_blob = f"models/{target_directory}/{filename}"
                
                # Check if the blob exists before attempting download
                if not azure_handler.object_exists(azure_blob):
                    # Try without models/ prefix as fallback
                    azure_blob = f"{target_directory}/{filename}"
                    if not azure_handler.object_exists(azure_blob):
                        raise ValueError(f"File not found in Azure. Tried:\n1. {azure_container}/models/{target_directory}/{filename}\n2. {azure_container}/{target_directory}/{filename}")
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                print(f"[EmProps] Found file in Azure, downloading to: {output_path}")
                success, error = azure_handler.download_file(azure_blob, output_path)
                if not success:
                    raise ValueError(f"Download failed: {error}")
                
                if not os.path.exists(output_path):
                    raise ValueError("File was not downloaded successfully")
                    
                print(f"[EmProps] Successfully downloaded model to: {output_path}")
            except Exception as e:
                raise ValueError(f"Azure download failed: {str(e)}")
        else:  # url
            print(f"[EmProps] Downloading model from URL: {url}")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # Download with progress bar
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024
            progress_bar = tqdm.tqdm(total=total_size, unit='iB', unit_scale=True)
            
            with open(output_path, 'wb') as f:
                for data in response.iter_content(block_size):
                    progress_bar.update(len(data))
                    f.write(data)
            
            progress_bar.close()
            print(f"[EmProps] Successfully downloaded model to: {output_path}")

        # Added: 2025-04-20T21:47:57-04:00 - Return as tuple for consistency
        print(f"[EmProps MODEL_DOWNLOADER] Returning downloaded filename: {filename}")
        # Return as a tuple to match RETURN_TYPES = ("STRING",)
        return (filename,)

{{ ... }}
