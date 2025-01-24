import torch
import logging

class TensorDimensionInspector:
    """
    A node that displays the dimensions of any input tensor.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "tensor": ("*",),  # Accept any type of input
            },
        }

    RETURN_TYPES = ("*",)  # Return the same type as input
    FUNCTION = "inspect_dimensions"
    CATEGORY = "EmProps/inspection"

    def inspect_dimensions(self, tensor):
        # Get the type of input
        tensor_type = type(tensor).__name__
        
        if isinstance(tensor, torch.Tensor):
            shape_info = f"Tensor Shape: {tensor.shape}, dtype: {tensor.dtype}"
        elif isinstance(tensor, (list, tuple)):
            shape_info = f"Sequence length: {len(tensor)}"
            if len(tensor) > 0 and isinstance(tensor[0], torch.Tensor):
                shape_info += f", First element shape: {tensor[0].shape}"
        else:
            shape_info = f"Non-tensor type: {tensor_type}"
        
        logging.info(f"[TensorDimensionInspector] Input type: {tensor_type}")
        logging.info(f"[TensorDimensionInspector] {shape_info}")
        
        return (tensor,)

NODE_CLASS_MAPPINGS = {
    "EmProps Tensor Inspector": TensorDimensionInspector
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EmProps Tensor Inspector": "Tensor Inspector"
}
