import base64

def unescape_env_value(encoded_value):
    """
    Unescapes a base64 encoded environment variable value.
    
    Args:
        encoded_value (str): The base64 encoded string
        
    Returns:
        str: The decoded string, or empty string if decoding fails
    """
    try:
        if not encoded_value:
            return ''
        return base64.b64decode(encoded_value).decode('utf-8')
    except Exception as e:
        print(f"[EmProps] Error decoding environment variable: {str(e)}")
        return ''
