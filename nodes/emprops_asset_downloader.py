import os
import sys
import json
import time
import math
import shutil
import requests
import traceback
from pathlib import Path
from tqdm import tqdm
from dotenv import load_dotenv
from server import PromptServer
import folder_paths  # Updated: 2025-05-12T14:04:35-04:00 - Use folder_paths module instead of direct import
from typing import Dict, List, Optional, TypedDict
from ..db.model_cache import model_cache_db

# Load environment variables from .env file in the node's root directory
node_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv_path = os.path.join(node_root, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print(f"[EmProps] Loaded environment variables from: {dotenv_path}")
else:
    print(f"[EmProps] Warning: No .env file found at {dotenv_path}")
    # Also try .env.local
    dotenv_local_path = os.path.join(node_root, '.env.local')
    if os.path.exists(dotenv_local_path):
        load_dotenv(dotenv_local_path)
        print(f"[EmProps] Loaded environment variables from: {dotenv_local_path}")
    else:
        print(f"[EmProps] Warning: No .env.local file found at {dotenv_local_path}")

# Define token provider type
class TokenProvider(TypedDict):
    name: str
    env_var: Optional[str]

# Supported token providers with their display names and environment variable names
TOKEN_PROVIDERS: List[TokenProvider] = [
    {"name": "None", "env_var": None},
    {"name": "Hugging Face", "env_var": "HF_TOKEN"},
    {"name": "Custom", "env_var": "CUSTOM"}
]

# Added: 2025-05-12T13:52:12-04:00 - Asset Downloader implementation 
def log_debug(message):
    """Enhanced logging function with timestamp and stack info"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    caller = traceback.extract_stack()[-2]
    file = os.path.basename(caller.filename)
    line = caller.lineno
    print(f"[EmProps DEBUG {timestamp}] [{file}:{line}] {message}", flush=True)

def get_token_provider_options() -> List[str]:
    """Get token provider options for the dropdown."""
    return [provider["name"] for provider in TOKEN_PROVIDERS]

def get_token_from_provider(provider_name: str, custom_token: str = "") -> Optional[str]:
    """
    Get token based on the selected provider and optional custom token.
    
    Args:
        provider_name: Name of the selected provider
        custom_token: Token provided in the custom token field (if any)
        
    Returns:
        str or None: The token to use, or None if no token should be used
    """
    # Log all environment variables for debugging (filtered for security)
    log_debug("=== Environment Variables ===")
    for k, v in os.environ.items():
        if 'TOKEN' in k or 'KEY' in k or 'SECRET' in k:
            log_debug(f"{k} = {'*' * 8 + v[-4:] if v else 'None'}")
    log_debug("============================")

    # If a custom token is provided, use it regardless of the provider
    if custom_token and custom_token.strip():
        log_debug(f"Using custom token: {'*' * 8 + custom_token[-4:] if custom_token else 'None'}")
        if custom_token.startswith("$"):
            # Handle environment variable reference
            var_name = custom_token[1:]
            env_value = os.getenv(var_name)
            log_debug(f"Looking up environment variable: {var_name} = {'*' * 8 + env_value[-4:] if env_value else 'None'}")
            return env_value if env_value is not None else custom_token
        return custom_token
    
    # Find the selected provider
    provider = next((p for p in TOKEN_PROVIDERS if p["name"] == provider_name), None)
    if not provider or not provider["env_var"] or provider["env_var"] == "CUSTOM":
        log_debug(f"No valid provider found for: {provider_name}")
        return None
    
    # Get token from environment variable
    env_var_name = provider["env_var"]
    token = os.getenv(env_var_name)
    log_debug(f"Retrieving token from environment variable: {env_var_name}")
    log_debug(f"Token value: {'*' * 8 + token[-4:] if token else 'None'}")
    log_debug(f"Environment has HF_TOKEN: {'HF_TOKEN' in os.environ}")
    log_debug(f"Environment has {env_var_name}: {env_var_name in os.environ}")
    
    # If token is None, try getting it from the environment directly
    if token is None and env_var_name in os.environ:
        token = os.environ[env_var_name]
        log_debug(f"Retrieved token directly from os.environ: {'*' * 8 + token[-4:] if token else 'None'}")
    
    return token

def model_folders():
    # Updated: 2025-05-12T14:04:35-04:00 - Get folder names from folder_paths
    # Updated: 2025-05-30T10:38:56-04:00 - Added text_encoders to the list of folders
    folders = sorted(list(folder_paths.folder_names_and_paths.keys()))
    
    # Make sure text_encoders is in the list (for CLIP models)
    if "text_encoders" not in folders and "text_encoders" in folder_paths.folder_names_and_paths:
        log_debug("Adding text_encoders folder to model folders list")
        folders.append("text_encoders")
        
    # Make sure diffusion_models is in the list (for UNET models)
    if "diffusion_models" not in folders and "diffusion_models" in folder_paths.folder_names_and_paths:
        log_debug("Adding diffusion_models folder to model folders list")
        folders.append("diffusion_models")
        
    return folders

# Updated: 2025-05-12T14:04:35-04:00 - No longer needed as we use folder_paths

class EmProps_Asset_Downloader:
    # Updated: 2025-05-12T16:00:00-04:00 - Added second output for direct compatibility with Load Checkpoint
    # Updated: 2025-05-13T16:04:00-04:00 - Fixed return type to be STRING instead of list of checkpoints
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("downloaded_path", "ckpt_name")
    OUTPUT_NODE = True
    CATEGORY = "EmProps"
    FUNCTION = "download"

    def __init__(self):
        self.status = "Idle"
        self.progress = 0.0
        self.node_id = None
        log_debug("EmProps_Asset_Downloader initialized")

    @classmethod
    def INPUT_TYPES(cls):
        log_debug("EmProps_Asset_Downloader.INPUT_TYPES called")
        return {
            "required": {
                "url": ("STRING", {"multiline": False, "default": "https://huggingface.co/ByteDance/SDXL-Lightning/resolve/main/sdxl_lightning_4step.safetensors", "widget": True}),
                "save_to": (model_folders(), { "default": "checkpoints", "widget": True }),
                "filename": ("STRING", {"multiline": False, "default": "sdxl_lightning_4step.safetensors", "widget": True}),
                # Added: 2025-06-02T11:43:17-04:00 - Token provider dropdown
                "token_provider": (get_token_provider_options(), {"default": get_token_provider_options()[0][0]}),
            },
            "optional": {
                # Updated: 2025-06-02T11:43:17-04:00 - Make token field optional and only show when Custom is selected
                "token": ("STRING", { 
                    "default": "", 
                    "multiline": False, 
                    "password": True, 
                    "widget": True,
                    "dynamicPrompts": False,
                    "placeholder": "Enter token or $ENV_VAR"
                }),
                # Added: 2025-05-12T14:42:00-04:00 - Test mode checkbox for creating a copy instead of downloading
                "test_with_copy": ("BOOLEAN", {"default": False, "label": "Test with copy"}),
                # Added: 2025-05-12T14:42:00-04:00 - Source filename for test mode
                "source_filename": ("STRING", {"default": "", "multiline": False, "placeholder": "Leave empty to use filename"}),
            },
            "hidden": {
                "node_id": "UNIQUE_ID"
            }
        }
        
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Force update when token_provider changes to update the UI
        if "token_provider" in kwargs:
            return float("inf")
        return 0

    def download(self, url, save_to, filename, token_provider, node_id, token="", test_with_copy=False, source_filename=""):
        log_debug(f"EmProps_Asset_Downloader.download called with url={url}, save_to={save_to}, filename={filename}, token_provider='{token_provider}', node_id={node_id}")
        
        if not url or not save_to or not filename:
            log_debug(f"EmProps_Asset_Downloader: Missing required values: url='{url}', save_to='{save_to}', filename='{filename}'")
            # Updated: 2025-05-13T16:10:33-04:00 - Return consistent tuple format
            return ("", "")
            
        # Get token based on provider and custom token
        auth_token = get_token_from_provider(token_provider, token)
        if auth_token:
            log_debug(f"Using token from provider: {token_provider}")
        else:
            log_debug("No token will be used for this download")
            
        # Updated: 2025-05-12T14:04:35-04:00 - Use folder_paths to get the correct folder path
        if save_to not in folder_paths.folder_names_and_paths:
            log_debug(f"EmProps_Asset_Downloader: Invalid save_to path: {save_to}. Must be a valid model folder.")
            # Updated: 2025-05-13T16:10:33-04:00 - Return consistent tuple format
            return ("", "")
            
        # Get the first folder path for the selected model type
        model_folder = folder_paths.get_folder_paths(save_to)[0]
        log_debug(f"Using model folder: {model_folder}")
        
        # Ensure the model folder exists
        if not os.path.exists(model_folder):
            log_debug(f"Creating model folder: {model_folder}")
            os.makedirs(model_folder, exist_ok=True)
        
        # Construct the full save path
        save_path = os.path.join(model_folder, filename)
        
        # Added: 2025-05-13T18:10:44-04:00 - Check free disk space before downloading
        try:
            # We don't know the file size in advance, so we'll use 0 for required_bytes
            # This will just check against the minimum free space setting
            has_enough_space, space_info = model_cache_db.check_free_space(model_folder)
            
            log_debug(f"Checking free disk space for model folder: {model_folder}")
            log_debug(f"Free space: {space_info['free_gb']:.2f} GB, Minimum required: {space_info['min_free_gb']:.2f} GB")
            
            if not has_enough_space:
                log_debug(f"WARNING: Low disk space! Free: {space_info['free_gb']:.2f} GB, Minimum: {space_info['min_free_gb']:.2f} GB")
                log_debug(f"Will need to evict least recently used models before downloading new ones")
                
                # Added: 2025-05-13T18:17:12-04:00 - Identify files that would be deleted
                try:
                    # Calculate how much space we need to free up
                    space_needed_bytes = (space_info['min_free_bytes'] + space_info.get('required_bytes', 0)) - space_info['free_bytes']
                    space_needed_gb = space_needed_bytes / (1024 * 1024 * 1024)
                    log_debug(f"Need to free up approximately {space_needed_gb:.2f} GB of space")
                    
                    # Get least recently used models that aren't protected
                    # We'll get more than we need to ensure we have enough options
                    lru_models = model_cache_db.get_least_recently_used_models(limit=10)
                    
                    if lru_models:
                        log_debug(f"Found {len(lru_models)} candidate models for deletion:")
                        total_reclaimable_bytes = 0
                        models_to_delete = []
                        
                        for model in lru_models:
                            model_size_gb = model['size_bytes'] / (1024 * 1024 * 1024)
                            log_debug(f"  - {model['filename']} ({model_size_gb:.2f} GB)")
                            log_debug(f"    Last used: {model['last_used']}, Use count: {model['use_count']}")
                            
                            total_reclaimable_bytes += model['size_bytes']
                            models_to_delete.append(model)
                            
                            # Check if we've identified enough models to delete
                            if total_reclaimable_bytes >= space_needed_bytes:
                                reclaimable_gb = total_reclaimable_bytes / (1024 * 1024 * 1024)
                                log_debug(f"Identified {len(models_to_delete)} models that could free up {reclaimable_gb:.2f} GB")
                                break
                        
                        if total_reclaimable_bytes < space_needed_bytes:
                            reclaimable_gb = total_reclaimable_bytes / (1024 * 1024 * 1024)
                            log_debug(f"WARNING: Could only identify {reclaimable_gb:.2f} GB of reclaimable space, need {space_needed_gb:.2f} GB")
                    else:
                        log_debug("No candidate models found for deletion. All models may be protected.")
                        
                    # TODO: Implement actual model deletion
                except Exception as e:
                    log_debug(f"Error identifying files for deletion: {str(e)}")
                    log_debug(traceback.format_exc())
        except Exception as e:
            log_debug(f"Error checking disk space: {str(e)}")
            log_debug(traceback.format_exc())
        
        # Added: 2025-05-12T14:42:00-04:00 - Test with copy mode
        if test_with_copy:
            log_debug(f"EmProps_Asset_Downloader: Test with copy mode enabled")
            
            # Determine source filename (use the target filename if not specified)
            src_filename = source_filename if source_filename else filename
            
            # If source filename is the same as target, modify it to remove the 'x' if present
            if src_filename == filename and filename.endswith('x.' + filename.split('.')[-1]):
                src_filename = filename[:-2] + '.' + filename.split('.')[-1]
            elif src_filename == filename:
                # If they're the same and no 'x', we need to ensure they're different
                name_parts = filename.split('.')
                if len(name_parts) > 1:
                    src_filename = '.'.join(name_parts[:-1]) + '_orig.' + name_parts[-1]
                else:
                    src_filename = filename + '_orig'
            
            source_path = os.path.join(model_folder, src_filename)
            
            if not os.path.exists(source_path):
                log_debug(f"EmProps_Asset_Downloader: Source file does not exist: {source_path}")
                # Updated: 2025-05-13T16:10:33-04:00 - Return consistent tuple format
                return ("Source file not found", "")
                
            log_debug(f"EmProps_Asset_Downloader: Copying {source_path} to {save_path}")
            
            # Create a copy with progress updates
            try:
                # Get file size for progress reporting
                total_size = os.path.getsize(source_path)
                copied = 0
                last_progress_update = 0
                
                with open(source_path, 'rb') as src_file:
                    with open(save_path, 'wb') as dst_file:
                        # Use a reasonable buffer size
                        buffer_size = 4 * 1024 * 1024  # 4MB buffer
                        while True:
                            buffer = src_file.read(buffer_size)
                            if not buffer:
                                break
                                
                            dst_file.write(buffer)
                            copied += len(buffer)
                            
                            # Update progress
                            if total_size > 0:
                                progress = (copied / total_size) * 100.0
                                if (progress - last_progress_update) > 1.0:
                                    log_debug(f"Copying {filename}... {progress:.1f}%")
                                    last_progress_update = progress
                                if progress is not None and hasattr(self, 'node_id'):
                                    PromptServer.instance.send_sync("progress", {
                                        "node": self.node_id,
                                        "value": progress,
                                        "max": 100
                                    })
                
                log_debug(f"EmProps_Asset_Downloader: Successfully copied file to {save_path}")
                
                # Refresh model cache
                log_debug(f"Refreshing model cache for {save_to}")
                if save_to in folder_paths.filename_list_cache:
                    del folder_paths.filename_list_cache[save_to]
                folder_paths.get_filename_list(save_to)
                
                # Return both values
                log_debug(f"EmProps_Asset_Downloader: Returning filename: {filename}")
                return (filename, filename)
                
            except Exception as e:
                error_msg = f"Error downloading file: {str(e)}"
                log_debug(error_msg)
                if 'temp_path' in locals() and temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                        log_debug(f"Removed temporary file: {temp_path}")
                    except Exception as cleanup_error:
                        log_debug(f"Error removing temporary file: {str(cleanup_error)}")
                
                # Log response details if available
                if 'response' in locals() and hasattr(e, 'response'):
                    try:
                        log_debug(f"Response status: {e.response.status_code}")
                        log_debug(f"Response headers: {dict(e.response.headers)}")
                        log_debug(f"Response body: {e.response.text[:500]}...")
                    except Exception as response_error:
                        log_debug(f"Could not log response details: {str(response_error)}")
                
                # Updated: 2025-05-13T16:10:33-04:00 - Return consistent tuple format
                return (f"Error: {error_msg}", "")
        
        # Normal download mode - check if file already exists
        if os.path.exists(save_path):
            log_debug(f"EmProps_Asset_Downloader: File already exists: {os.path.join(save_to, filename)}")
            
            # Added: 2025-05-13T17:28:11-04:00 - Update usage information for existing model
            # Updated: 2025-05-13T17:48:26-04:00 - Added more detailed logging
            try:
                file_size = os.path.getsize(save_path)
                # Check if model exists in database
                model_info = model_cache_db.get_model_info(save_path)
                
                log_debug(f"Checking model in database: {save_path}")
                if model_info:
                    log_debug(f"Model found in database with ID: {model_info['id']}")
                    log_debug(f"Current use count: {model_info['use_count']}")
                    log_debug(f"Last used: {model_info['last_used']}")
                    
                    # Update existing model usage
                    log_debug(f"Updating usage for existing model...")
                    model_cache_db.update_model_usage(save_path)
                    log_debug(f"Successfully updated usage for existing model in cache database")
                else:
                    log_debug(f"Model not found in database, registering it...")
                    # Register model if it's not in the database
                    model_cache_db.register_model(save_path, save_to, file_size)
                    log_debug(f"Successfully registered existing model in cache database")
            except Exception as e:
                log_debug(f"Error updating model in cache database: {str(e)}")
                log_debug(traceback.format_exc())
            
            # Updated: 2025-05-12T15:15:00-04:00 - Return just the filename for compatibility with checkpoint loader
            # Updated: 2025-05-13T16:10:33-04:00 - Return consistent tuple format with both values
            log_debug(f"EmProps_Asset_Downloader: Returning filename: {filename}")
            return (filename, filename)

        log_debug(f'EmProps_Asset_Downloader: Downloading {url} to {os.path.join(save_to, filename)}')
        self.node_id = node_id
        temp_path = save_path + '.tmp'  # Define temp_path early for error handling

        try:
            # Prepare headers for the request
            headers = {}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
                # Add headers required by Hugging Face API
                if "huggingface.co" in url:
                    headers["Accept"] = "application/json"
                    log_debug(f"Using Hugging Face API with token: {'*' * 8 + auth_token[-4:] if auth_token else 'No token'}")
            
            log_debug(f"Downloading {url} to {os.path.join(save_to, filename)}")
            log_debug(f"Request headers: {{k: '****' if 'authorization' in k.lower() else v for k, v in headers.items()}}")
            
            response = requests.get(url, headers=headers, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            
            # Ensure parent directory exists
            parent_dir = os.path.dirname(temp_path)
            if not os.path.exists(parent_dir):
                log_debug(f"Creating parent directory: {parent_dir}")
                os.makedirs(parent_dir, exist_ok=True)

            downloaded = 0
            last_progress_update = 0
            
            try:
                with open(temp_path, 'wb') as file:
                    with tqdm(total=total_size, unit='iB', unit_scale=True, desc=filename) as pbar:
                        for data in response.iter_content(chunk_size=4*1024*1024):
                            size = file.write(data)
                            downloaded += size
                            pbar.update(size)

                            if total_size > 0:
                                progress = (downloaded / total_size) * 100.0
                                if (progress - last_progress_update) > 0.2:
                                    log_debug(f"Downloading {filename}... {progress:.1f}%")
                                    last_progress_update = progress
                                if progress is not None and hasattr(self, 'node_id'):
                                    PromptServer.instance.send_sync("progress", {
                                        "node": self.node_id,
                                        "value": progress,
                                        "max": 100
                                    })
                
                # Close the file before moving it
            except Exception as e:
                log_debug(f"Error writing to temporary file: {str(e)}")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise e
                
            # Move the temporary file to the final location
            try:
                shutil.move(temp_path, save_path)
            except Exception as e:
                log_debug(f"Error moving temporary file to final location: {str(e)}")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise e
            log_debug(f"Complete! {filename} saved to {save_path}")
            
            # Added: 2025-05-13T17:15:00-04:00 - Register the model in the cache database
            try:
                file_size = os.path.getsize(save_path)
                model_cache_db.register_model(save_path, save_to, file_size)
                log_debug(f"Registered model in cache database: {save_path}")
            except Exception as e:
                log_debug(f"Error registering model in cache database: {str(e)}")
            
            # Updated: 2025-05-12T14:08:00-04:00 - Refresh model cache
            log_debug(f"Refreshing model cache for {save_to}")
            # Clear the filename cache for this folder to force a refresh
            if save_to in folder_paths.filename_list_cache:
                del folder_paths.filename_list_cache[save_to]
            
            # Force a refresh of the model list
            folder_paths.get_filename_list(save_to)
            
            # Updated: 2025-05-12T15:15:00-04:00 - Return just the filename for compatibility with checkpoint loader
            # Updated: 2025-05-13T16:10:33-04:00 - Return consistent tuple format with both values
            log_debug(f"EmProps_Asset_Downloader: Returning filename: {filename}")
            return (filename, filename)

        except Exception as e:
            log_debug(f"Error downloading file: {str(e)}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

        # Updated: 2025-05-12T16:00:00-04:00 - Return empty values on failure
        return ("", "")
