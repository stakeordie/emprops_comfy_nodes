import os
import json
import piexif
from PIL import Image
from PIL.PngImagePlugin import PngImageFile
from PIL.JpegImagePlugin import JpegImageFile

def extract_metadata(img):
    """Extract metadata from a PIL Image object."""
    prompt = {}
    metadata = {
        "format": img.format,
        "mode": img.mode,
        "size": img.size,
        "info": img.info
    }
    
    # Extract metadata based on image format
    if isinstance(img, (PngImageFile, JpegImageFile)):
        try:
            if "parameters" in img.info:
                prompt = img.info["parameters"]
                metadata["parameters"] = prompt
            elif "Comment" in img.info:
                prompt = img.info["Comment"]
                try:
                    prompt = json.loads(prompt)
                except json.JSONDecodeError:
                    pass
                metadata["Comment"] = prompt
        except Exception as e:
            print(f"[EmProps] Error extracting PNG/JPEG metadata: {str(e)}", flush=True)
    
    # Try to extract EXIF data if we have a path
    if hasattr(img, 'filename') and img.filename:
        try:
            if img.format in ['JPEG', 'WEBP']:
                exif_data = piexif.load(img.filename)
                if '0th' in exif_data:
                    # Extract prompt from Make field
                    if 271 in exif_data['0th']:
                        prompt_data = exif_data['0th'][271].decode('utf-8')
                        prompt_data = prompt_data.replace('Prompt:', '', 1)
                        try:
                            prompt.update(json.loads(prompt_data))
                        except json.JSONDecodeError:
                            prompt['text'] = prompt_data
                    
                    # Extract workflow from Model field
                    if 270 in exif_data['0th']:
                        workflow_data = exif_data['0th'][270].decode('utf-8')
                        workflow_data = workflow_data.replace('Workflow:', '', 1)
                        try:
                            metadata['workflow'] = json.loads(workflow_data)
                        except json.JSONDecodeError:
                            metadata['workflow'] = workflow_data
                
                metadata['exif'] = exif_data
        except Exception as e:
            print(f"[EmProps] Error extracting EXIF data: {str(e)}", flush=True)
    
    return prompt, metadata