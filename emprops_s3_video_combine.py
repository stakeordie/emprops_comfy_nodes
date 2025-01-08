import os
import sys
import boto3
import folder_paths
import importlib.util
from dotenv import load_dotenv
from .utils import unescape_env_value

# Import VideoCombine from VideoHelperSuite
vhs_path = os.path.join(os.path.dirname(__file__), 'deps', 'ComfyUI-VideoHelperSuite', 'videohelpersuite', 'nodes.py')
spec = importlib.util.spec_from_file_location("vhs_nodes", vhs_path)
vhs_nodes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vhs_nodes)
VideoCombine = vhs_nodes.VideoCombine

class EmProps_S3_Video_Combine(VideoCombine):
    """
    Node for combining videos and uploading to S3 with dynamic prefix support
    """
    def __init__(self):
        super().__init__()
        self.s3_bucket = "emprops-share"
        self.type = "s3_video_output"
        self.output_dir = folder_paths.get_output_directory()
        
        # First try system environment
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.aws_region = os.getenv('AWS_DEFAULT_REGION')

        # If not found, try .env and .env.local files
        if not self.aws_access_key or not self.aws_secret_key:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
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

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "frame_rate": ("INT", {"default": 8, "min": 1, "max": 60}),
                "loop_count": ("INT", {"default": 0, "min": 0, "max": 100}),
                "filename_prefix": ("STRING", {"default": ""}),
                "s3_prefix": ("STRING", {"default": "videos/"}),
                "format": (["video/mp4", "video/webm", "image/gif"],),
                "audio": ("AUDIO", {"default": None})
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("url",)
    FUNCTION = "combine_and_upload"
    OUTPUT_NODE = True
    CATEGORY = "EmProps"

    def combine_and_upload(self, images, frame_rate, loop_count, filename_prefix, s3_prefix, format="video/mp4", audio=None):
        # First combine the video using parent class
        video_path = super().combine(images, frame_rate, loop_count, filename_prefix, format, audio)[0]
        
        try:
            # Initialize S3 client
            s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.aws_region
            )

            # Clean up the prefix
            s3_prefix = s3_prefix.strip('/')
            if s3_prefix:
                s3_prefix += '/'

            # Get the filename from the path
            filename = os.path.basename(video_path)
            
            # Upload to S3
            s3_key = f"{s3_prefix}{filename}"
            content_type = format
            
            s3_client.upload_file(
                video_path,
                self.s3_bucket,
                s3_key,
                ExtraArgs={'ContentType': content_type}
            )

            # Generate the URL
            url = f"https://{self.s3_bucket}.s3.amazonaws.com/{s3_key}"
            print(f"[EmProps] Video uploaded successfully to: {url}")
            
            return (url,)
            
        except Exception as e:
            print(f"[EmProps] Error uploading to S3: {str(e)}")
            raise e
