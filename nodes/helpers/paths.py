import os

# Base directories
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NODES_DIR = os.path.join(ROOT_DIR, 'nodes')
HELPERS_DIR = os.path.join(NODES_DIR, 'helpers')

# Metadata files
MODEL_METADATA_FILE = os.path.join(HELPERS_DIR, 'model_metadata.json')

# Folder paths dictionary for model and data storage
folder_paths = {
    "models": os.path.join(ROOT_DIR, "models"),
    "downloads": os.path.join(ROOT_DIR, "downloads"),
    "metadata": HELPERS_DIR,
}

def get_model_metadata_path():
    """Returns the path to the model metadata file."""
    return MODEL_METADATA_FILE

def ensure_dir_exists(path):
    """Ensures that the directory for the given path exists."""
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        os.makedirs(directory)

# Create necessary directories
for path in folder_paths.values():
    if not os.path.exists(path):
        os.makedirs(path)
