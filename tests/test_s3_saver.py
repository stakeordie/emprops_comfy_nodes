import os
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import torch
import numpy as np
from nodes.emprops_s3_saver import EmProps_S3_Saver

def create_test_image(width=512, height=512):
    """Create a test tensor image similar to what ComfyUI would provide"""
    # Create a random RGB image tensor with values between 0 and 1
    return torch.rand((height, width, 3))

def test_s3_saver():
    """Test the S3 saver functionality"""
    try:
        # Create test images
        test_images = [create_test_image(), create_test_image()]
        
        # Create instance of our S3 saver
        s3_saver = EmProps_S3_Saver()
        
        # Test metadata
        test_prompt = {
            "text": "Test prompt",
            "model": "test_model"
        }
        
        test_extra_info = {
            "workflow": "test_workflow",
            "timestamp": "2024-01-01"
        }
        
        # Try to save images
        print("Attempting to save images to S3...")
        result = s3_saver.save_to_s3(
            images=test_images,
            prefix="test/",
            filename="test_image.png",
            bucket="emprops-share-test",
            prompt=test_prompt,
            extra_pnginfo=test_extra_info
        )
        
        # Check result
        s3_url = result[0]
        if s3_url:
            print(f"Success! Images uploaded to: {s3_url}")
        else:
            print("Failed to get S3 URL")
            
    except Exception as e:
        print(f"Test failed with error: {str(e)}")

if __name__ == "__main__":
    test_s3_saver()
