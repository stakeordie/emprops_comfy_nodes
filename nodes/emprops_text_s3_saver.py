import os
import boto3
import folder_paths
from dotenv import load_dotenv
from ..utils import unescape_env_value

class EmProps_Text_S3_Saver:
    """
    Node for saving text content to S3 with dynamic prefix support
    """
    def __init__(self):
        self.s3_bucket = "emprops-share"
        self.type = "s3_output"
        
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
                "text": ("STRING", {"multiline": True}),  # Allow multiline text input
                "prefix": ("STRING", {"default": "uploads/"}),
                "filename": ("STRING", {"default": "text.txt"}),
                "bucket": ("STRING", {"default": "emprops-share"})
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "save_to_s3"
    CATEGORY = "EmProps"
    OUTPUT_NODE = True
    DESCRIPTION = "Saves text content to S3 with configurable bucket and prefix."

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

    def save_to_s3(self, text, prefix, filename, bucket):
        """Save text content to S3 with the specified prefix and filename"""
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
            
            # Get the file extension
            ext = os.path.splitext(filename)[1].lower()
            if not ext:  # If no extension provided, default to .txt
                filename += '.txt'
                ext = '.txt'
            
            # Set appropriate content type
            content_type = 'text/plain'
            if ext == '.json':
                content_type = 'application/json'
            elif ext == '.html':
                content_type = 'text/html'
            elif ext == '.md':
                content_type = 'text/markdown'
            
            # Construct the S3 key
            s3_key = prefix + filename
            print(f"[EmProps] Uploading to S3: {bucket}/{s3_key}", flush=True)
            
            # Upload to S3 with content type
            from io import BytesIO
            text_bytes = BytesIO(text.encode('utf-8'))
            s3_client.upload_fileobj(
                text_bytes,
                bucket,
                s3_key,
                ExtraArgs={'ContentType': content_type}
            )
            
            # Verify upload
            if self.verify_s3_upload(s3_client, bucket, s3_key):
                print(f"[EmProps] Successfully uploaded and verified: {bucket}/{s3_key}", flush=True)
                return {"ui": {"text": [f"Saved to: s3://{bucket}/{s3_key}"]}}
            else:
                print(f"[EmProps] Failed to verify upload: {bucket}/{s3_key}", flush=True)
                return {"ui": {"text": [f"Failed to verify upload: s3://{bucket}/{s3_key}"]}}
            
        except Exception as e:
            print(f"[EmProps] Error saving to S3: {str(e)}", flush=True)
            raise e
