import base64

def unescape_env_value(encoded_value):
    """
    Unescapes a base64 encoded environment variable value.
    Also handles _SLASH_ replacement in the raw string.
    
    Args:
        encoded_value (str): The potentially encoded string
        
    Returns:
        str: The decoded string, or empty string if decoding fails
    """
    try:
        if not encoded_value:
            return ''
            
        # First replace _SLASH_ with actual forward slashes
        decoded_value = encoded_value.replace('_SLASH_', '/')
        
        # Return the processed string without trying base64 decode
        return decoded_value
        
    except Exception as e:
        print(f"[EmProps] Error processing environment variable: {str(e)}")
        return ''
