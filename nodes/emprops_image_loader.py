import os
import hashlib
import torch
import numpy as np
from PIL import Image, ImageOps, ImageSequence
import folder_paths
# 2025-04-27 20:59: Updated imports to support multiple cloud providers
from ..utils import try_download_file, is_url, S3Handler, GCSHandler, AzureHandler, extract_metadata, GCS_AVAILABLE, AZURE_AVAILABLE

class EmpropsImageLoader:
    def __init__(self):
        # 2025-04-27 21:00: Get default cloud provider from environment
        # Updated: 2025-05-07T15:40:00-04:00 - Added validation for CLOUD_PROVIDER
        self.default_provider = os.getenv('CLOUD_PROVIDER', 'aws').lower()
        if self.default_provider not in ['aws', 'google', 'azure']:
            print(f"[EmProps] Warning: Unknown CLOUD_PROVIDER value: {self.default_provider}, defaulting to 'aws'")
            self.default_provider = 'aws'
            
        self.default_bucket = "emprops-share"
        
        # Check if test mode is enabled
        self.test_mode = os.getenv('STORAGE_TEST_MODE', 'false').lower() == 'true'
        if self.test_mode:
            self.default_bucket = "emprops-share-test"
    
    @classmethod
    def INPUT_TYPES(s):
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        
        # 2025-04-27 21:00: Determine available providers based on imports
        providers = ["aws"]
        if GCS_AVAILABLE:
            providers.append("google")
        if AZURE_AVAILABLE:
            providers.append("azure")
            
        # Get default provider from environment
        default_provider = os.getenv('CLOUD_PROVIDER', 'aws')
        if default_provider not in providers:
            default_provider = providers[0]
        
        return {
            "required": {
                "source_type": (["upload", "cloud", "public_download"],),
                "image": (sorted(files),),
                "provider": (providers, {"default": default_provider}),
                "cloud_key": ("STRING", {"default": "", "placeholder": "Path in cloud storage"}),
                "bucket": ("STRING", {"default": "emprops-share"}),
                "url": ("STRING", {"default": "", "placeholder": "https://example.com/image.jpg"}),
            }
        }

    CATEGORY = "image"
    RETURN_TYPES = ("IMAGE", "MASK", "JSON", "METADATA_RAW")
    RETURN_NAMES = ("image", "mask", "prompt", "Metadata RAW")
    FUNCTION = "load_image"

    def load_image(self, **kwargs):
        print(f"[EmProps] Loading image from source type: {kwargs['source_type']}", flush=True)
        
        if kwargs['source_type'] == 'upload':
            image_path = folder_paths.get_annotated_filepath(kwargs['image'])
            print(f"[EmProps] Loading local file: {image_path}", flush=True)
        elif kwargs['source_type'] == 'public_download':
            print(f"[EmProps] Downloading from URL: {kwargs['url']}", flush=True)
            image_path = try_download_file(kwargs['url'])
            if not image_path:
                print(f"[EmProps] Error: Failed to download image from URL: {kwargs['url']}", flush=True)
                raise Exception(f"Failed to download image from URL: {kwargs['url']}")
        else:  # cloud
            # 2025-04-27 21:00: Handle multiple cloud providers
            provider = kwargs.get('provider', self.default_provider)
            bucket = kwargs.get('bucket', self.default_bucket)
            cloud_key = kwargs.get('cloud_key', '')
            
            if not cloud_key:
                print(f"[EmProps] Error: No cloud key provided", flush=True)
                raise Exception("No cloud key provided")
                
            temp_dir = folder_paths.get_temp_directory()
            os.makedirs(temp_dir, exist_ok=True)
            image_name = os.path.basename(cloud_key)
            image_path = os.path.join(temp_dir, image_name)
            
            # Select the appropriate cloud handler based on provider
            if provider == 'aws':
                print(f"[EmProps] Downloading from AWS S3: {bucket}/{cloud_key}", flush=True)
                handler = S3Handler(bucket)
            elif provider == 'google':
                print(f"[EmProps] Downloading from Google Cloud Storage: {bucket}/{cloud_key}", flush=True)
                handler = GCSHandler(bucket)
            elif provider == 'azure':
                # Updated: 2025-05-07T15:40:30-04:00 - Added debug info for Azure credentials
                print(f"[EmProps] Downloading from Azure Blob Storage: {bucket}/{cloud_key}", flush=True)
                
                # Debug info for Azure credentials
                account_name = os.getenv('STORAGE_ACCOUNT_NAME') or os.getenv('AZURE_STORAGE_ACCOUNT')
                if account_name:
                    print(f"[EmProps] Using Azure Storage Account: {account_name}")
                else:
                    print(f"[EmProps] Warning: No Azure Storage Account found in environment variables")
                    
                handler = AzureHandler(bucket)
            else:
                print(f"[EmProps] Error: Unsupported cloud provider: {provider}", flush=True)
                raise Exception(f"Unsupported cloud provider: {provider}")
            
            # Download the file
            success, error = handler.download_file(cloud_key, image_path)
            if not success:
                print(f"[EmProps] Error: Failed to download image from {provider}: {error}", flush=True)
                raise Exception(f"Failed to download image from {provider}: {error}")

        print(f"[EmProps] Opening image: {image_path}", flush=True)


        img = Image.open(image_path)
        img = ImageOps.exif_transpose(img)

        #metadata start
        prompt, metadata = extract_metadata(img)
        #metadata end

        output_images = []
        output_masks = []
        w, h = None, None

        excluded_formats = ['MPO']
        print(f"[EmProps] Processing image format: {img.format}", flush=True)

        for i in ImageSequence.Iterator(img):
            i = ImageOps.exif_transpose(i)

            if i.mode == 'I':
                print(f"[EmProps] Converting mode 'I' image", flush=True)
                i = i.point(lambda i: i * (1 / 255))
            image = i.convert("RGB")

            if len(output_images) == 0:
                w = image.size[0]
                h = image.size[1]
                print(f"[EmProps] Image dimensions: {w}x{h}", flush=True)

            if image.size[0] != w or image.size[1] != h:
                print(f"[EmProps] Skipping frame with mismatched dimensions: {image.size[0]}x{image.size[1]}", flush=True)
                continue

            image = np.array(image).astype(np.float32) / 255.0
            image = torch.from_numpy(image)[None,]
            if 'A' in i.getbands():
                print("[EmProps] Processing alpha channel", flush=True)
                mask = np.array(i.getchannel('A')).astype(np.float32) / 255.0
                mask = 1. - torch.from_numpy(mask)
            else:
                print("[EmProps] No alpha channel found, creating empty mask", flush=True)
                mask = torch.zeros((64,64), dtype=torch.float32, device="cpu")
            output_images.append(image)
            output_masks.append(mask.unsqueeze(0))

        if len(output_images) > 1 and img.format not in excluded_formats:
            print(f"[EmProps] Note: Using metadata from first frame for all {len(output_images)} frames", flush=True)
            print(f"[EmProps] Combining {len(output_images)} frames", flush=True)
            output_image = torch.cat(output_images, dim=0)
            output_mask = torch.cat(output_masks, dim=0)
        else:
            print("[EmProps] Using single frame", flush=True)
            output_image = output_images[0]
            output_mask = output_masks[0]

        print("[EmProps] Image loading complete", flush=True)
        return (output_image, output_mask, prompt, metadata)

    @classmethod
    def IS_CHANGED(s, **kwargs):
        if kwargs.get('source_type') == 'upload':
            image_path = folder_paths.get_annotated_filepath(kwargs['image'])
            m = hashlib.sha256()
            with open(image_path, 'rb') as f:
                m.update(f.read())
            return m.digest().hex()
        elif kwargs.get('source_type') == 'public_download':
            return kwargs.get('url', '')
        # 2025-04-27 21:00: Updated for cloud storage
        return kwargs.get('cloud_key', '') + kwargs.get('bucket', '') + kwargs.get('provider', 'aws')

    @classmethod
    def VALIDATE_INPUTS(s, **kwargs):
        if kwargs.get('source_type') == 'upload':
            if not folder_paths.exists_annotated_filepath(kwargs['image']):
                return "Invalid image file: {}".format(kwargs['image'])
        elif kwargs.get('source_type') == 'public_download':
            if not kwargs.get('url'):
                return "URL is required for public download"
            if not is_url(kwargs.get('url')):
                return "Invalid URL format"
        else:  # cloud
            # 2025-04-27 21:00: Updated for cloud storage
            if not kwargs.get('cloud_key'):
                return "Cloud key is required when using cloud source"
            
            # Validate provider
            provider = kwargs.get('provider', 'aws')
            if provider == 'google' and not GCS_AVAILABLE:
                return "Google Cloud Storage is not available. Install with 'pip install google-cloud-storage'"
            elif provider == 'azure' and not AZURE_AVAILABLE:
                return "Azure Blob Storage is not available. Install with 'pip install azure-storage-blob'"
        return True