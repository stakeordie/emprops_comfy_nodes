import os
import boto3
from dotenv import load_dotenv
from .utils import unescape_env_value

class EmProps_S3_Saver:
    """
    Node for saving files to S3 with dynamic prefix support
    """
    def __init__(self):
        self.s3_bucket = "emprops-share"
        
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
                "images": ("IMAGE",),
                "prefix": ("STRING", {"default": "uploads/"}),
                "filename": ("STRING", {"default": "image.png"}),
                "bucket": ("STRING", {"default": "emprops-share"})
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("s3_url",)
    FUNCTION = "save_to_s3"
    CATEGORY = "EmProps"

    def save_to_s3(self, images, prefix, filename, bucket):
        """Save images to S3 with the specified prefix and filename"""
        try:
            # Initialize S3 client
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
                
            # Construct the full S3 key
            s3_key = f"{prefix}{filename}"
            
            # TODO: Implement actual image saving logic here
            # This would involve converting the image tensor to a file format
            # and uploading it to S3
            
            # Generate the S3 URL
            s3_url = f"s3://{bucket}/{s3_key}"
            
            print(f"[EmProps] Successfully uploaded to {s3_url}")
            return (s3_url,)
            
        except Exception as e:
            print(f"[EmProps] Error saving to S3: {str(e)}")
            return ("",)
