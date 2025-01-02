import base64
import subprocess

def get_shell_env_var(var_name):
    """Get environment variable value directly from shell"""
    try:
        result = subprocess.run(['echo', f'${var_name}'], 
                              shell=True, 
                              capture_output=True, 
                              text=True)
        value = result.stdout.strip()
        return value if value and not value.startswith('$') else None
    except Exception as e:
        print(f"[EmProps] Error reading shell env var: {str(e)}")
        return None

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
