import os
import sys
import folder_paths
import traceback
import time

# Added: 2025-04-20T19:47:26-04:00 - Enhanced logging for debugging
def log_debug(message):
    """Enhanced logging function with timestamp and stack info"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    caller = traceback.extract_stack()[-2]
    file = os.path.basename(caller.filename)
    line = caller.lineno
    print(f"[EmProps DEBUG {timestamp}] [{file}:{line}] {message}", flush=True)
# Added: 2025-04-20T21:57:24-04:00 - Removed model downloader nodes
from .nodes.emprops_lora_loader import EmProps_Lora_Loader
from .nodes.emprops_cloud_storage_saver import EmpropsCloudStorageSaver
from .nodes.emprops_image_loader import EmpropsImageLoader
from .nodes.emprops_text_s3_saver import EmProps_Text_S3_Saver
from .nodes.emprops_text_cloud_storage_saver import EmpropsTextCloudStorageSaver, EmProps_Text_S3_Saver as EmProps_Text_S3_Saver_New  # Added: 2025-04-24T15:20:02-04:00
from .nodes.emprops_asset_downloader import EmProps_Asset_Downloader  # Added: 2025-05-12T13:52:12-04:00
from .nodes.emprops_checkpoint_loader import EmProps_Checkpoint_Loader  # Added: 2025-05-13T09:42:00-04:00

log_debug("Starting EmProps initialization")
log_debug(f"Python path: {sys.path}")
log_debug(f"Current working directory: {os.getcwd()}")
log_debug(f"Module directory: {os.path.dirname(os.path.abspath(__file__))}")

log_debug("Loading EmProps nodes")
log_debug(f"Current directory: {os.path.dirname(os.path.abspath(__file__))}")

# Log all available modules
log_debug(f"Available modules in sys.modules: {[m for m in sys.modules.keys() if 'emprops' in m.lower()]}")

# Debug: Print node class details
# Updated: 2025-04-20T19:47:26-04:00 - Enhanced logging for debugging
try:
    for name in ['EmProps_Lora_Loader', 'EmpropsCloudStorageSaver', 'EmpropsImageLoader', 'EmpropsModelDownloader']:
        try:
            cls = globals()[name]
            log_debug(f"Node class {name} found in globals()")
            log_debug(f"  - Type: {type(cls)}")
            log_debug(f"  - Dir: {dir(cls)}")
            log_debug(f"  - RETURN_TYPES: {getattr(cls, 'RETURN_TYPES', None)}")
            log_debug(f"  - INPUT_TYPES: {getattr(cls, 'INPUT_TYPES', None) if hasattr(cls, 'INPUT_TYPES') else 'No INPUT_TYPES'}")
            
            # Check if the class has the required methods
            if hasattr(cls, 'INPUT_TYPES') and callable(getattr(cls, 'INPUT_TYPES')):
                try:
                    input_types = cls.INPUT_TYPES()
                    log_debug(f"  - INPUT_TYPES() result: {input_types}")
                except Exception as e:
                    log_debug(f"  - ERROR calling INPUT_TYPES(): {str(e)}\n{traceback.format_exc()}")
        except KeyError:
            log_debug(f"Node class {name} NOT found in globals()")
        except Exception as e:
            log_debug(f"Error inspecting {name}: {str(e)}\n{traceback.format_exc()}")
except Exception as e:
    log_debug(f"Error in debug loop: {str(e)}\n{traceback.format_exc()}")

# Updated: 2025-04-20T19:47:26-04:00 - Added enhanced logging
log_debug("Creating NODE_CLASS_MAPPINGS dictionary")
try:
    NODE_CLASS_MAPPINGS = {
    # Added: 2025-04-20T21:57:24-04:00 - Removed model downloader nodes
    "EmProps_Lora_Loader": EmProps_Lora_Loader,
    "EmProps_Cloud_Storage_Saver": EmpropsCloudStorageSaver,
    "EmProps_S3_Saver": EmpropsCloudStorageSaver,  # Backward compatibility
    "EmProps_Image_Loader": EmpropsImageLoader,
    "EmProps_Text_S3_Saver": EmProps_Text_S3_Saver_New,  # Updated: 2025-04-24T15:20:02-04:00
    "EmProps_Text_Cloud_Storage_Saver": EmpropsTextCloudStorageSaver,  # Added: 2025-04-24T15:20:02-04:00
    "EmProps_Asset_Downloader": EmProps_Asset_Downloader,  # Added: 2025-05-12T13:52:12-04:00
    "EmProps_Checkpoint_Loader": EmProps_Checkpoint_Loader,  # Added: 2025-05-13T09:42:00-04:00
}
    log_debug(f"NODE_CLASS_MAPPINGS created successfully with {len(NODE_CLASS_MAPPINGS)} entries")
    for node_name, node_class in NODE_CLASS_MAPPINGS.items():
        log_debug(f"Registered node: {node_name} -> {node_class.__name__ if hasattr(node_class, '__name__') else str(node_class)}")
except Exception as e:
    log_debug(f"Error creating NODE_CLASS_MAPPINGS: {str(e)}\n{traceback.format_exc()}")

try:
    log_debug("Creating NODE_DISPLAY_NAME_MAPPINGS dictionary")
    NODE_DISPLAY_NAME_MAPPINGS = {
    # Added: 2025-04-20T21:57:24-04:00 - Removed model downloader nodes
    "EmProps_Lora_Loader": "EmProps LoRA Loader",
    "EmProps_Cloud_Storage_Saver": "EmProps Cloud Storage Saver",
    "EmProps_S3_Saver": "EmProps S3 Saver (Legacy)",  # Backward compatibility
    "EmProps_Image_Loader": "EmProps Image Loader",
    "EmProps_Text_S3_Saver": "EmProps Text S3 Saver (Legacy)",  # Updated: 2025-04-24T15:20:02-04:00
    "EmProps_Text_Cloud_Storage_Saver": "EmProps Text Cloud Storage Saver",  # Added: 2025-04-24T15:20:02-04:00
    "EmProps_Asset_Downloader": "EmProps Asset Downloader",  # Added: 2025-05-12T13:52:12-04:00
    "EmProps_Checkpoint_Loader": "EmProps Checkpoint Loader",  # Added: 2025-05-13T09:42:00-04:00
}
    log_debug(f"NODE_DISPLAY_NAME_MAPPINGS created successfully with {len(NODE_DISPLAY_NAME_MAPPINGS)} entries")
except Exception as e:
    log_debug(f"Error creating NODE_DISPLAY_NAME_MAPPINGS: {str(e)}\n{traceback.format_exc()}")

# Added: 2025-05-12T13:52:12-04:00 - Added WEB_DIRECTORY for asset downloader JS
WEB_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)), "js")

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']
