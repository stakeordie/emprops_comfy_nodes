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
    # Updated: 2025-05-12T14:08:00-04:00 - Added STRING return type to signal download completion
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("downloaded_path",)
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
                "url": ("STRING", {"multiline": False, "default": "https://huggingface.co/ByteDance/SDXL-Lightning/resolve/main/sdxl_lightning_4step.safetensors"}),
                "save_to": (model_folders(), { "default": "checkpoints" }),
                "filename": ("STRING", {"multiline": False, "default": "sdxl_lightning_4step.safetensors"}),
            },
            "optional": {
                "token": ("STRING", { "default": "", "multiline": False, "password": True }),
            },
            "hidden": {
                "node_id": "UNIQUE_ID"
            }
        }

    def download(self, url, save_to, filename, node_id, token=""):
        log_debug(f"EmProps_Asset_Downloader.download called with url={url}, save_to={save_to}, filename={filename}, node_id={node_id}")
        
        if not url or not save_to or not filename:
            log_debug(f"EmProps_Asset_Downloader: Missing required values: url='{url}', save_to='{save_to}', filename='{filename}'")
            return ()
            
        # Updated: 2025-05-12T14:04:35-04:00 - Use folder_paths to get the correct folder path
        if save_to not in folder_paths.folder_names_and_paths:
            log_debug(f"EmProps_Asset_Downloader: Invalid save_to path: {save_to}. Must be a valid model folder.")
            return ()
            
        # Get the first folder path for the selected model type
        model_folder = folder_paths.get_folder_paths(save_to)[0]
        log_debug(f"Using model folder: {model_folder}")
        
        # Construct the full save path
        save_path = os.path.join(model_folder, filename)
        if os.path.exists(save_path):
            log_debug(f"EmProps_Asset_Downloader: File already exists: {os.path.join(save_to, filename)}")
            # Updated: 2025-05-12T14:08:00-04:00 - Return path even if file already exists
            return (os.path.join(save_to, filename),)

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

            downloaded = 0
            last_progress_update = 0
            
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

            shutil.move(temp_path, save_path)
            log_debug(f"Complete! {filename} saved to {save_path}")
            
            # Updated: 2025-05-12T14:08:00-04:00 - Refresh model cache
            log_debug(f"Refreshing model cache for {save_to}")
            # Clear the filename cache for this folder to force a refresh
            if save_to in folder_paths.filename_list_cache:
                del folder_paths.filename_list_cache[save_to]
            
            # Force a refresh of the model list
            folder_paths.get_filename_list(save_to)
            
            # Return the path to the downloaded file as a signal
            return (os.path.join(save_to, filename),)

        except Exception as e:
            log_debug(f"Error downloading file: {str(e)}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e

        # Updated: 2025-05-12T14:08:00-04:00 - Return empty path on failure
        return ("",)
