import os
import boto3  # type: ignore # Will be fixed with types-boto3
import folder_paths  # type: ignore # Custom module without stubs
from dotenv import load_dotenv
from typing import Optional, Tuple, List, Dict, Any
from ..utils import unescape_env_value, S3Handler, GCSHandler, GCS_AVAILABLE
from .helpers.image_save_helper import ImageSaveHelper

class EmProps_S3_Saver:
    """
    Node for saving files to cloud storage (AWS S3 or Google Cloud Storage) with dynamic prefix support
    """
    def __init__(self):
        # Initialize common properties
        self.default_bucket = "emprops-share"
        self.image_helper = ImageSaveHelper()
        self.type = "s3_output"  # Keep the same type for backward compatibility
        self.output_dir = folder_paths.get_output_directory()
        self.compress_level = 4
        
        # Check if Google Cloud Storage is available
        self.gcs_available = GCS_AVAILABLE
        if self.gcs_available:
            print("[EmProps] Google Cloud Storage support is available")
        else:
            print("[EmProps] Google Cloud Storage support is not available. Install with 'pip install google-cloud-storage'")
        
        # First try system environment for AWS credentials
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.aws_region = os.getenv('AWS_DEFAULT_REGION')

        # If not found, try .env and .env.local files
        if not self.aws_access_key or not self.aws_secret_key:
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go up one level to project root
            
            # Try .env first
            env_path = os.path.join(current_dir, '.env')
            if os.path.exists(env_path):
                print("[EmProps] Loading .env from: " + env_path)
                load_dotenv(env_path)
                self.aws_secret_key = self.aws_secret_key or unescape_env_value(os.getenv('AWS_SECRET_ACCESS_KEY_ENCODED', ''))
                if not self.aws_secret_key:
                    self.aws_secret_key = self.aws_secret_key or os.getenv('AWS_SECRET_ACCESS_KEY', '')
                    print("[EmProps] AWS_SECRET_ACCESS_KEY_ENCODED not found in .env, trying AWS_SECRET_ACCESS_KEY")
                self.aws_access_key = self.aws_access_key or os.getenv('AWS_ACCESS_KEY_ID', '')
                self.aws_region = self.aws_region or os.getenv('AWS_DEFAULT_REGION', '')
            
            # If still not found, try .env.local
            if not self.aws_access_key or not self.aws_secret_key:
                env_local_path = os.path.join(current_dir, '.env.local')
                if os.path.exists(env_local_path):
                    print("[EmProps] Loading .env.local from: " + env_local_path)
                    load_dotenv(env_local_path)
                    self.aws_secret_key = self.aws_secret_key or unescape_env_value(os.getenv('AWS_SECRET_ACCESS_KEY_ENCODED', ''))
                    if not self.aws_secret_key:
                        self.aws_secret_key = self.aws_secret_key or os.getenv('AWS_SECRET_ACCESS_KEY', '')
                        print("[EmProps] AWS_SECRET_ACCESS_KEY_ENCODED not found in .env.local, trying AWS_SECRET_ACCESS_KEY")
                    self.aws_access_key = self.aws_access_key or os.getenv('AWS_ACCESS_KEY_ID', '')
                    self.aws_region = self.aws_region or os.getenv('AWS_DEFAULT_REGION', '')
        
        # Set default region if still not set
        self.aws_region = self.aws_region or 'us-east-1'

        if not self.aws_secret_key or not self.aws_access_key:
            print("[EmProps] Warning: AWS credentials not found in environment or .env.local")
            
        # Check for Google Cloud credentials
        self.gcs_credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not self.gcs_credentials_path and self.gcs_available:
            print("[EmProps] Warning: GOOGLE_APPLICATION_CREDENTIALS not found in environment")

    @classmethod
    def INPUT_TYPES(cls):
        # Determine available providers based on imports
        providers = ["aws"]
        if GCS_AVAILABLE:
            providers.append("google")
            
        return {
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

    RETURN_TYPES = ()  
    FUNCTION = "save_to_cloud"
    CATEGORY = "EmProps"
    OUTPUT_NODE = True
    DESCRIPTION = "Saves the input images to cloud storage (AWS S3 or Google Cloud Storage) with configurable bucket and prefix and displays them in the UI."

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

    def save_to_cloud(self, images, provider, prefix, filename, bucket, prompt=None, extra_pnginfo=None):
        """Save images to cloud storage (AWS S3 or Google Cloud Storage) with the specified prefix and filename"""
        # Log the provider for debugging
        print(f"[EmProps] Using cloud provider: {provider}")
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
            else:
                raise ValueError(f"Unsupported provider: {provider}")
            
            # Ensure prefix ends with '/'
            if not prefix.endswith('/'):
                prefix += '/'
            
            # Remove leading '/' if present
            if prefix.startswith('/'):
                prefix = prefix[1:]
            
            # Get the file extension and format from filename
            ext = os.path.splitext(filename)[1].lower()
            format_map = {
                '.jpg': ('JPEG', 'image/jpeg'),
                '.jpeg': ('JPEG', 'image/jpeg'),
                '.png': ('PNG', 'image/png'),
                '.gif': ('GIF', 'image/gif'),
                '.webp': ('WEBP', 'image/webp'),
                '.tiff': ('TIFF', 'image/tiff'),
                '.bmp': ('BMP', 'image/bmp')
            }
            format_info = format_map.get(ext, ('PNG', 'image/png'))
            
            # Process images with format and mime type
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
                    
                    # Verify upload
                    if self.verify_s3_upload(s3_client, bucket, storage_key):
                        saved.append(current_filename)
                        print(f"[EmProps] Successfully uploaded and verified: {bucket}/{storage_key}", flush=True)
                    else:
                        print(f"[EmProps] Failed to verify upload: {bucket}/{storage_key}", flush=True)
                        
                elif provider == "google":
                    print(f"[EmProps] Uploading to Google Cloud Storage: {bucket}/{storage_key}", flush=True)
                    
                    try:
                        # Get bucket and create blob
                        bucket_obj = gcs_handler.gcs_client.bucket(bucket)
                        blob = bucket_obj.blob(storage_key)
                        
                        # Upload from file-like object with content type
                        blob.upload_from_file(
                            image_bytes,
                            content_type=mime_type,
                            rewind=True  # Rewind the file pointer to the beginning
                        )
                        
                        # Verify upload
                        if self.verify_gcs_upload(gcs_handler, storage_key):
                            saved.append(current_filename)
                            print(f"[EmProps] Successfully uploaded and verified: {bucket}/{storage_key}", flush=True)
                        else:
                            print(f"[EmProps] Failed to verify upload: {bucket}/{storage_key}", flush=True)
                    except Exception as e:
                        print(f"[EmProps] Error uploading to GCS: {str(e)}", flush=True)
                        raise e
            
            return self.image_helper.format_ui_response(saved, prefix, self.type)
            
        except Exception as e:
            print(f"[EmProps] Error saving to S3: {str(e)}", flush=True)
            raise e
