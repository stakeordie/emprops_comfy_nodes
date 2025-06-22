import os
import sys
import boto3  # type: ignore # Will be fixed with types-boto3
import folder_paths  # type: ignore # Custom module without stubs
import traceback
import time
from dotenv import load_dotenv
from typing import Optional, Tuple, List, Dict, Any
from io import BytesIO
from ..utils import unescape_env_value, S3Handler, GCSHandler, AzureHandler, GCS_AVAILABLE, AZURE_AVAILABLE

# Added: 2025-04-24T15:20:02-04:00 - Enhanced logging for debugging
def log_debug(message):
    """Enhanced logging function with timestamp and stack info"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    caller = traceback.extract_stack()[-2]
    file = os.path.basename(caller.filename)
    line = caller.lineno
    print(f"[EmProps TEXT_CLOUD_STORAGE_SAVER {timestamp}] [{file}:{line}] {message}", flush=True)

# Added: 2025-04-24T15:20:02-04:00 - Updated to support multiple cloud providers

class EmpropsTextCloudStorageSaver:
    """
    Node for saving text content to cloud storage (AWS S3, Google Cloud Storage, or Azure Blob Storage) with dynamic prefix support
    """
    # Updated: 2025-04-24T15:20:02-04:00 - Added enhanced logging
    def __init__(self):
        # [REMOVED NON-CRITICAL LOG 2025-05-11T13:14:14-04:00] log_debug("Initializing EmpropsTextCloudStorageSaver class")  # Non-critical: class init, comment for future cleanup
        try:
            # Initialize common properties
            # [REMOVED NON-CRITICAL LOG 2025-05-11T13:14:14-04:00] log_debug("Setting up common properties")  # Non-critical: setup, comment for future cleanup
            self.default_bucket = "emprops-share"
            self.type = "s3_output"  # Keep the same type for backward compatibility
            # [REMOVED NON-CRITICAL LOG 2025-05-11T13:14:14-04:00] log_debug("Common properties set")  # Non-critical: setup, comment for future cleanup
        
            # Check if Google Cloud Storage is available
            # [REMOVED NON-CRITICAL LOG 2025-05-11T13:14:14-04:00] log_debug(f"Checking GCS availability: {GCS_AVAILABLE}")  # Non-critical: provider check
            self.gcs_available = GCS_AVAILABLE
            if self.gcs_available:
                pass  # [REMOVED NON-CRITICAL LOG 2025-05-11T13:14:14-04:00]
                pass  # [REMOVED NON-CRITICAL LOG 2025-05-11T13:14:14-04:00]
                # [REMOVED NON-CRITICAL LOG 2025-05-11T13:14:14-04:00] log_debug("Google Cloud Storage support is available")  # Non-critical: provider check
            else:
                pass  # [REMOVED NON-CRITICAL LOG 2025-05-11T13:14:14-04:00] log_debug("Google Cloud Storage support is not available. Install with 'pip install google-cloud-storage'")  # Non-critical: provider check
            
            # Check if Azure Blob Storage is available
            # [REMOVED NON-CRITICAL LOG 2025-05-11T13:14:14-04:00] log_debug(f"Checking Azure availability: {AZURE_AVAILABLE}")  # Non-critical: provider check
            self.azure_available = AZURE_AVAILABLE
            if self.azure_available:
                pass  # [REMOVED NON-CRITICAL LOG 2025-05-11T13:14:14-04:00]
                # [REMOVED NON-CRITICAL LOG 2025-05-11T13:14:14-04:00] log_debug("Azure Blob Storage support is available")  # Non-critical: provider check
            else:
                pass  # [REMOVED NON-CRITICAL LOG 2025-05-11T13:14:14-04:00] log_debug("Azure Blob Storage support is not available. Install with 'pip install azure-storage-blob'")  # Non-critical: provider check
        
            # Check for CLOUD_PROVIDER environment variable
            # Added: 2025-05-07T14:40:00-04:00 - Support for CLOUD_PROVIDER environment variable
            self.default_provider = os.getenv('CLOUD_PROVIDER', 'aws').lower()
            if self.default_provider not in ['aws', 'azure', 'google']:
                log_debug(f"Warning: Unknown CLOUD_PROVIDER value: {self.default_provider}, defaulting to 'aws'")
                self.default_provider = 'aws'
            # [REMOVED NON-CRITICAL LOG 2025-05-11T13:14:14-04:00] log_debug(f"Default cloud provider from environment: {self.default_provider}")  # Non-critical: routine
                
            # [REMOVED NON-CRITICAL LOG 2025-05-11T13:14:14-04:00] log_debug("EmpropsTextCloudStorageSaver initialization completed successfully")  # Non-critical: routine
        except Exception as e:
            log_debug(f"ERROR in EmpropsTextCloudStorageSaver.__init__: {str(e)}\n{traceback.format_exc()}")
            raise

    @classmethod
    def INPUT_TYPES(cls):
        # [REMOVED NON-CRITICAL LOG 2025-05-11T13:14:14-04:00] log_debug("EmpropsTextCloudStorageSaver.INPUT_TYPES called")  # Non-critical: routine
        try:
            # Determine available providers based on imports
            providers = ["aws"]
            # [REMOVED NON-CRITICAL LOG 2025-05-11T13:14:14-04:00] log_debug(f"GCS_AVAILABLE: {GCS_AVAILABLE}, AZURE_AVAILABLE: {AZURE_AVAILABLE}")  # Non-critical: provider check
            if GCS_AVAILABLE:
                providers.append("google")
                # [REMOVED NON-CRITICAL LOG 2025-05-11T13:14:14-04:00] log_debug("Added 'google' to providers list")  # Non-critical: provider list
            if AZURE_AVAILABLE:
                providers.append("azure")
                # [REMOVED NON-CRITICAL LOG 2025-05-11T13:14:14-04:00] log_debug("Added 'azure' to providers list")  # Non-critical: provider list
            
            # [REMOVED NON-CRITICAL LOG 2025-05-11T13:14:14-04:00] log_debug(f"Final providers list: {providers}")  # Non-critical: provider list
            result = {
                "required": {
                    "text": ("STRING", {"multiline": True}),  # Allow multiline text input
                    "provider": (providers,),
                    "prefix": ("STRING", {"default": "uploads/"}),
                    "filename": ("STRING", {"default": "text.txt"}),
                    "bucket": ("STRING", {"default": "emprops-share"})
                }
            }
            # [REMOVED NON-CRITICAL LOG 2025-05-11T13:14:14-04:00] log_debug(f"Returning INPUT_TYPES result: {result}")  # Non-critical: routine
            return result
        except Exception as e:
            log_debug(f"ERROR in INPUT_TYPES: {str(e)}\n{traceback.format_exc()}")
            # Provide a fallback in case of error
            return {
                "required": {
                    "text": ("STRING", {"multiline": True}),  # Allow multiline text input
                    "provider": (["aws"],),
                    "prefix": ("STRING", {"default": "uploads/"}),
                    "filename": ("STRING", {"default": "text.txt"}),
                    "bucket": ("STRING", {"default": "emprops-share"})
                }
            }

    RETURN_TYPES = ()  
    FUNCTION = "save_to_cloud"
    CATEGORY = "EmProps"
    OUTPUT_NODE = True
    DESCRIPTION = "Saves text content to cloud storage (AWS S3, Google Cloud Storage, or Azure Blob Storage) with configurable bucket and prefix."

    def _init_aws_credentials(self):
        """Lazy initialization of AWS credentials"""
        if hasattr(self, 'aws_access_key'):
            return  # Already initialized
            
        # First try system environment for AWS credentials
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.aws_region = os.getenv('AWS_DEFAULT_REGION')

        # If not found, try .env and .env.local files
        if not self.aws_access_key or not self.aws_secret_key:
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # Try .env first
            env_path = os.path.join(current_dir, '.env')
            if os.path.exists(env_path):
                load_dotenv(env_path)
                self.aws_secret_key = self.aws_secret_key or unescape_env_value(os.getenv('AWS_SECRET_ACCESS_KEY_ENCODED', ''))
                if not self.aws_secret_key:
                    self.aws_secret_key = self.aws_secret_key or os.getenv('AWS_SECRET_ACCESS_KEY', '')
                self.aws_access_key = self.aws_access_key or os.getenv('AWS_ACCESS_KEY_ID', '')
                self.aws_region = self.aws_region or os.getenv('AWS_DEFAULT_REGION', '')
            
            # If still not found, try .env.local
            if not self.aws_access_key or not self.aws_secret_key:
                env_local_path = os.path.join(current_dir, '.env.local')
                if os.path.exists(env_local_path):
                    load_dotenv(env_local_path)
                    self.aws_secret_key = self.aws_secret_key or unescape_env_value(os.getenv('AWS_SECRET_ACCESS_KEY_ENCODED', ''))
                    if not self.aws_secret_key:
                        self.aws_secret_key = self.aws_secret_key or os.getenv('AWS_SECRET_ACCESS_KEY', '')
                    self.aws_access_key = self.aws_access_key or os.getenv('AWS_ACCESS_KEY_ID', '')
                    self.aws_region = self.aws_region or os.getenv('AWS_DEFAULT_REGION', '')
        
        # Set default region if still not set
        self.aws_region = self.aws_region or 'us-east-1'

        if not self.aws_secret_key or not self.aws_access_key:
            log_debug("Warning: AWS credentials not found in environment or .env.local")

    def _init_gcs_credentials(self):
        """Lazy initialization of GCS credentials"""
        if hasattr(self, 'gcs_credentials_path'):
            return  # Already initialized
            
        self.gcs_credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not self.gcs_credentials_path and self.gcs_available:
            log_debug("Warning: GOOGLE_APPLICATION_CREDENTIALS not found in environment")

    def _init_azure_credentials(self):
        """Lazy initialization of Azure credentials"""
        if hasattr(self, 'azure_account_name'):
            return  # Already initialized
            
        # Support for provider-agnostic environment variables
        self.azure_account_name = os.getenv('STORAGE_ACCOUNT_NAME', os.getenv('AZURE_STORAGE_ACCOUNT'))
        self.azure_account_key = os.getenv('STORAGE_ACCOUNT_KEY', os.getenv('AZURE_STORAGE_KEY'))
        self.azure_container = os.getenv('STORAGE_CONTAINER', os.getenv('AZURE_STORAGE_CONTAINER', 'test'))
        
        # Check for test mode using provider-agnostic variable
        storage_test_mode = os.getenv('STORAGE_TEST_MODE', os.getenv('AZURE_TEST_MODE', 'false')).lower() == 'true'
        if storage_test_mode:
            self.azure_container = f"{self.azure_container}-test"
            
        if (not self.azure_account_name or not self.azure_account_key) and self.azure_available:
            log_debug("Warning: Azure credentials not found in environment. Set STORAGE_ACCOUNT_NAME/STORAGE_ACCOUNT_KEY or AZURE_STORAGE_ACCOUNT/AZURE_STORAGE_KEY")

    def verify_s3_upload(self, s3_client, bucket: str, key: str, max_attempts: int = 5, delay: int = 1) -> bool:
        """Verify that a file exists in S3 by checking with head_object"""
        import time
        
        for attempt in range(max_attempts):
            try:
                s3_client.head_object(Bucket=bucket, Key=key)
                return True
            except Exception as e:
                if attempt < max_attempts - 1:
                    print(f"[EmProps] Waiting for S3 file to be available... attempt {attempt + 1}/{max_attempts}")
                    time.sleep(delay)
                else:
                    print(f"[EmProps] Warning: Could not verify S3 upload: {str(e)}")
                    return False
        return False
        
    def verify_gcs_upload(self, gcs_handler: GCSHandler, key: str, max_attempts: int = 5, delay: int = 1) -> bool:
        """Verify that a file exists in GCS by checking with exists method"""
        import time
        
        for attempt in range(max_attempts):
            try:
                if gcs_handler.object_exists(key):
                    return True
                if attempt < max_attempts - 1:
                    print(f"[EmProps] Waiting for GCS file to be available... attempt {attempt + 1}/{max_attempts}")
                    time.sleep(delay)
                else:
                    print(f"[EmProps] Warning: Could not verify GCS upload")
                    return False
            except Exception as e:
                if attempt < max_attempts - 1:
                    print(f"[EmProps] Error checking GCS file, retrying... attempt {attempt + 1}/{max_attempts}")
                    time.sleep(delay)
                else:
                    print(f"[EmProps] Warning: Could not verify GCS upload: {str(e)}")
                    return False
        return False
        
    # Added: 2025-05-07T14:25:00-04:00 - Azure verification method
    def verify_azure_upload(self, azure_handler: AzureHandler, key: str, max_attempts: int = 5, delay: int = 1) -> bool:
        """Verify that a file exists in Azure Blob Storage by checking with exists method"""
        import time
        
        for attempt in range(max_attempts):
            try:
                if azure_handler.object_exists(key):
                    return True
                if attempt < max_attempts - 1:
                    print(f"[EmProps] Waiting for Azure blob to be available... attempt {attempt + 1}/{max_attempts}")
                    time.sleep(delay)
                else:
                    print(f"[EmProps] Warning: Could not verify Azure upload")
                    return False
            except Exception as e:
                if attempt < max_attempts - 1:
                    print(f"[EmProps] Error checking Azure blob, retrying... attempt {attempt + 1}/{max_attempts}")
                    time.sleep(delay)
                else:
                    print(f"[EmProps] Warning: Could not verify Azure upload: {str(e)}")
                    return False
        return False

    def save_to_cloud(self, text, provider, prefix, filename, bucket):
        """Save text content to cloud storage (AWS S3, Google Cloud Storage, or Azure Blob Storage) with the specified prefix and filename"""
        # Log the provider for debugging
        # [REMOVED NON-CRITICAL LOG 2025-05-11T13:14:14-04:00] log_debug(f"save_to_cloud called with provider: {provider}, bucket: {bucket}, prefix: {prefix}, filename: {filename}")  # Non-critical: routine
        # [REMOVED NON-CRITICAL LOG 2025-05-11T13:14:14-04:00] log_debug(f"Text type: {type(text)}, length: {len(text) if text else 0}")  # Non-critical: routine
        try:
            # Initialize the appropriate cloud storage client based on provider
            if provider == "aws":
                # Initialize AWS credentials only when needed
                self._init_aws_credentials()
                
                # Debug: Print AWS credentials being used (first 4 chars only)
                if self.aws_access_key:
                    print(f"[EmProps] Debug - Using AWS Access Key ID: {self.aws_access_key[:4]}...")
                if self.aws_secret_key:
                    print(f"[EmProps] Debug - Using AWS Secret Key: {self.aws_secret_key[:4]}...")
                print(f"[EmProps] Debug - Using AWS Region: {self.aws_region}")

                # Initialize S3 client with explicit credentials
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_key,
                    region_name=self.aws_region
                )
                
                # Create S3Handler for verification
                s3_handler = S3Handler(bucket)
            elif provider == "google":
                if not self.gcs_available:
                    raise ValueError("Google Cloud Storage is not available. Install with 'pip install google-cloud-storage'")
                
                # Initialize GCS credentials only when needed
                self._init_gcs_credentials()
                    
                # Debug: Print GCS credentials being used
                if self.gcs_credentials_path:
                    print(f"[EmProps] Debug - Using GCS credentials from: {self.gcs_credentials_path}")
                else:
                    print("[EmProps] Debug - Using default GCS credentials")
                    
                # Initialize GCS handler
                gcs_handler = GCSHandler(bucket)
                
                # Check if GCS client is initialized
                if not gcs_handler.gcs_client:
                    raise ValueError("Failed to initialize Google Cloud Storage client. Check your credentials.")
            elif provider == "azure":
                if not self.azure_available:
                    raise ValueError("Azure Blob Storage is not available. Install with 'pip install azure-storage-blob'")
                
                # Initialize Azure credentials only when needed
                self._init_azure_credentials()
                    
                # Debug: Print Azure credentials being used
                if self.azure_account_name:
                    print(f"[EmProps] Debug - Using Azure Storage Account: {self.azure_account_name}")
                if self.azure_account_key:
                    print(f"[EmProps] Debug - Using Azure Storage Key: {self.azure_account_key[:4]}...")
                print(f"[EmProps] Debug - Using Azure Container: {self.azure_container}")
                
                # Initialize Azure handler
                log_debug(f"Initializing Azure handler with container: {bucket}")
                azure_handler = AzureHandler(bucket)
                
                # Check if Azure client is initialized
                if not azure_handler.blob_service_client or not azure_handler.container_client:
                    raise ValueError("Failed to initialize Azure Blob Storage client. Check your credentials.")
            else:
                raise ValueError(f"Unsupported provider: {provider}")
            
            # Ensure prefix ends with '/'
            if not prefix.endswith('/'):
                prefix += '/'
            
            # Remove leading '/' if present
            if prefix.startswith('/'):
                prefix = prefix[1:]
            
            # Get the file extension
            ext = os.path.splitext(filename)[1].lower()
            if not ext:  # If no extension provided, default to .txt
                filename += '.txt'
                ext = '.txt'
            
            # Set appropriate content type
            content_type = 'text/plain'
            if ext == '.json':
                content_type = 'application/json'
            elif ext == '.html':
                content_type = 'text/html'
            elif ext == '.md':
                content_type = 'text/markdown'
            elif ext == '.csv':
                content_type = 'text/csv'
            elif ext == '.xml':
                content_type = 'application/xml'
            
            # Construct the storage key (path) for the file
            storage_key = prefix + filename
            
            # Convert text to bytes
            text_bytes = BytesIO(text.encode('utf-8'))
            
            # Upload based on provider
            if provider == "aws":
                print(f"[EmProps] Uploading to AWS S3: {bucket}/{storage_key}", flush=True)
                
                # Upload to S3 with content type
                s3_client.upload_fileobj(
                    text_bytes,
                    bucket,
                    storage_key,
                    ExtraArgs={'ContentType': content_type}
                )
                
                # Verify upload
                if self.verify_s3_upload(s3_client, bucket, storage_key):
                    print(f"[EmProps] Successfully uploaded and verified: {bucket}/{storage_key}", flush=True)
                    return {"ui": {"text": [f"Saved to: s3://{bucket}/{storage_key}"]}}
                else:
                    print(f"[EmProps] Failed to verify upload: {bucket}/{storage_key}", flush=True)
                    return {"ui": {"text": [f"Failed to verify upload: s3://{bucket}/{storage_key}"]}}
                    
            elif provider == "google":
                print(f"[EmProps] Uploading to Google Cloud Storage: {bucket}/{storage_key}", flush=True)
                
                try:
                    # Get bucket and create blob
                    bucket_obj = gcs_handler.gcs_client.bucket(bucket)
                    blob = bucket_obj.blob(storage_key)
                    
                    # Upload from file-like object with content type
                    blob.upload_from_file(
                        text_bytes,
                        content_type=content_type,
                        rewind=True  # Rewind the file pointer to the beginning
                    )
                    
                    # Verify upload
                    if self.verify_gcs_upload(gcs_handler, storage_key):
                        print(f"[EmProps] Successfully uploaded and verified: {bucket}/{storage_key}", flush=True)
                        return {"ui": {"text": [f"Saved to: gs://{bucket}/{storage_key}"]}}
                    else:
                        print(f"[EmProps] Failed to verify upload: {bucket}/{storage_key}", flush=True)
                        return {"ui": {"text": [f"Failed to verify upload: gs://{bucket}/{storage_key}"]}}
                except Exception as e:
                    print(f"[EmProps] Error uploading to GCS: {str(e)}", flush=True)
                    raise e
                    
            elif provider == "azure":
                print(f"[EmProps] Uploading to Azure Blob Storage: {bucket}/{storage_key}", flush=True)
                
                try:
                    # Upload directly from memory stream
                    log_debug(f"Uploading to Azure blob: {storage_key}")
                    blob_client = azure_handler.container_client.get_blob_client(storage_key)
                    
                    # Rewind the file pointer to the beginning
                    text_bytes.seek(0)
                    
                    # Fixed: 2025-05-07T14:40:00-04:00 - Use ContentSettings object instead of dict
                    from azure.storage.blob import ContentSettings
                    content_settings = ContentSettings(content_type=content_type)
                    blob_client.upload_blob(
                        text_bytes, 
                        overwrite=True, 
                        content_settings=content_settings
                    )
                    
                    # Verify upload using our dedicated verification method
                    if self.verify_azure_upload(azure_handler, storage_key):
                        print(f"[EmProps] Successfully uploaded and verified: {bucket}/{storage_key}", flush=True)
                        return {"ui": {"text": [f"Saved to: azure://{bucket}/{storage_key}"]}}
                    else:
                        print(f"[EmProps] Failed to verify upload: {bucket}/{storage_key}", flush=True)
                        return {"ui": {"text": [f"Failed to verify upload: azure://{bucket}/{storage_key}"]}}
                except Exception as e:
                    log_debug(f"Error uploading to Azure: {str(e)}\n{traceback.format_exc()}")
                    print(f"[EmProps] Error uploading to Azure: {str(e)}", flush=True)
                    raise e
            
        except Exception as e:
            print(f"[EmProps] Error saving to cloud storage: {str(e)}", flush=True)
            raise e

# Added: 2025-04-24T15:20:02-04:00 - Backward compatibility class
class EmProps_Text_S3_Saver(EmpropsTextCloudStorageSaver):
    """Legacy class for backward compatibility"""
    
    @classmethod
    def INPUT_TYPES(cls):
        inputs = super().INPUT_TYPES()
        # Remove provider from required inputs for backward compatibility
        if "provider" in inputs["required"]:
            del inputs["required"]["provider"]
        return inputs
    
    def save_to_s3(self, text, prefix, filename, bucket):
        """Legacy method for backward compatibility"""
        return self.save_to_cloud(text, "aws", prefix, filename, bucket)
