# EmProps ComfyUI Nodes Changelog

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
