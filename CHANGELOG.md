# Changelog

All notable changes to the LogVault Python SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.2] - 2025-11-27

### Added
- Exponential backoff with jitter for automatic retries
- Strict action format validation (`entity.verb` pattern)
- Payload size validation (max 1MB)
- Python 3.13 support

### Changed
- Improved error sanitization to prevent sensitive data leakage
- Dynamic version detection from package metadata

### Fixed
- Timeout handling for both sync and async clients

## [0.2.1] - 2025-11-26

### Fixed
- Payload key compatibility (`user_id` vs `userId`)

## [0.2.0] - 2025-11-26

### Added
- `AsyncClient` for async/await support
- Configurable timeout settings
- Retry logic with configurable max attempts

### Changed
- Improved type hints throughout

## [0.1.0] - 2025-11-20

### Added
- Initial release
- `Client` class for synchronous API calls
- `log()` method for creating audit events
- `list_events()` method for retrieving events
- Custom exceptions: `APIError`, `AuthenticationError`, `RateLimitError`, `ValidationError`
- Context manager support

