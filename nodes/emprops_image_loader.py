import os
import hashlib
import torch
import numpy as np
from PIL import Image, ImageOps, ImageSequence
import folder_paths
from ..utils import try_download_file, is_url, S3Handler, extract_metadata

class EmpropsImageLoader:
    @classmethod
    def INPUT_TYPES(s):
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        return {
            "required": {
                "source_type": (["upload", "s3", "public_download"],),
                "image": (sorted(files),),
                "s3_key": ("STRING", {"default": "", "placeholder": "S3 path"}),
                "s3_bucket": ("STRING", {"default": "emprops-share"}),
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
        else:  # s3
            s3_handler = S3Handler(kwargs.get('s3_bucket'))
            temp_dir = folder_paths.get_temp_directory()
            os.makedirs(temp_dir, exist_ok=True)
            image_name = os.path.basename(kwargs['s3_key'])
            image_path = os.path.join(temp_dir, image_name)
            print(f"[EmProps] Downloading from S3: {kwargs['s3_bucket']}/{kwargs['s3_key']}", flush=True)
            success, error = s3_handler.download_file(kwargs['s3_key'], image_path)
            if not success:
                print(f"[EmProps] Error: Failed to download image from S3: {error}", flush=True)
                raise Exception(f"Failed to download image from S3: {error}")

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
        return kwargs.get('s3_key', '') + kwargs.get('s3_bucket', '')

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
        else:  # s3
            if not kwargs.get('s3_key'):
                return "S3 key is required when using S3 source"
        return True
