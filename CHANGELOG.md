# Changelog

All notable changes to the Missing Episode Alert plugin will be documented in this file.

## [1.0.0] - 2024-09-15

### Added
- Initial release of Missing Episode Alert plugin
- Missing episode detection for TV series
- Playback monitoring and event handling
- User notification system with popup alerts
- Configurable plugin settings via admin interface
- Support for preventing auto-play when episodes are missing
- Smart detection that only checks TV shows (configurable)
- Customizable notification duration (1-60 seconds)

### Features
- **Episode Sequence Analysis**: Detects gaps in episode numbering within seasons
- **Cross-Season Detection**: Handles missing episodes at season boundaries
- **Playback Completion Tracking**: Only triggers on episodes played to 90%+ completion
- **User-Friendly Notifications**: Clear messages indicating which episode is missing
- **Admin Configuration**: Full web-based configuration interface
- **Dependency Injection**: Proper service registration and lifecycle management

### Technical Details
- Built for .NET 8.0
- Compatible with Jellyfin 10.9.x
- Uses Jellyfin's session management and library APIs
- Implements proper disposal patterns for event handlers
