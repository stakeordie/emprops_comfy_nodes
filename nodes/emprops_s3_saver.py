import os
import boto3
import folder_paths
from dotenv import load_dotenv
from ..utils import unescape_env_value
from .helpers.image_save_helper import ImageSaveHelper

class EmProps_S3_Saver:
    """
    Node for saving files to S3 with dynamic prefix support
    """
    def __init__(self):
        self.s3_bucket = "emprops-share"
        self.image_helper = ImageSaveHelper()
        self.type = "s3_output"
        self.output_dir = folder_paths.get_output_directory()
        self.compress_level = 4
        
        # First try system environment
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

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
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
    FUNCTION = "save_to_s3"
    CATEGORY = "EmProps"
    OUTPUT_NODE = True
    DESCRIPTION = "Saves the input images to S3 with configurable bucket and prefix and displays them in the UI."

    def verify_s3_upload(self, s3_client, bucket, key, max_attempts=5, delay=1):
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

    def save_to_s3(self, images, prefix, filename, bucket, prompt=None, extra_pnginfo=None):
        """Save images to S3 with the specified prefix and filename"""
        try:
            # Debug: Print credentials being used (first 4 chars only)
            if self.aws_access_key:
                print(f"[EmProps] Debug - Using Access Key ID: {self.aws_access_key[:4]}...")
            if self.aws_secret_key:
                print(f"[EmProps] Debug - Using Secret Key: {self.aws_secret_key[:4]}...")
            print(f"[EmProps] Debug - Using Region: {self.aws_region}")

            # Initialize S3 client with explicit credentials
            s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.aws_region
            )
            
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
                
                s3_key = prefix + current_filename
                print(f"[EmProps] Uploading to S3: {bucket}/{s3_key}", flush=True)
                
                # Upload to S3 with content type
                s3_client.upload_fileobj(
                    image_bytes, 
                    bucket, 
                    s3_key,
                    ExtraArgs={'ContentType': mime_type}
                )
                
                # Verify upload
                if self.verify_s3_upload(s3_client, bucket, s3_key):
                    saved.append(current_filename)
                    print(f"[EmProps] Successfully uploaded and verified: {bucket}/{s3_key}", flush=True)
                else:
                    print(f"[EmProps] Failed to verify upload: {bucket}/{s3_key}", flush=True)
            
            return self.image_helper.format_ui_response(saved, prefix, self.type)
            
        except Exception as e:
            print(f"[EmProps] Error saving to S3: {str(e)}", flush=True)
            raise e
