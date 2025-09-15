# Missing Episode Alert Plugin for Jellyfin

A Jellyfin plugin that detects when the next episode in a TV series is missing from your library and alerts users instead of auto-playing the next available episode.

## Features

- **Missing Episode Detection**: Automatically detects gaps in episode sequences within TV series
- **Playback Interruption**: Stops auto-play when the next sequential episode is missing
- **User Notifications**: Shows popup notifications when missing episodes are detected
- **Configurable Settings**: Customize notification behavior and plugin functionality
- **Smart Detection**: Only checks TV episodes and ignores movies (configurable)

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

## Installation

1. Download the plugin DLL file
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
3. Build the project:
   ```bash
   dotnet build Jellyfin.Plugin.MissingEpisodeAlert/Jellyfin.Plugin.MissingEpisodeAlert.csproj
   ```
4. The compiled DLL will be in the `bin` directory

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
