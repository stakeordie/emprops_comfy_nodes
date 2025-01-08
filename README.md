# EmProps ComfyUI Nodes

Custom nodes for ComfyUI developed by EmProps.

## Installation

### Option 1: Clone with Submodules (Recommended)
```bash
cd custom_nodes
git clone --recursive https://github.com/stakeordie/emprops_comfy_nodes.git
```

### Option 2: Clone and Initialize Submodules Separately
```bash
cd custom_nodes
git clone https://github.com/stakeordie/emprops_comfy_nodes.git
cd emprops_comfy_nodes
git submodule init
git submodule update
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

## Dependencies

This project uses VideoHelperSuite as a submodule. The submodule is automatically handled during installation if you follow the instructions above.

### Updating the Repository

To update both the main repository and its submodules, use:
```bash
git pull --recurse-submodules
```

Or if you've already pulled, update submodules with:
```bash
git submodule update --recursive
```

## Nodes

### EmProps_S3_Video_Combine
Combines video frames and uploads the result to S3. Inherits functionality from VideoHelperSuite's VideoCombine node.