import os
import sys
import boto3  # type: ignore # Will be fixed with types-boto3
import folder_paths  # type: ignore # Custom module without stubs
import traceback
import time
import json
import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from dotenv import load_dotenv
from typing import Optional, Tuple, List, Dict, Any
from ..utils import unescape_env_value, S3Handler, GCSHandler, AzureHandler, GCS_AVAILABLE, AZURE_AVAILABLE
from .helpers.image_save_helper import ImageSaveHelper

# Added: 2025-04-20T19:47:26-04:00 - Enhanced logging for debugging
def log_debug(message):
    """Enhanced logging function with timestamp and stack info"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    caller = traceback.extract_stack()[-2]
    file = os.path.basename(caller.filename)
    line = caller.lineno
    print(f"[EmProps CLOUD_STORAGE_SAVER {timestamp}] [{file}:{line}] {message}", flush=True)

# Added: 2025-04-20T19:21:11-04:00 - Updated to support multiple cloud providers

class EmpropsCloudStorageSaver:
    """
    Node for saving files to cloud storage (AWS S3, Google Cloud Storage, or Azure Blob Storage) with dynamic prefix support
    """
    # Updated: 2025-04-20T19:47:26-04:00 - Added enhanced logging
    def __init__(self):
        log_debug("Initializing EmpropsCloudStorageSaver class")
        try:
            # Initialize common properties
            log_debug("Setting up common properties")
            self.default_bucket = "emprops-share"
            self.image_helper = ImageSaveHelper()
            self.type = "output"  # Use "output" for proper ComfyUI preview display
            self.output_dir = folder_paths.get_output_directory()
            self.compress_level = 4
            log_debug(f"Output directory: {self.output_dir}")
        
            # Check if Google Cloud Storage is available
            log_debug(f"Checking GCS availability: {GCS_AVAILABLE}")
            self.gcs_available = GCS_AVAILABLE
            if self.gcs_available:
                log_debug("Google Cloud Storage support is available")
            else:
                log_debug("Google Cloud Storage support is not available. Install with 'pip install google-cloud-storage'")
            
            # Check if Azure Blob Storage is available
            log_debug(f"Checking Azure availability: {AZURE_AVAILABLE}")
            self.azure_available = AZURE_AVAILABLE
            if self.azure_available:
                log_debug("Azure Blob Storage support is available")
            else:
                log_debug("Azure Blob Storage support is not available. Install with 'pip install azure-storage-blob'")
        
            # First try system environment for AWS credentials
            log_debug("Loading AWS credentials from environment")
            self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
            self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            self.aws_region = os.getenv('AWS_DEFAULT_REGION')
            log_debug(f"AWS credentials from env: Access Key: {'Found' if self.aws_access_key else 'Not found'}, Secret Key: {'Found' if self.aws_secret_key else 'Not found'}, Region: {self.aws_region or 'Not found'}")

            # If not found, try .env and .env.local files
            if not self.aws_access_key or not self.aws_secret_key:
                current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go up one level to project root
                log_debug(f"Looking for .env files in: {current_dir}")
                
                # Try .env first
                env_path = os.path.join(current_dir, '.env')
                if os.path.exists(env_path):
                    log_debug(f"Loading .env from: {env_path}")
                    load_dotenv(env_path)
                    self.aws_secret_key = self.aws_secret_key or unescape_env_value(os.getenv('AWS_SECRET_ACCESS_KEY_ENCODED', ''))
                    if not self.aws_secret_key:
                        self.aws_secret_key = self.aws_secret_key or os.getenv('AWS_SECRET_ACCESS_KEY', '')
                        log_debug("AWS_SECRET_ACCESS_KEY_ENCODED not found in .env, trying AWS_SECRET_ACCESS_KEY")
                    self.aws_access_key = self.aws_access_key or os.getenv('AWS_ACCESS_KEY_ID', '')
                    self.aws_region = self.aws_region or os.getenv('AWS_DEFAULT_REGION', '')
                
                # If still not found, try .env.local
                if not self.aws_access_key or not self.aws_secret_key:
                    env_local_path = os.path.join(current_dir, '.env.local')
                    if os.path.exists(env_local_path):
                        log_debug(f"Loading .env.local from: {env_local_path}")
                        load_dotenv(env_local_path)
                        self.aws_secret_key = self.aws_secret_key or unescape_env_value(os.getenv('AWS_SECRET_ACCESS_KEY_ENCODED', ''))
                        if not self.aws_secret_key:
                            self.aws_secret_key = self.aws_secret_key or os.getenv('AWS_SECRET_ACCESS_KEY', '')
                            log_debug("AWS_SECRET_ACCESS_KEY_ENCODED not found in .env.local, trying AWS_SECRET_ACCESS_KEY")
                        self.aws_access_key = self.aws_access_key or os.getenv('AWS_ACCESS_KEY_ID', '')
                        self.aws_region = self.aws_region or os.getenv('AWS_DEFAULT_REGION', '')
        
            # Set default region if still not set
            self.aws_region = self.aws_region or 'us-east-1'
            log_debug(f"Final AWS region: {self.aws_region}")

            if not self.aws_secret_key or not self.aws_access_key:
                log_debug("Warning: AWS credentials not found in environment or .env.local")
            
            # Check for Google Cloud credentials
            log_debug("Checking Google Cloud credentials")
            self.gcs_credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            log_debug(f"GCS credentials path: {self.gcs_credentials_path or 'Not found'}")
            if not self.gcs_credentials_path and self.gcs_available:
                log_debug("Warning: GOOGLE_APPLICATION_CREDENTIALS not found in environment")
            
            # Check for Azure credentials
            log_debug("Checking Azure credentials")
            # Support for provider-agnostic environment variables
            # Added: 2025-05-07T14:30:00-04:00 - Provider-agnostic environment variables
            self.azure_account_name = os.getenv('STORAGE_ACCOUNT_NAME', os.getenv('AZURE_STORAGE_ACCOUNT'))
            self.azure_account_key = os.getenv('STORAGE_ACCOUNT_KEY', os.getenv('AZURE_STORAGE_KEY'))
            self.azure_container = os.getenv('STORAGE_CONTAINER', os.getenv('AZURE_STORAGE_CONTAINER', 'test'))
            
            # Check for test mode using provider-agnostic variable
            storage_test_mode = os.getenv('STORAGE_TEST_MODE', os.getenv('AZURE_TEST_MODE', 'false')).lower() == 'true'
            if storage_test_mode:
                self.azure_container = f"{self.azure_container}-test"
                log_debug(f"Using test container for Azure: {self.azure_container}")
                
            log_debug(f"Azure credentials: Account: {'Found' if self.azure_account_name else 'Not found'}, Key: {'Found' if self.azure_account_key else 'Not found'}, Container: {self.azure_container}")
            if (not self.azure_account_name or not self.azure_account_key) and self.azure_available:
                log_debug("Warning: Azure credentials not found in environment. Set STORAGE_ACCOUNT_NAME/STORAGE_ACCOUNT_KEY or AZURE_STORAGE_ACCOUNT/AZURE_STORAGE_KEY")
                
            # Check for CLOUD_PROVIDER environment variable
            # Added: 2025-05-07T14:39:30-04:00 - Support for CLOUD_PROVIDER environment variable
            self.default_provider = os.getenv('CLOUD_PROVIDER', 'aws').lower()
            if self.default_provider not in ['aws', 'azure', 'google']:
                log_debug(f"Warning: Unknown CLOUD_PROVIDER value: {self.default_provider}, defaulting to 'aws'")
                self.default_provider = 'aws'
            log_debug(f"Default cloud provider from environment: {self.default_provider}")
            
            # Added: 2025-06-29 - Use CLOUD_STORAGE_CONTAINER for CDN check
            self.production_cdn_container = os.getenv('CLOUD_STORAGE_CONTAINER', 'emprops-production')
            log_debug(f"Production CDN container: {self.production_cdn_container}")
            
            log_debug("EmpropsCloudStorageSaver initialization completed successfully")
        except Exception as e:
            log_debug(f"ERROR in EmpropsCloudStorageSaver.__init__: {str(e)}\n{traceback.format_exc()}")
            raise

    @classmethod
    def INPUT_TYPES(cls):
        log_debug("EmpropsCloudStorageSaver.INPUT_TYPES called")
        try:
            # Determine available providers based on imports
            providers = ["aws"]
            log_debug(f"GCS_AVAILABLE: {GCS_AVAILABLE}, AZURE_AVAILABLE: {AZURE_AVAILABLE}")
            if GCS_AVAILABLE:
                providers.append("google")
                log_debug("Added 'google' to providers list")
            if AZURE_AVAILABLE:
                providers.append("azure")
                log_debug("Added 'azure' to providers list")
            
            log_debug(f"Final providers list: {providers}")
            result = {
                "required": {
                    "images": ("IMAGE",),
                    "provider": (providers,),
                    "prefix": ("STRING", {"default": "uploads/"}),
                    "filename": ("STRING", {"default": "image.png"}),
                    "bucket": ("STRING", {"default": "emprops-share"})
                },
                "hidden": {
                    "prompt": "PROMPT",
                    "extra_pnginfo": "EXTRA_PNGINFO"
                }
            }
            log_debug(f"Returning INPUT_TYPES result: {result}")
            return result
        except Exception as e:
            log_debug(f"ERROR in INPUT_TYPES: {str(e)}\n{traceback.format_exc()}")
            # Provide a fallback in case of error
            return {
                "required": {
                    "images": ("IMAGE",),
                    "provider": (["aws"],),
                    "prefix": ("STRING", {"default": "uploads/"}),
                    "filename": ("STRING", {"default": "image.png"}),
                    "bucket": ("STRING", {"default": "emprops-share"})
                },
                "hidden": {
                    "prompt": "PROMPT",
                    "extra_pnginfo": "EXTRA_PNGINFO"
                }
            }

    RETURN_TYPES = ()  
    FUNCTION = "save_to_cloud"
    CATEGORY = "EmProps"
    OUTPUT_NODE = True
    DESCRIPTION = "Saves the input images to cloud storage (AWS S3, Google Cloud Storage, or Azure Blob Storage) with configurable bucket and prefix and displays them in the UI."

    # Added: 2025-05-07T14:55:00-04:00 - Added missing save_to_cloud method
    def save_to_cloud(self, images, provider=None, prefix="uploads/", filename="image.png", bucket="emprops-share", prompt=None, extra_pnginfo=None):
        """Save images to cloud storage (AWS S3, Google Cloud Storage, or Azure Blob Storage) with the specified prefix and filename"""
        # Use default provider from environment if not specified
        if provider is None:
            provider = getattr(self, 'default_provider', 'aws')
            log_debug(f"Using default provider from environment: {provider}")
            
        # Log the provider for debugging
        log_debug(f"save_to_cloud called with provider: {provider}, bucket: {bucket}, prefix: {prefix}, filename: {filename}")
        log_debug(f"Images type: {type(images)}, shape: {images.shape if hasattr(images, 'shape') else 'unknown'}")
        log_debug(f"Prompt: {'Present' if prompt else 'None'}, extra_pnginfo: {'Present' if extra_pnginfo else 'None'}")
        
        # First save locally for preview (like standard SaveImage node)
        try:
            import folder_paths
            log_debug(f"Starting local save for preview - filename: {filename}")
            
            filename_prefix_clean = filename.replace(".png", "").replace(".jpg", "").replace(".jpeg", "").replace(".webp", "")
            log_debug(f"Using filename prefix: {filename_prefix_clean}")
            
            full_output_folder, local_filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(
                filename_prefix_clean, 
                self.output_dir, 
                images[0].shape[1], 
                images[0].shape[0]
            )
            log_debug(f"Local save path info - folder: {full_output_folder}, filename: {local_filename}, counter: {counter}, subfolder: {subfolder}")
            
            local_results = []
            for (batch_number, image) in enumerate(images):
                log_debug(f"Processing image {batch_number} for local save")
                i = 255. * image.cpu().numpy()
                img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
                metadata = None
                if prompt is not None or extra_pnginfo is not None:
                    metadata = PngInfo()
                    if prompt is not None:
                        metadata.add_text("prompt", json.dumps(prompt))
                    if extra_pnginfo is not None:
                        for x in extra_pnginfo:
                            metadata.add_text(x, json.dumps(extra_pnginfo[x]))

                local_filename_with_batch = local_filename.replace("%batch_num%", str(batch_number))
                local_file = f"{local_filename_with_batch}_{counter:05}_.png"
                local_full_path = os.path.join(full_output_folder, local_file)
                
                log_debug(f"Saving local file: {local_full_path}")
                img.save(local_full_path, pnginfo=metadata, compress_level=self.compress_level)
                log_debug(f"Successfully saved local file: {local_file}")
                
                local_results.append({
                    "filename": local_file,
                    "subfolder": subfolder,
                    "type": self.type
                })
                counter += 1
            
            log_debug(f"Local results for UI: {local_results}")
            
        except Exception as local_save_error:
            log_debug(f"ERROR in local save: {str(local_save_error)}\n{traceback.format_exc()}")
            print(f"[EmProps] ERROR saving locally: {str(local_save_error)}", flush=True)
            # Create empty local_results as fallback
            local_results = []
        
        try:
            # Initialize the appropriate cloud storage client based on provider
            if provider == "aws":
                # Debug: Print AWS credentials being used (first 4 chars only)
                if self.aws_access_key:
                    print(f"[EmProps] Debug - Using AWS Access Key ID: {self.aws_access_key[:4]}...")
                if self.aws_secret_key:
                    print(f"[EmProps] Debug - Using AWS Secret Key: {self.aws_secret_key[:4]}...")
                print(f"[EmProps] Debug - Using AWS Region: {self.aws_region}")

                # Initialize S3 client with explicit credentials
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_key,
                    region_name=self.aws_region
                )
                
                # Create S3Handler for verification
                s3_handler = S3Handler(bucket)
            elif provider == "google":
                if not self.gcs_available:
                    raise ValueError("Google Cloud Storage is not available. Install with 'pip install google-cloud-storage'")
                    
                # Debug: Print GCS credentials being used
                if self.gcs_credentials_path:
                    print(f"[EmProps] Debug - Using GCS credentials from: {self.gcs_credentials_path}")
                else:
                    print("[EmProps] Debug - Using default GCS credentials")
                    
                # Initialize GCS handler
                gcs_handler = GCSHandler(bucket)
                
                # Check if GCS client is initialized
                if not gcs_handler.gcs_client:
                    raise ValueError("Failed to initialize Google Cloud Storage client. Check your credentials.")
            elif provider == "azure":
                if not self.azure_available:
                    raise ValueError("Azure Blob Storage is not available. Install with 'pip install azure-storage-blob'")
                
                # Debug: Print Azure credentials being used
                if self.azure_account_name:
                    print(f"[EmProps] Debug - Using Azure Account Name: {self.azure_account_name}")
                if self.azure_account_key:
                    print(f"[EmProps] Debug - Using Azure Account Key: {self.azure_account_key[:4]}...")
                print(f"[EmProps] Debug - Using Azure Container: {self.azure_container}")
                
                # Initialize Azure handler
                log_debug(f"Initializing Azure handler with container: {bucket}")
                azure_handler = AzureHandler(bucket)
                
                # Check if Azure client is initialized
                if not azure_handler.blob_service_client or not azure_handler.container_client:
                    raise ValueError("Failed to initialize Azure Blob Storage client. Check your credentials.")
            else:
                raise ValueError(f"Unsupported provider: {provider}")
            
            # Ensure prefix ends with '/'
            if not prefix.endswith('/'):
                prefix += '/'
            
            # Determine format based on filename extension
            ext = os.path.splitext(filename)[1].lower()
            if ext == '.jpg' or ext == '.jpeg':
                format_info = ('JPEG', 'image/jpeg')
            elif ext == '.webp':
                format_info = ('WEBP', 'image/webp')
            else:  # Default to PNG
                format_info = ('PNG', 'image/png')
            
            # Process images and get bytes
            processed = self.image_helper.process_images(
                images, 
                prompt=prompt, 
                extra_pnginfo=extra_pnginfo,
                format=format_info[0],
                mime_type=format_info[1]
            )
            
            saved = []
            for idx, (image_bytes, metadata, mime_type) in enumerate(processed):
                # Generate unique filename for each image
                if len(processed) > 1:
                    base, ext = os.path.splitext(filename)
                    current_filename = f"{base}_{idx}{ext}"
                else:
                    current_filename = filename
                
                # Create the storage key (path) for the file
                storage_key = prefix + current_filename
                
                # Upload based on provider
                if provider == "aws":
                    print(f"[EmProps] Uploading to AWS S3: {bucket}/{storage_key}", flush=True)
                    
                    # Upload to S3 with content type
                    s3_client.upload_fileobj(
                        image_bytes, 
                        bucket, 
                        storage_key,
                        ExtraArgs={'ContentType': mime_type}
                    )
                    
                    # Verify upload using our dedicated verification method
                    if self.verify_s3_upload(s3_client, bucket, storage_key):
                        saved.append(current_filename)
                        print(f"[EmProps] Successfully uploaded and verified: {bucket}/{storage_key}", flush=True)
                    else:
                        print(f"[EmProps] Failed to verify upload: {bucket}/{storage_key}", flush=True)
                        
                elif provider == "google":
                    print(f"[EmProps] Uploading to Google Cloud Storage: {bucket}/{storage_key}", flush=True)
                    
                    try:
                        # Upload to GCS with content type
                        gcs_handler.upload_from_fileobj(image_bytes, storage_key, content_type=mime_type)
                        
                        # Verify upload using our dedicated verification method
                        if self.verify_gcs_upload(gcs_handler, storage_key):
                            saved.append(current_filename)
                            print(f"[EmProps] Successfully uploaded and verified: {bucket}/{storage_key}", flush=True)
                        else:
                            print(f"[EmProps] Failed to verify upload: {bucket}/{storage_key}", flush=True)
                    except Exception as e:
                        print(f"[EmProps] Error uploading to GCS: {str(e)}", flush=True)
                        raise e
                        
                elif provider == "azure":
                    print(f"[EmProps] Uploading to Azure Blob Storage: {bucket}/{storage_key}", flush=True)
                    
                    try:
                        # Debug: Print Azure credentials being used
                        if self.azure_account_name:
                            print(f"[EmProps] Debug - Using Azure Storage Account: {self.azure_account_name}")
                        if self.azure_account_key:
                            print(f"[EmProps] Debug - Using Azure Storage Key: {self.azure_account_key[:4]}...")
                        print(f"[EmProps] Debug - Using Azure Container: {bucket}")
                        
                        # Initialize Azure handler with the specified bucket (container)
                        log_debug(f"Initializing Azure handler with container: {bucket}")
                        azure_handler = AzureHandler(bucket)
                        
                        # Upload directly from memory stream
                        log_debug(f"Uploading to Azure blob: {storage_key}")
                        blob_client = azure_handler.container_client.get_blob_client(storage_key)
                        
                        # Rewind the file pointer to the beginning
                        image_bytes.seek(0)
                        
                        # Upload the blob with content settings
                        from azure.storage.blob import ContentSettings
                        content_settings = ContentSettings(content_type=mime_type)
                        blob_client.upload_blob(
                            image_bytes, 
                            overwrite=True, 
                            content_settings=content_settings
                        )
                        
                        # Verify upload using our dedicated verification method
                        if self.verify_azure_upload(azure_handler, storage_key, bucket):
                            saved.append(current_filename)
                            print(f"[EmProps] Successfully uploaded and verified: {bucket}/{storage_key}", flush=True)
                        else:
                            print(f"[EmProps] Failed to verify upload: {bucket}/{storage_key}", flush=True)
                    except Exception as e:
                        log_debug(f"Error uploading to Azure: {str(e)}\n{traceback.format_exc()}")
                        print(f"[EmProps] Error uploading to Azure: {str(e)}", flush=True)
                        raise e
            
            # Return the local preview results for UI display
            return {"ui": {"images": local_results}}
            
        except Exception as e:
            print(f"[EmProps] Error saving to cloud storage: {str(e)}", flush=True)
            raise e

    def verify_s3_upload(self, s3_client, bucket: str, key: str, max_attempts: int = 5, delay: int = 1) -> bool:
        """Verify that a file exists in S3 by checking with head_object"""
        import time
        
        for attempt in range(max_attempts):
            try:
                s3_client.head_object(Bucket=bucket, Key=key)
                return True
            except Exception as e:
                if attempt < max_attempts - 1:
                    print(f"[EmProps] Waiting for S3 file to be available... attempt {attempt + 1}/{max_attempts}")
                    time.sleep(delay)
                else:
                    print(f"[EmProps] Warning: Could not verify S3 upload: {str(e)}")
                    return False
        return False
        
    def verify_gcs_upload(self, gcs_handler: GCSHandler, key: str, max_attempts: int = 5, delay: int = 1) -> bool:
        """Verify that a file exists in GCS by checking with exists method"""
        import time
        
        for attempt in range(max_attempts):
            try:
                if gcs_handler.object_exists(key):
                    return True
                if attempt < max_attempts - 1:
                    print(f"[EmProps] Waiting for GCS file to be available... attempt {attempt + 1}/{max_attempts}")
                    time.sleep(delay)
                else:
                    print(f"[EmProps] Warning: Could not verify GCS upload")
                    return False
            except Exception as e:
                if attempt < max_attempts - 1:
                    print(f"[EmProps] Error checking GCS file, retrying... attempt {attempt + 1}/{max_attempts}")
                    time.sleep(delay)
                else:
                    print(f"[EmProps] Warning: Could not verify GCS upload: {str(e)}")
                    return False
        return False
        
    # Added: 2025-05-07T14:11:24-04:00 - Azure verification method
    # Updated: 2025-06-29 - Only check CDN for production bucket
    def verify_azure_upload(self, azure_handler: AzureHandler, key: str, bucket: str, max_attempts: int = 5, delay: int = 1) -> bool:
        """Verify that a file exists in Azure Blob Storage and optionally check CDN availability for production bucket"""
        import time
        import requests
        
        # First verify blob storage
        blob_verified = False
        for attempt in range(max_attempts):
            try:
                if azure_handler.object_exists(key):
                    blob_verified = True
                    print(f"[EmProps] Azure blob verified: {key}")
                    break
                if attempt < max_attempts - 1:
                    print(f"[EmProps] Waiting for Azure blob to be available... attempt {attempt + 1}/{max_attempts}")
                    time.sleep(delay)
                else:
                    print(f"[EmProps] Warning: Could not verify Azure upload")
                    return False
            except Exception as e:
                if attempt < max_attempts - 1:
                    print(f"[EmProps] Error checking Azure blob, retrying... attempt {attempt + 1}/{max_attempts}")
                    time.sleep(delay)
                else:
                    print(f"[EmProps] Warning: Could not verify Azure upload: {str(e)}")
                    return False
        
        if not blob_verified:
            return False
        
        # Only check CDN for production container
        if bucket != self.production_cdn_container:
            print(f"[EmProps] Skipping CDN check for non-production container: {bucket}")
            return True
        
        # Now verify CDN availability for production bucket
        # Use CDN_URI from environment if available, otherwise fall back to default
        cdn_base = os.getenv('CDN_URI', 'https://cdn.emprops.ai')
        cdn_url = f"{cdn_base}/{key}"
        print(f"[EmProps] Verifying CDN availability at: {cdn_url}")
        
        # Increase max attempts for CDN propagation (30 seconds with 6 attempts of 5 seconds each)
        cdn_max_attempts = 6
        cdn_delay = 5
        
        for attempt in range(cdn_max_attempts):
            try:
                response = requests.head(cdn_url, timeout=10)
                if response.status_code == 200:
                    print(f"[EmProps] CDN verified: {cdn_url}")
                    return True
                elif response.status_code == 404:
                    if attempt < cdn_max_attempts - 1:
                        print(f"[EmProps] Waiting for CDN propagation... attempt {attempt + 1}/{cdn_max_attempts} (status: {response.status_code})")
                        time.sleep(cdn_delay)
                    else:
                        print(f"[EmProps] Warning: CDN not available after {cdn_max_attempts * cdn_delay} seconds")
                        return False
                else:
                    print(f"[EmProps] Unexpected CDN response status: {response.status_code}")
                    if attempt < cdn_max_attempts - 1:
                        time.sleep(cdn_delay)
            except requests.exceptions.RequestException as e:
                if attempt < cdn_max_attempts - 1:
                    print(f"[EmProps] Error checking CDN, retrying... attempt {attempt + 1}/{cdn_max_attempts}: {str(e)}")
                    time.sleep(cdn_delay)
                else:
                    print(f"[EmProps] Warning: Could not verify CDN availability: {str(e)}")
                    return False
        
        return False
