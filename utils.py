import base64
import os
import urllib.parse
import requests
import folder_paths
import boto3
from typing import Optional, Tuple, List
from dotenv import load_dotenv

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

def is_url(string):
    """Check if a string is a valid URL."""
    try:
        result = urllib.parse.urlparse(string)
        return all([result.scheme, result.netloc])
    except:
        return False

def try_download_file(url, chunk_size=8192):
    """
    Download a file from a URL to a temporary directory.
    
    Args:
        url (str): URL to download from
        chunk_size (int): Size of chunks to download
        
    Returns:
        str: Path to downloaded file, or None if download failed
    """
    try:
        temp_dir = folder_paths.get_temp_directory()
        os.makedirs(temp_dir, exist_ok=True)
        
        # Extract filename from URL or use a default
        parsed_url = urllib.parse.urlparse(url)
        filename = os.path.basename(parsed_url.path)
        if not filename:
            filename = 'downloaded_file'
            
        output_path = os.path.join(temp_dir, filename)
        
        # Download the file in chunks
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    
        return output_path
    except Exception as e:
        print(f"[EmProps] Error downloading file: {str(e)}")
        return None

def _process_secret_key(secret_key: str) -> str:
    """Process AWS secret key by replacing _SLASH_ with /"""
    return secret_key.replace('_SLASH_', '/') if secret_key else ''

class S3Handler:
    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = bucket_name or "emprops-share"
        
        # First try system environment
        access_key = os.getenv('AWS_ACCESS_KEY_ID')
        secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        region = os.getenv('AWS_DEFAULT_REGION')

        # Try encoded secret key if regular one not found
        if not secret_key:
            secret_key = os.getenv('AWS_SECRET_ACCESS_KEY_ENCODED')
            if secret_key:
                secret_key = _process_secret_key(secret_key)

        # If not found, try .env and .env.local files
        if not access_key or not secret_key or not region:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Try .env first
            env_path = os.path.join(current_dir, '.env')
            if os.path.exists(env_path):
                load_dotenv(env_path)
                secret_key = secret_key or _process_secret_key(os.getenv('AWS_SECRET_ACCESS_KEY_ENCODED', ''))
                if not secret_key:
                    secret_key = secret_key or os.getenv('AWS_SECRET_ACCESS_KEY', '')
                access_key = access_key or os.getenv('AWS_ACCESS_KEY_ID', '')
                region = region or os.getenv('AWS_DEFAULT_REGION', '')
            
            # If still not found, try .env.local
            if not access_key or not secret_key or not region:
                env_local_path = os.path.join(current_dir, '.env.local')
                if os.path.exists(env_local_path):
                    load_dotenv(env_local_path)
                    secret_key = secret_key or _process_secret_key(os.getenv('AWS_SECRET_ACCESS_KEY_ENCODED', ''))
                    if not secret_key:
                        secret_key = secret_key or os.getenv('AWS_SECRET_ACCESS_KEY', '')
                    access_key = access_key or os.getenv('AWS_ACCESS_KEY_ID', '')
                    region = region or os.getenv('AWS_DEFAULT_REGION', '')
        
        # Set default region if still not set
        region = region or 'us-east-1'
        
        if not all([access_key, secret_key]):
            missing = []
            if not access_key: missing.append('AWS_ACCESS_KEY_ID')
            if not secret_key: missing.append('AWS_SECRET_ACCESS_KEY')
            raise ValueError(f"Missing required AWS environment variables: {', '.join(missing)}")
        
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )

    def verify_s3_upload(self, bucket: str, key: str, max_attempts: int = 5, delay: float = 1) -> bool:
        """Verify that a file exists in S3 by checking with head_object"""
        import time
        
        for attempt in range(max_attempts):
            try:
                response = self.s3_client.head_object(Bucket=bucket, Key=key)
                return True
            except Exception as e:
                if attempt < max_attempts - 1:
                    last_error = e
                    time.sleep(delay)
                else:
                    raise e
        return False

    def upload_file(self, file_path: str, s3_prefix: Optional[str] = None, index: Optional[int] = None, target_name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Upload a file to S3 bucket
        
        Args:
            file_path: Local path to the file
            s3_prefix: Optional prefix (folder) in S3 bucket
            index: Optional index for multiple files
            target_name: Optional target filename to use instead of the source filename
            
        Returns:
            Tuple[bool, str]: (success, error_message)
        """
        try:
            if not os.path.exists(file_path):
                return False, f"File not found: {file_path}"
            
            # Determine target filename
            if target_name:
                s3_key = target_name
            else:
                filename = os.path.basename(file_path)
                if index is not None:
                    name, ext = os.path.splitext(filename)
                    filename = f"{name}_{index}{ext}"
                s3_key = filename
            
            # Add prefix if provided
            if s3_prefix:
                s3_key = f"{s3_prefix.rstrip('/')}/{s3_key}"
            
            # Upload file
            self.s3_client.upload_file(file_path, self.bucket_name, s3_key)
            
            # Verify upload
            if not self.verify_s3_upload(self.bucket_name, s3_key):
                return False, "Failed to verify S3 upload"
            
            return True, ""
            
        except Exception as e:
            return False, str(e)

    def download_file(self, s3_key: str, local_path: str) -> Tuple[bool, str]:
        """
        Download a file from S3 bucket
        
        Args:
            s3_key: S3 object key
            local_path: Local path to save the file
            
        Returns:
            Tuple[bool, str]: (success, error_message)
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Download file
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            
            if not os.path.exists(local_path):
                return False, "Failed to download file"
                
            return True, ""
            
        except Exception as e:
            return False, str(e)

    def list_files(self, prefix: Optional[str] = None) -> List[str]:
        """
        List files in S3 bucket with optional prefix
        
        Args:
            prefix: Optional prefix to filter files
            
        Returns:
            List[str]: List of S3 keys
        """
        try:
            kwargs = {'Bucket': self.bucket_name}
            if prefix:
                kwargs['Prefix'] = prefix
                
            paginator = self.s3_client.get_paginator('list_objects_v2')
            files = []
            
            for page in paginator.paginate(**kwargs):
                if 'Contents' in page:
                    files.extend([obj['Key'] for obj in page['Contents']])
                    
            return files
            
        except Exception as e:
            print(f"Error listing S3 files: {str(e)}")
            return []
