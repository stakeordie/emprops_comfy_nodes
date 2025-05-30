# Adding New Nodes to EmProps ComfyUI Extension

This document provides a step-by-step guide for adding new nodes to the EmProps ComfyUI extension. Following these steps ensures that new nodes are properly registered and visible in the ComfyUI interface.

## [2025-05-30T10:30:57-04:00] Complete Node Implementation Checklist

### 1. Create the Node File

Create a new Python file in the `nodes/` directory with the following naming convention:
```
emprops_<node_type>_<node_function>.py
```

Example: `emprops_dualclip_loader.py`

### 2. Implement the Node Class

Implement your node class with the following components:
- Class name should follow the pattern `EmProps_<NodeType>_<NodeFunction>`
- Include proper docstrings explaining the node's purpose
- Implement the required ComfyUI methods:
  - `INPUT_TYPES` (class method)
  - `RETURN_TYPES` and `RETURN_NAMES`
  - Main function (e.g., `load_model`, `process`, etc.)
  - Set `CATEGORY = "EmProps"`
  - Set `OUTPUT_NODE` if appropriate

### 3. Add NODE_CLASS_MAPPINGS and NODE_DISPLAY_NAME_MAPPINGS

At the end of your node file, include:

```python
# Node class mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "EmProps_YourNode_Name": EmProps_YourNode_Name,
}

# Human-readable names for the UI
NODE_DISPLAY_NAME_MAPPINGS = {
    "EmProps_YourNode_Name": "EmProps Your Node Name",
}
```

### 4. Update the Main __init__.py File

In the main `__init__.py` file, make the following changes:

1. Add an import for your new node:
```python
from .nodes.emprops_yournode_name import EmProps_YourNode_Name  # Added: <timestamp>
```

2. Add your node to the NODE_CLASS_MAPPINGS dictionary:
```python
"EmProps_YourNode_Name": EmProps_YourNode_Name,  # Added: <timestamp>
```

3. Add your node to the NODE_DISPLAY_NAME_MAPPINGS dictionary:
```python
"EmProps_YourNode_Name": "EmProps Your Node Name",  # Added: <timestamp>
```

### 5. Update the JavaScript File (if needed)

If your node needs progress indicators or other UI enhancements:

1. Open `js/empropsAssetDownloader.js`
2. Add your node to the `nodeTypes` array:
```javascript
const nodeTypes = [
    // Existing nodes...
    "EmProps_YourNode_Name"
]
```

### 6. Update the Changelog

Add an entry to `CHANGELOG.md` describing your new node:
```markdown
## YYYY-MM-DD

### Added
- Added new node EmProps_YourNode_Name (YYYY-MM-DDThh:mm:ss-04:00)
  - Brief description of what the node does
  - Any special features or capabilities
```

### 7. Commit Your Changes

Commit all the changes to the repository:
```bash
git add nodes/emprops_yournode_name.py __init__.py js/empropsAssetDownloader.js CHANGELOG.md
git commit -m "[YYYY-MM-DDThh:mm:ss-04:00] Added EmProps_YourNode_Name"
```

### 8. Restart ComfyUI

ComfyUI needs to be restarted to pick up the new nodes. Stop and start the ComfyUI server.

## Common Issues and Troubleshooting

- **Node not appearing in ComfyUI**: Make sure the node is properly registered in both the node file and the main `__init__.py` file.
- **Import errors**: Check for syntax errors in your node file.
- **UI not updating**: Clear your browser cache or try opening ComfyUI in a private/incognito window.
- **Progress indicators not working**: Ensure your node is added to the `nodeTypes` array in the JavaScript file.

## Example: Adding a New Loader Node

Here's a simplified example of adding a new loader node:

1. Create `nodes/emprops_example_loader.py`:
```python
import os
import time
import traceback
from server import PromptServer
import folder_paths

def log_debug(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    caller = traceback.extract_stack()[-2]
    file = os.path.basename(caller.filename)
    line = caller.lineno
    print(f"[EmProps DEBUG {timestamp}] [{file}:{line}] {message}", flush=True)

class EmProps_Example_Loader:
    RETURN_TYPES = ("EXAMPLE",)
    RETURN_NAMES = ("EXAMPLE",)
    OUTPUT_NODE = True
    FUNCTION = "load_example"
    CATEGORY = "EmProps"
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "example_name": ("STRING", {"multiline": False, "default": ""}),
            },
            "hidden": {
                "node_id": "UNIQUE_ID"
            }
        }

    def load_example(self, example_name, node_id=None):
        # Implementation here
        return (example,)

# Node class mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "EmProps_Example_Loader": EmProps_Example_Loader,
}

# Human-readable names for the UI
NODE_DISPLAY_NAME_MAPPINGS = {
    "EmProps_Example_Loader": "EmProps Example Loader",
}
```

2. Update `__init__.py`:
```python
from .nodes.emprops_example_loader import EmProps_Example_Loader  # Added: timestamp

# In NODE_CLASS_MAPPINGS:
"EmProps_Example_Loader": EmProps_Example_Loader,  # Added: timestamp

# In NODE_DISPLAY_NAME_MAPPINGS:
"EmProps_Example_Loader": "EmProps Example Loader",  # Added: timestamp
```

3. Update `js/empropsAssetDownloader.js`:
```javascript
const nodeTypes = [
    // Existing nodes...
    "EmProps_Example_Loader"
]
```

Following these steps consistently will ensure that all new nodes are properly implemented and visible in the ComfyUI interface.
