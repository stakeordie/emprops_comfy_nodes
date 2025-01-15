# TODO List

## High Priority
- [ ] Investigate and fix image loader preview functionality
  - Check if OUTPUT_NODE flag is set correctly
  - Verify return format matches ComfyUI's expected structure
  - Compare with working S3 saver implementation

## Release Planning
- [ ] Create new release for recent fixes
  - S3 saver preview functionality restored
  - Fixed .env file path resolution
  - Added browser-like headers for image downloads
  - Fixed local filename handling for previews

## Future Improvements
- [ ] Add better error handling for image downloads
- [ ] Consider adding retry logic for failed downloads
- [ ] Add progress indicators for long downloads
