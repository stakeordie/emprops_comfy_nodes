# EmProps ComfyUI Nodes Changelog

## 2025-05-12

### Added
- Added `EmProps_Asset_Downloader` node (2025-05-12T13:52:12-04:00)
  - Enables downloading models and assets from external URLs (Hugging Face, CivitAI, etc.)
  - Supports authenticated downloads using API tokens
  - Includes visual progress indicator during downloads
  - Integrated from ServiceStack/comfy-asset-downloader

### Improved
- Enhanced `EmProps_Asset_Downloader` node (2025-05-12T14:08:00-04:00)
  - Updated to use ComfyUI's folder path configuration system
  - Added output signal to indicate download completion
  - Automatically refreshes model cache after download
  - Enables workflows to work on first run with missing models
  
- Fixed `EmProps_Asset_Downloader` node (2025-05-12T14:20:33-04:00)
  - Added automatic directory creation for download paths
  - Improved error handling for file operations
  - Fixed indentation issues in the code
  - Ensures compatibility with various ComfyUI environments
  
- Enhanced `EmProps_Asset_Downloader` node (2025-05-12T15:15:00-04:00)
  - Modified to return just the filename instead of the full path
  - Improved compatibility with Load Checkpoint node
  - Added test mode for copying existing models instead of downloading
  - Added detailed debug logging for troubleshooting

## 2025-04-24

### Added
- Added `EmpropsTextCloudStorageSaver` node (2025-04-24T15:20:02-04:00)
  - Supports multiple cloud providers (AWS S3, Google Cloud Storage, Azure Blob Storage)
  - Replaces the previous AWS-only `EmProps_Text_S3_Saver` node
  - Maintains backward compatibility through the legacy class

### Changed
- Updated `__init__.py` to register the new node (2025-04-24T15:20:02-04:00)
- Renamed `EmProps_Text_S3_Saver` to `EmpropsTextCloudStorageSaver` (2025-04-24T15:20:02-04:00)
- Added provider-agnostic environment variable support (2025-04-24T15:20:02-04:00)
  - Now checks for `CLOUD_PROVIDER` to determine which provider to use
  - Supports `STORAGE_TEST_MODE` instead of provider-specific test modes
  - Maintains backward compatibility with old environment variable names

### Deprecated
- `EmProps_Text_S3_Saver` is now deprecated in favor of `EmpropsTextCloudStorageSaver` (2025-04-24T15:20:02-04:00)
  - The old class is still available for backward compatibility
  - Will be removed in a future release
