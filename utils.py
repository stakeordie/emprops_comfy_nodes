import base64
import os
import urllib.parse
import requests  # type: ignore # Will be fixed with types-requests
import folder_paths  # type: ignore # Custom module without stubs
import boto3  # type: ignore # Will be fixed with types-boto3
from typing import Optional, Tuple, List, Any, Dict, Union
from dotenv import load_dotenv
import piexif  # type: ignore # No stubs available
import json
import mimetypes
from PIL.PngImagePlugin import PngImageFile
from PIL.JpegImagePlugin import JpegImageFile
from PIL import Image

# Import Google Cloud Storage client library
try:
    from google.cloud import storage  # type: ignore # No stubs available
    from google.oauth2 import service_account  # type: ignore # No stubs available
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    print("[EmProps] Google Cloud Storage not available. Install with 'pip install google-cloud-storage'")

# Import Azure Blob Storage client library
# Added: 2025-04-13T21:28:00-04:00 - Azure Blob Storage support
try:
    from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    print("[EmProps] Azure Blob Storage not available. Install with 'pip install azure-storage-blob'")

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
        str: Path to downloaded file or None if download fails
    """
    try:
        # Setup headers to mimic a browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/'
        }
        
        # Get the filename from the URL
        parsed_url = urllib.parse.urlparse(url)
        filename = os.path.basename(parsed_url.path)
        if not filename:
            filename = 'downloaded_image.jpg'
            
        # Create temp directory if it doesn't exist
        temp_dir = folder_paths.get_temp_directory()
        os.makedirs(temp_dir, exist_ok=True)
        
        # Download the file
        local_filename = os.path.join(temp_dir, filename)
        with requests.get(url, stream=True, headers=headers) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    f.write(chunk)
        return local_filename
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
            
            # Determine content type from file extension
            ext = os.path.splitext(s3_key)[1].lower()
            format_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp',
                '.tiff': 'image/tiff',
                '.bmp': 'image/bmp'
            }
            content_type = format_map.get(ext, 'application/octet-stream')
            print(f"[EmProps] Uploading with content type: {content_type}", flush=True)
            
            # Upload file with content type
            self.s3_client.upload_file(
                file_path, 
                self.bucket_name, 
                s3_key,
                ExtraArgs={'ContentType': content_type}
            )
            
            # Verify upload
            if not self.verify_s3_upload(self.bucket_name, s3_key):
                return False, "Failed to verify S3 upload"
            
            return True, ""
            
        except Exception as e:
            return False, str(e)

    def object_exists(self, s3_key: str) -> bool:
        """
        Check if an object exists in the S3 bucket
        
        Args:
            s3_key: S3 object key to check
            
        Returns:
            bool: True if object exists, False otherwise
        """
        try:
            s3_url = f"s3://{self.bucket_name}/{s3_key}"
            print(f"[EmProps] Checking if file exists at: {s3_url}")
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except Exception:
            return False

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
            s3_url = f"s3://{self.bucket_name}/{s3_key}"
            print(f"[EmProps] Downloading from: {s3_url}")
            self.s3_client.download_file(
                Bucket=self.bucket_name,
                Key=s3_key,
                Filename=local_path
            )
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


class GCSHandler:
    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = bucket_name or "emprops-share"
        
        # First try system environment for service account key path
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        # If not found, try .env and .env.local files
        if not credentials_path:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Try .env first
            env_path = os.path.join(current_dir, '.env')
            if os.path.exists(env_path):
                load_dotenv(env_path)
                credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')
            
            # If still not found, try .env.local
            if not credentials_path:
                env_local_path = os.path.join(current_dir, '.env.local')
                if os.path.exists(env_local_path):
                    load_dotenv(env_local_path)
                    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')
        
        # Check if credentials are available
        if not credentials_path:
            print("[EmProps] Warning: GOOGLE_APPLICATION_CREDENTIALS not set. GCS operations may fail.")
            # Initialize client without explicit credentials (will use default if available)
            self.gcs_client = storage.Client() if GCS_AVAILABLE else None
        else:
            # Initialize client with credentials from file
            try:
                credentials = service_account.Credentials.from_service_account_file(credentials_path)
                self.gcs_client = storage.Client(credentials=credentials) if GCS_AVAILABLE else None
            except Exception as e:
                print(f"[EmProps] Error initializing GCS client: {str(e)}")
                self.gcs_client = None

    def object_exists(self, gcs_key: str) -> bool:
        """
        Check if an object exists in the GCS bucket
        
        Args:
            gcs_key: GCS object key to check
            
        Returns:
            bool: True if object exists, False otherwise
        """
        try:
            if not self.gcs_client:
                return False
                
            gcs_url = f"gs://{self.bucket_name}/{gcs_key}"
            print(f"[EmProps] Checking if file exists at: {gcs_url}")
            bucket = self.gcs_client.bucket(self.bucket_name)
            blob = bucket.blob(gcs_key)
            return blob.exists()
        except Exception as e:
            print(f"[EmProps] Error checking GCS object: {str(e)}")
            return False

    def download_file(self, gcs_key: str, local_path: str) -> Tuple[bool, str]:
        """
        Download a file from GCS bucket
        
        Args:
            gcs_key: GCS object key
            local_path: Local path to save the file
            
        Returns:
            Tuple[bool, str]: (success, error_message)
        """
        try:
            if not self.gcs_client:
                return False, "GCS client not initialized"
                
            gcs_url = f"gs://{self.bucket_name}/{gcs_key}"
            print(f"[EmProps] Downloading from: {gcs_url}")
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            bucket = self.gcs_client.bucket(self.bucket_name)
            blob = bucket.blob(gcs_key)
            blob.download_to_filename(local_path)
            
            return True, ""
        except Exception as e:
            return False, str(e)

    def list_files(self, prefix: Optional[str] = None) -> List[str]:
        """
        List files in GCS bucket with optional prefix
        
        Args:
            prefix: Optional prefix to filter files
            
        Returns:
            List[str]: List of GCS keys
        """
        try:
            if not self.gcs_client:
                return []
                
            bucket = self.gcs_client.bucket(self.bucket_name)
            blobs = bucket.list_blobs(prefix=prefix)
            
            return [blob.name for blob in blobs]
        except Exception as e:
            print(f"[EmProps] Error listing GCS files: {str(e)}")
            return []

# Added: 2025-04-13T21:30:00-04:00 - Azure Blob Storage handler implementation
class AzureHandler:
    def __init__(self, container_name: Optional[str] = None):
        # Updated: 2025-05-07T16:05:00-04:00 - Explicitly load environment variables from .env files
        # Use provided container name or check environment variables
        if container_name:
            self.container_name = container_name
        else:
            # First check for provider-agnostic container name
            self.container_name = os.getenv('CLOUD_STORAGE_CONTAINER')
            if not self.container_name:
                # Fall back to Azure-specific container name
                self.container_name = os.getenv('AZURE_STORAGE_CONTAINER', 'test')
        
        # Get Azure-specific credentials from environment
        self.account_name = os.getenv('AZURE_STORAGE_ACCOUNT')
        self.account_key = os.getenv('AZURE_STORAGE_KEY')
        
        # If not found, try loading from .env and .env.local files
        if not self.account_name or not self.account_key:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Try .env first
            env_path = os.path.join(current_dir, '.env')
            if os.path.exists(env_path):
                print(f"[EmProps] Loading environment variables from: {env_path}")
                load_dotenv(env_path)
                self.account_name = self.account_name or os.getenv('AZURE_STORAGE_ACCOUNT')
                self.account_key = self.account_key or os.getenv('AZURE_STORAGE_KEY')
                self.container_name = self.container_name or os.getenv('CLOUD_STORAGE_CONTAINER') or os.getenv('AZURE_STORAGE_CONTAINER', 'test')
            
            # If still not found, try .env.local
            if not self.account_name or not self.account_key:
                env_local_path = os.path.join(current_dir, '.env.local')
                if os.path.exists(env_local_path):
                    print(f"[EmProps] Loading environment variables from: {env_local_path}")
                    load_dotenv(env_local_path)
                    self.account_name = self.account_name or os.getenv('AZURE_STORAGE_ACCOUNT')
                    self.account_key = self.account_key or os.getenv('AZURE_STORAGE_KEY')
                    self.container_name = self.container_name or os.getenv('CLOUD_STORAGE_CONTAINER') or os.getenv('AZURE_STORAGE_CONTAINER', 'test')
        
        # Debug information about available environment variables
        print(f"[EmProps] Azure Handler - Available environment variables:")
        print(f"[EmProps] AZURE_STORAGE_ACCOUNT: {'Present' if self.account_name else 'Not found'}")
        print(f"[EmProps] AZURE_STORAGE_KEY: {'Present' if self.account_key else 'Not found'}")
        print(f"[EmProps] Container name: {self.container_name}")
        
        # Check for test mode
        # Updated: 2025-05-07T15:54:30-04:00 - Use provider-agnostic test container name
        test_container = os.getenv('CLOUD_STORAGE_TEST_CONTAINER')
        if test_container:
            self.container_name = test_container
            print(f"[EmProps] Using test container from CLOUD_STORAGE_TEST_CONTAINER: {self.container_name}")
        elif os.getenv('STORAGE_TEST_MODE', 'false').lower() == 'true' or os.getenv('AZURE_TEST_MODE', 'false').lower() == 'true':
            self.container_name = f"{self.container_name}-test"
            print(f"[EmProps] Using test container: {self.container_name}")
        
        # Validate credentials
        if not all([self.account_name, self.account_key]):
            missing = []
            # Updated: 2025-05-07T15:55:00-04:00 - Focus on Azure-specific variables
            if not self.account_name: 
                missing.append('AZURE_STORAGE_ACCOUNT')
            if not self.account_key: 
                missing.append('AZURE_STORAGE_KEY')
            raise ValueError(f"Missing required Azure environment variables: {', '.join(missing)}. Please set these in your .env file or environment.")
        
        # Initialize Azure Blob Service client
        # Updated: 2025-05-07T15:52:00-04:00 - Added debug information for connection
        print(f"[EmProps] Initializing Azure Blob Service client with account: {self.account_name}")
        connection_string = f"DefaultEndpointsProtocol=https;AccountName={self.account_name};AccountKey={self.account_key};EndpointSuffix=core.windows.net"
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_client = self.blob_service_client.get_container_client(self.container_name)
        
        # Create container if it doesn't exist
        try:
            container_properties = self.container_client.get_container_properties()
            print(f"[EmProps] Using existing Azure container: {self.container_name}")
        except Exception as e:
            try:
                print(f"[EmProps] Creating Azure container: {self.container_name}")
                self.container_client.create_container()
            except Exception as create_error:
                print(f"[EmProps] Warning: Could not create Azure container: {str(create_error)}")
    
    def object_exists(self, blob_name: str) -> bool:
        """
        Check if a blob exists in the Azure container
        
        Args:
            blob_name: Azure blob name to check
            
        Returns:
            bool: True if blob exists, False otherwise
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            return blob_client.exists()
        except Exception as e:
            print(f"[EmProps] Error checking Azure blob: {str(e)}")
            return False
    
    def download_file(self, blob_name: str, local_path: str) -> Tuple[bool, str]:
        """
        Download a file from Azure Blob Storage
        
        Args:
            blob_name: Azure blob name
            local_path: Local path to save the file
            
        Returns:
            Tuple[bool, str]: (success, error_message)
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Get blob client
            blob_client = self.container_client.get_blob_client(blob_name)
            
            # Check if blob exists
            if not blob_client.exists():
                return False, f"Blob not found: {blob_name}"
            
            # Download the blob
            with open(local_path, "wb") as download_file:
                download_file.write(blob_client.download_blob().readall())
            
            return True, ""
        except Exception as e:
            return False, str(e)
    
    def upload_file(self, file_path: str, blob_prefix: Optional[str] = None, index: Optional[int] = None, target_name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Upload a file to Azure Blob Storage
        
        Args:
            file_path: Local path to the file
            blob_prefix: Optional prefix (folder) in Azure container
            index: Optional index for multiple files
            target_name: Optional target filename to use instead of the source filename
            
        Returns:
            Tuple[bool, str]: (success, error_message)
        """
        # Added: 2025-05-07T15:35:00-04:00 - Implement Azure upload with ContentSettings
        try:
            if not os.path.exists(file_path):
                return False, f"File not found: {file_path}"
                
            # Determine the target blob name
            if target_name:
                blob_name = target_name
            else:
                blob_name = os.path.basename(file_path)
                
            # Add index if provided
            if index is not None:
                base, ext = os.path.splitext(blob_name)
                blob_name = f"{base}_{index}{ext}"
                
            # Add prefix if provided
            if blob_prefix:
                blob_name = f"{blob_prefix.rstrip('/')}/{blob_name}"
                
            # Get content type
            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                # Default to binary/octet-stream
                content_type = 'application/octet-stream'
            
            # Upload the blob with proper ContentSettings object
            from azure.storage.blob import ContentSettings
            content_settings = ContentSettings(content_type=content_type)
            blob_client = self.container_client.get_blob_client(blob_name)
            
            with open(file_path, 'rb') as data:
                blob_client.upload_blob(data, overwrite=True, content_settings=content_settings)
            
            # Verify upload
            if self.object_exists(blob_name):
                # Generate URL
                url = f"https://{self.account_name}.blob.core.windows.net/{self.container_name}/{blob_name}"
                return True, url
            else:
                return False, "Failed to verify Azure Blob Storage upload"
        except Exception as e:
            print(f"[EmProps] Error uploading to Azure: {str(e)}")
            return False, str(e)
    
    def list_files(self, prefix: Optional[str] = None) -> List[str]:
        """
        List files in Azure container with optional prefix
        
        Args:
            prefix: Optional prefix to filter files
            
        Returns:
            List[str]: List of blob names
        """
        try:
            blobs = self.container_client.list_blobs(name_starts_with=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            print(f"[EmProps] Error listing Azure blobs: {str(e)}")
            return []

# Initialize mimetypes with common image formats
mimetypes.init()
mimetypes.add_type('image/jpeg', '.jpg')
mimetypes.add_type('image/jpeg', '.jpeg')
mimetypes.add_type('image/png', '.png')
mimetypes.add_type('image/gif', '.gif')
mimetypes.add_type('image/webp', '.webp')
mimetypes.add_type('image/tiff', '.tiff')
mimetypes.add_type('image/bmp', '.bmp')

def extract_metadata(img):
    """Extract metadata from a PIL Image object."""
    prompt = {}
    metadata = {
        "format": img.format,
        "mode": img.mode,
        "size": img.size,
        "info": img.info
    }
    
    # Add MIME type information 
    if img.format:
        print(f"[EmProps] Image format: {img.format}", flush=True)
        # Direct format to MIME type mapping
        format_to_mime = {
            "JPEG": "image/jpeg",
            "JPG": "image/jpeg",
            "PNG": "image/png",
            "GIF": "image/gif",
            "WEBP": "image/webp",
            "TIFF": "image/tiff",
            "BMP": "image/bmp"
        }
        metadata["mime_type"] = format_to_mime.get(img.format.upper(), "application/octet-stream")
        print(f"[EmProps] Using MIME type: {metadata['mime_type']}", flush=True)
    
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
