import os
import sys
import folder_paths  # type: ignore # Custom module without stubs
import json
import requests
import boto3
import botocore
import traceback
import time
from ..utils import S3Handler
import tqdm

# Added: 2025-04-20T21:33:36-04:00 - Enhanced logging for debugging
def log_debug(message):
    """Enhanced logging function with timestamp and stack info"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    caller = traceback.extract_stack()[-2]
    file = os.path.basename(caller.filename)
    line = caller.lineno
    print(f"[EmProps MODEL_DOWNLOADER_CHECKPOINT {timestamp}] [{file}:{line}] {message}", flush=True)

# Clear caches before class definition
log_debug("Clearing folder_paths caches")
try:
    folder_paths.cache_helper.clear()
    folder_paths.filename_list_cache.clear()
    log_debug("Caches cleared successfully")
except Exception as e:
    log_debug(f"Error clearing caches: {str(e)}\n{traceback.format_exc()}")


class EmpropsModelDownloaderCheckpoint:
    @classmethod
    def INPUT_TYPES(cls):
        log_debug("EmpropsModelDownloaderCheckpoint.INPUT_TYPES called")
        try:
            result = {
                "required": {
                    "source_type": (["url", "s3"],),
                    "filename": ("STRING", {"default": "", "placeholder": "model.safetensors"}),
                    # URL input
                    "url": ("STRING", {
                        "default": "",
                        "placeholder": "https://example.com/model.safetensors"
                    }),
                    # S3 input
                    "s3_bucket": ("STRING", {
                        "default": "emprops-share"
                    })
                }
            }
            log_debug(f"INPUT_TYPES returning: {result}")
            return result
        except Exception as e:
            log_debug(f"ERROR in INPUT_TYPES: {str(e)}\n{traceback.format_exc()}")
            # Provide a fallback in case of error
            return {
                "required": {
                    "source_type": (["url", "s3"],),
                    "filename": ("STRING", {"default": "", "placeholder": "model.safetensors"}),
                    "url": ("STRING", {"default": "", "placeholder": "https://example.com/model.safetensors"}),
                    "s3_bucket": ("STRING", {"default": "emprops-share"})
                }
            }

    @classmethod
    def IS_CHANGED(cls, source_type, **kwargs):
        log_debug(f"IS_CHANGED called with source_type: {source_type}")
        return float("NaN")  # So it always updates

    # Added: 2025-04-20T21:33:36-04:00 - Fixed return types to use string type instead of function
    RETURN_TYPES = ("STRING",)
    
    @classmethod
    def __init_subclass__(cls, **kwargs):
        log_debug(f"EmpropsModelDownloaderCheckpoint subclass initialized: {cls.__name__}")
        super().__init_subclass__(**kwargs)
        
    # Added: 2025-04-20T21:33:36-04:00 - Organized class variables for better readability
    RETURN_NAMES = ("FILENAME",)
    FUNCTION = "run"
    CATEGORY = "EmProps/Loaders"

    def run(self, source_type, filename, url, s3_bucket):
        log_debug(f"run method called with source_type={source_type}, filename={filename}, url={url}, s3_bucket={s3_bucket}")
        try:
            # Added: 2025-04-20T19:47:26-04:00 - Enhanced logging for debugging
            log_debug("Clearing caches before execution")
            folder_paths.cache_helper.clear()
            folder_paths.filename_list_cache.clear()
            
            # Get the current checkpoint files (for information only)
            current_files = folder_paths.get_filename_list("checkpoints")
            log_debug(f"Current checkpoint files: {len(current_files)} files")
            # Don't modify RETURN_TYPES here - it should remain as ("STRING",)


            # Hide fields based on source type
            log_debug(f"Processing source type: {source_type}")
            if source_type == "url":
                if not url:
                    log_debug("ERROR: URL is required when using URL source type")
                    raise ValueError("URL is required when using URL source type")
                log_debug(f"Using URL source: {url}")
                s3_bucket = None  # Hide s3 field
            else:  # s3
                if not filename:
                    log_debug("ERROR: Filename is required when using S3 source type")
                    raise ValueError("Filename is required when using S3 source type")
                log_debug(f"Using S3 source: bucket={s3_bucket}, filename={filename}")
                url = None  # Hide url field
            
            # Get the base models directory by getting any model path and going up two levels
            checkpoint_paths = folder_paths.get_folder_paths("checkpoints")
            log_debug(f"Available checkpoint paths: {checkpoint_paths}")
            output_dir = checkpoint_paths[0]  # Get first checkpoint path
            log_debug(f"Using output directory: {output_dir}")
            
            # Create output path variable first so it's available to both download methods
            output_path = os.path.join(output_dir, filename)
            log_debug(f"Target output path: {output_path}")
            
            # Download based on source type
            if source_type == "s3":
                try:
                    log_debug(f"Preparing to download from S3 bucket: {s3_bucket}")
                    # Initialize S3 handler with proper credential management
                    s3_handler = S3Handler(s3_bucket)
                    
                    # Construct and verify the S3 key
                    s3_key = f"models/checkpoints/{filename}"
                    log_debug(f"Trying S3 key: {s3_key}")
                    
                    # Check if the object exists before attempting download
                    if not s3_handler.object_exists(s3_key):
                        # Try without models/ prefix as fallback
                        s3_key = f"checkpoints/{filename}"
                        log_debug(f"First key not found, trying fallback: {s3_key}")
                        if not s3_handler.object_exists(s3_key):
                            log_debug(f"File not found in S3 with either key pattern")
                            raise ValueError(f"File not found in S3. Tried:\n1. s3://{s3_bucket}/models/checkpoints/{filename}\n2. s3://{s3_bucket}/checkpoints/{filename}")
                    
                    # Create directory if it doesn't exist
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    log_debug(f"Created directory structure for: {output_path}")
                    
                    print(f"[EmProps] Found file in S3, downloading to: {output_path}")
                    success, error = s3_handler.download_file(s3_key, output_path)
                    if not success:
                        raise ValueError(f"Download failed: {error}")
                    
                    if not os.path.exists(output_path):
                        raise ValueError("File was not downloaded successfully")
                        
                    print(f"[EmProps] Successfully downloaded model to: {output_path}")
                except Exception as e:
                    raise ValueError(f"S3 download failed: {str(e)}")
            else:  # url
                try:
                    log_debug(f"Downloading from URL: {url}")
                    response = requests.get(url, stream=True)
                    response.raise_for_status()
                    log_debug(f"Response status code: {response.status_code}")
                    log_debug(f"Response headers: {response.headers}")
                    
                    # Get filename from URL if not provided
                    if not filename:
                        log_debug("Filename not provided, attempting to extract from response")
                        content_disposition = response.headers.get('content-disposition')
                        if content_disposition:
                            import re
                            log_debug(f"Found content-disposition: {content_disposition}")
                            filename_match = re.search(r'filename="(.+?)"', content_disposition)
                            if filename_match:
                                filename = filename_match.group(1)
                                log_debug(f"Extracted filename from content-disposition: {filename}")
                        
                        # If still no filename, get it from URL
                        if not filename:
                            log_debug("Extracting filename from URL path")
                            from urllib.parse import urlparse
                            parsed_url = urlparse(url)
                            filename = os.path.basename(parsed_url.path)
                            log_debug(f"Extracted filename from URL: {filename}")
                            
                        # If still no filename, use default
                        if not filename:
                            log_debug("No filename could be determined, using default")
                            filename = "downloaded_model.safetensors"
                    
                    # Ensure filename has extension
                    if not os.path.splitext(filename)[1]:
                        log_debug(f"Adding .safetensors extension to filename: {filename}")
                        filename += ".safetensors"
                    
                    # Download file
                    output_path = os.path.join(output_dir, filename)
                    log_debug(f"Saving to: {output_path}")
                    
                    # Get file size for progress bar
                    file_size = int(response.headers.get('content-length', 0))
                    log_debug(f"File size: {file_size} bytes")
                    
                    # Download with progress bar
                    with open(output_path, 'wb') as f, tqdm.tqdm(
                        desc=filename,
                        total=file_size,
                        unit='B',
                        unit_scale=True,
                        unit_divisor=1024,
                    ) as bar:
                        downloaded = 0
                        for chunk in response.iter_content(chunk_size=8192):
                            size = f.write(chunk)
                            bar.update(size)
                            downloaded += size
                        log_debug(f"Downloaded {downloaded} of {file_size} bytes")
                    
                    log_debug(f"Download complete: {filename}")
                    
                except Exception as e:
                    log_debug(f"ERROR downloading from URL: {str(e)}\n{traceback.format_exc()}")
                    raise

            # Refresh the model list
            log_debug("Refreshing model list after download")
            folder_paths.cache_helper.clear()
            folder_paths.filename_list_cache.clear()
            
            # Verify file exists after download
            if os.path.exists(output_path):
                log_debug(f"Verified file exists at: {output_path}")
                file_size = os.path.getsize(output_path)
                log_debug(f"File size on disk: {file_size} bytes")
            else:
                log_debug(f"WARNING: File not found after download: {output_path}")
            
            # Get updated file list
            updated_files = folder_paths.get_filename_list("checkpoints")
            log_debug(f"Updated checkpoint files: {len(updated_files)} files")
            log_debug(f"Is downloaded file in list: {filename in updated_files}")
            
            # Return the filename as a string
            log_debug(f"Returning filename: {filename}")
            # Make sure we're returning a string, not a list or tuple of strings
            return (filename,)
        except Exception as e:
            log_debug(f"CRITICAL ERROR in run method: {str(e)}\n{traceback.format_exc()}")
            raise
