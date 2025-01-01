import os
import json
import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import io

class ImageSaveHelper:
    """
    Helper class for processing and saving images in a format compatible with ComfyUI's default implementation.
    This class handles image conversion, metadata, and compression in a way that matches the default SaveImage node.
    """
    
    def __init__(self, compress_level=4):
        """
        Initialize the helper with compression settings.
        
        Args:
            compress_level (int): PNG compression level (0-9), default matches ComfyUI's default
        """
        self.compress_level = compress_level

    def process_images(self, images, prompt=None, extra_pnginfo=None):
        """
        Process a batch of images and convert them to bytes with metadata.
        
        Args:
            images: List of tensor images from ComfyUI
            prompt: Optional prompt information to include in metadata
            extra_pnginfo: Optional additional metadata
            
        Returns:
            List of tuples (bytes_io, metadata) for each processed image
        """
        results = []
        
        for image in images:
            # Convert tensor to numpy array and scale to 0-255 range
            i = 255. * image.cpu().numpy()
            # Clip values and convert to uint8
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            
            # Create metadata if enabled
            metadata = self._create_metadata(prompt, extra_pnginfo)
            
            # Convert to bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG', pnginfo=metadata, compress_level=self.compress_level)
            img_bytes.seek(0)
            
            results.append((img_bytes, metadata))
        
        return results
    
    def _create_metadata(self, prompt=None, extra_pnginfo=None):
        """
        Create PNG metadata matching ComfyUI's format.
        
        Args:
            prompt: Optional prompt information
            extra_pnginfo: Optional additional metadata
            
        Returns:
            PngInfo object with metadata
        """
        metadata = PngInfo()
        
        if prompt is not None:
            metadata.add_text("prompt", json.dumps(prompt))
            
        if extra_pnginfo is not None:
            for key in extra_pnginfo:
                metadata.add_text(key, json.dumps(extra_pnginfo[key]))
                
        return metadata
    
    def format_ui_response(self, filenames, subfolder="", type="output"):
        """
        Format the response for ComfyUI's UI in the same way as the default SaveImage node.
        
        Args:
            filenames: List of saved filenames
            subfolder: Optional subfolder path
            type: Type of output (default: "output")
            
        Returns:
            Dictionary formatted for ComfyUI UI
        """
        results = []
        for filename in filenames:
            results.append({
                "filename": filename,
                "subfolder": subfolder,
                "type": type
            })
        
        return {"ui": {"images": results}}

    def get_file_extension(self):
        """
        Get the default file extension for saved images.
        
        Returns:
            String file extension including the dot
        """
        return ".png"
