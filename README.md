# Missing Episode Alert Plugin for Jellyfin

A Jellyfin plugin that detects when the next episode in a TV series is missing from your library and alerts users instead of auto-playing the next available episode.

## Features

- **Missing Episode Detection**: Automatically detects gaps in episode sequences within TV series
- **Playback Interruption**: Stops auto-play when the next sequential episode is missing
- **User Notifications**: Shows popup notifications when missing episodes are detected
- **Configurable Settings**: Customize notification behavior and plugin functionality
- **Smart Detection**: Only checks TV episodes and ignores movies (configurable)
- **Cross-Season Support**: Detects missing episodes across season boundaries

## How It Works

When you finish watching an episode, the plugin:

1. **Checks the sequence**: Looks for the next episode in numerical order
2. **Detects gaps**: If episode 5 is missing but episode 6 exists, it detects the gap
3. **Prevents auto-play**: Stops Jellyfin from automatically playing episode 6
4. **Shows notification**: Displays a popup alerting you that episode 5 is missing
5. **Provides context**: Shows which episode is missing and what the next available episode is

## Example Scenario

You have a TV series with episodes:
- Season 1: Episodes 1, 2, 3, 4, 6, 7, 8, 9, 10

When episode 4 finishes playing:
- ✅ **With plugin**: Shows alert "Missing Episode: S01E05 is missing. Next available: S01E06" and stops auto-play
- ❌ **Without plugin**: Automatically starts playing episode 6, potentially spoiling episode 5

## Installation via Jellyfin Plugin Catalog

### Method 1: Add Repository to Jellyfin (Recommended)

1. **Open Jellyfin Dashboard**
   - Go to `Dashboard` > `Plugins` > `Repositories`

2. **Add Plugin Repository**
   - Click `+` to add a new repository
   - **Repository Name**: `Missing Episode Alert`
   - **Repository URL**: `https://raw.githubusercontent.com/TrueBankai416/jellyfin/main/manifest.json`
   - Click `Save`

3. **Install Plugin**
   - Go to `Dashboard` > `Plugins` > `Catalog`
   - Find "Missing Episode Alert" in the list
   - Click `Install`
   - Restart Jellyfin server when prompted

4. **Configure Plugin**
   - Go to `Dashboard` > `Plugins` > `Missing Episode Alert`
   - Configure your preferences
   - Save settings

### Method 2: Manual Installation

1. Download the latest DLL from [Releases](https://github.com/TrueBankai416/jellyfin/releases)
2. Place it in your Jellyfin plugins directory
3. Restart Jellyfin server
4. Configure the plugin in Dashboard > Plugins > Missing Episode Alert

## Configuration Options

- **Enable Plugin**: Turn the plugin functionality on/off
- **Show Notification Popup**: Display popup notifications to users
- **Notification Duration**: How long to show notifications (1-60 seconds)
- **Check Only TV Shows**: Only monitor TV episodes (recommended)
- **Prevent Auto-Play**: Stop automatic playback when gaps are detected

## Technical Details

- **Target Framework**: .NET 8.0
- **Jellyfin Version**: Compatible with Jellyfin 10.9.x
- **Event Monitoring**: Hooks into Jellyfin's playback completion events
- **Library Integration**: Uses Jellyfin's library manager to analyze episode sequences

## Building from Source

1. Ensure you have .NET 8.0 SDK installed
2. Clone this repository
3. Run the build script:
   ```bash
   chmod +x build-plugin.sh
   ./build-plugin.sh
   ```
4. The compiled DLL will be in the `releases/v1.0.0/` directory

## Development

### Project Structure

```
Jellyfin.Plugin.MissingEpisodeAlert/
├── Plugin.cs                                    # Main plugin class
├── Configuration/
│   ├── PluginConfiguration.cs                  # Settings model
│   └── configPage.html                         # Admin UI
├── Services/
│   ├── MissingEpisodeDetectionService.cs       # Core detection logic
│   ├── PlaybackMonitorService.cs               # Event monitoring
│   └── NotificationService.cs                  # User notifications
└── PluginServiceRegistrator.cs                 # Dependency injection
```

### Plugin Catalog Structure

```
├── manifest.json                               # Plugin catalog manifest
├── images/
│   └── logo.png                               # Plugin logo
├── releases/
│   └── v1.0.0/
│       └── Jellyfin.Plugin.MissingEpisodeAlert.dll
└── build-plugin.sh                           # Build script
```

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

If you encounter any issues:

1. Check the Jellyfin logs for error messages
2. Verify your Jellyfin version is 10.9.x or later
3. Ensure the plugin is enabled in the configuration
4. Open an issue on GitHub with details about your setup

## Changelog

### v1.0.0 (2024-09-15)
- Initial release
- Missing episode detection for TV series
- Popup notifications for missing episodes
- Auto-play prevention
- Configurable settings
- Cross-season gap detection
