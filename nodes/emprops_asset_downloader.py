import os
# mypy: ignore-errors
import requests  # type: ignore
import shutil
import hashlib
import time
import traceback
from tqdm import tqdm
from server import PromptServer
import folder_paths  # Updated: 2025-05-12T14:04:35-04:00 - Use folder_paths module instead of direct import
# Added: 2025-05-13T17:15:00-04:00 - Import model cache database
from ..db.model_cache import model_cache_db

# Added: 2025-05-12T13:52:12-04:00 - Asset Downloader implementation
def log_debug(message):
    """Enhanced logging function with timestamp and stack info"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    caller = traceback.extract_stack()[-2]
    file = os.path.basename(caller.filename)
    line = caller.lineno
    print(f"[EmProps DEBUG {timestamp}] [{file}:{line}] {message}", flush=True)

def model_folders():
    # Updated: 2025-05-12T14:04:35-04:00 - Get folder names from folder_paths
    return sorted(list(folder_paths.folder_names_and_paths.keys()))

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
            },
            "optional": {
                "token": ("STRING", { "default": "", "multiline": False, "password": True, "widget": True }),
                # Added: 2025-05-12T14:42:00-04:00 - Test mode checkbox for creating a copy instead of downloading
                "test_with_copy": ("BOOLEAN", {"default": False, "label": "Test with copy"}),
                # Added: 2025-05-12T14:42:00-04:00 - Source filename for test mode
                "source_filename": ("STRING", {"default": "", "multiline": False, "placeholder": "Leave empty to use filename"}),
            },
            "hidden": {
                "node_id": "UNIQUE_ID"
            }
        }

    def download(self, url, save_to, filename, node_id, token="", test_with_copy=False, source_filename=""):
        log_debug(f"EmProps_Asset_Downloader.download called with url={url}, save_to={save_to}, filename={filename}, node_id={node_id}")
        
        if not url or not save_to or not filename:
            log_debug(f"EmProps_Asset_Downloader: Missing required values: url='{url}', save_to='{save_to}', filename='{filename}'")
            # Updated: 2025-05-13T16:10:33-04:00 - Return consistent tuple format
            return ("", "")
            
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
                log_debug(f"Error copying file: {str(e)}")
                if os.path.exists(save_path):
                    os.remove(save_path)
                # Updated: 2025-05-13T16:10:33-04:00 - Return consistent tuple format
                return (f"Error: {str(e)}", "")
        
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

        log_debug(f'EmProps_Asset_Downloader: Downloading {url} to {os.path.join(save_to, filename)} {" with token" if token else ""}')
        self.node_id = node_id

        # if token starts with `$` replace with environment variable if exists
        if token.startswith("$"):
            env_value = os.getenv(token[1:])
            token = env_value if env_value is not None else token

        headers={"Authorization": f"Bearer {token}"} if token else None

        log_debug(f"Downloading {url} to {os.path.join(save_to, filename)} {'with Authorization header' if headers else ''}")
        try:
            response = requests.get(url, headers=headers, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            temp_path = save_path + '.tmp'
            
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
