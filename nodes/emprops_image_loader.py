import os
import hashlib
import torch
import numpy as np
from PIL import Image, ImageOps, ImageSequence
import folder_paths
from ..utils import try_download_file, is_url, S3Handler

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
    RETURN_TYPES = ("IMAGE", "MASK")
    FUNCTION = "load_image"
    OUTPUT_NODE = True

    def load_image(self, **kwargs):
        if kwargs['source_type'] == 'upload':
            image_path = folder_paths.get_annotated_filepath(kwargs['image'])
        elif kwargs['source_type'] == 'public_download':
            image_path = try_download_file(kwargs['url'])
            if not image_path:
                raise Exception(f"Failed to download image from URL: {kwargs['url']}")
        else:  # s3
            s3_handler = S3Handler(kwargs.get('s3_bucket'))
            temp_dir = folder_paths.get_temp_directory()
            os.makedirs(temp_dir, exist_ok=True)
            image_name = os.path.basename(kwargs['s3_key'])
            image_path = os.path.join(temp_dir, image_name)
            success, error = s3_handler.download_file(kwargs['s3_key'], image_path)
            if not success:
                raise Exception(f"Failed to download image from S3: {error}")

        img = Image.open(image_path)
        img = ImageOps.exif_transpose(img)

        output_images = []
        output_masks = []
        w, h = None, None

        excluded_formats = ['MPO']

        for i in ImageSequence.Iterator(img):
            i = ImageOps.exif_transpose(i)

            if i.mode == 'I':
                i = i.point(lambda i: i * (1 / 255))
            image = i.convert("RGB")

            if len(output_images) == 0:
                w = image.size[0]
                h = image.size[1]

            if image.size[0] != w or image.size[1] != h:
                continue

            image = np.array(image).astype(np.float32) / 255.0
            image = torch.from_numpy(image)[None,]
            if 'A' in i.getbands():
                mask = np.array(i.getchannel('A')).astype(np.float32) / 255.0
                mask = 1. - torch.from_numpy(mask)
            else:
                mask = torch.zeros((64,64), dtype=torch.float32, device="cpu")
            output_images.append(image)
            output_masks.append(mask.unsqueeze(0))

        if len(output_images) > 1 and img.format not in excluded_formats:
            output_image = torch.cat(output_images, dim=0)
            output_mask = torch.cat(output_masks, dim=0)
        else:
            output_image = output_images[0]
            output_mask = output_masks[0]

        # Add preview info
        results = []
        results.append({
            "filename": os.path.basename(image_path),
            "subfolder": os.path.dirname(image_path),
            "type": "input"
        })

        return (output_image, output_mask, {"images": results})

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
