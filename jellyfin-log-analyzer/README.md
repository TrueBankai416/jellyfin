# Jellyfin Log Analyzer

A comprehensive script to analyze Jellyfin logs and extract different types of errors. The script automatically detects your Jellyfin installation type (Docker, native, Windows service, etc.) and searches for log files in appropriate locations.

## Features

- **Automatic Environment Detection**: Detects Docker, native installations, Windows services, and more
- **Dynamic Log Discovery**: Finds log files in common locations for different installation types
- **Multiple Error Categories**: Networking, transcoding, playback, authentication, database, plugin, and general errors
- **Cross-Platform**: Works on Windows, Linux, and in Docker containers
- **Flexible Output**: Customizable number of errors per category and output file location
- **Easy-to-Use Wrappers**: Platform-specific scripts for simplified usage

## Supported Error Types

- **Networking**: Connection timeouts, DNS issues, network failures, SSL problems
- **Transcoding**: FFmpeg errors, codec issues, hardware acceleration problems, plus detailed transcoding analysis with play methods, users, clients, and transcode reasons
- **DirectStream**: Container remuxing events, format conversion without transcoding
- **Playback**: Stream failures, format issues, seeking problems, buffer issues
- **Authentication**: Login failures, token issues, authorization problems
- **Database**: SQLite errors, corruption, migration issues
- **Plugin**: Plugin loading failures, assembly errors, dependency issues
- **General**: Unhandled exceptions, critical errors, system issues

## Supported Environments

- **Docker containers** (various mount points: `/config/log/`, `/data/log/`, etc.)
- **Linux native installations** (`/var/log/jellyfin/`)
- **Linux user installations** (`~/.local/share/jellyfin/log/`)
- **Windows service installations** (`%PROGRAMDATA%\Jellyfin\Server\log\`)
- **Windows user installations** (`%APPDATA%\Jellyfin\log\`)
- **Snap installations** (`~/snap/jellyfin/current/.config/jellyfin/log/`)
- **Flatpak installations** (`~/.var/app/org.jellyfin.JellyfinServer/config/jellyfin/log/`)

## Installation

### Prerequisites

- **Python 3.7+** (required for dataclasses support)
- No additional Python packages required (uses only standard library)

### Download

1. Clone or download this repository
2. Navigate to the `jellyfin-log-analyzer` folder:
   ```bash
   cd jellyfin-log-analyzer
   ```
3. Make the Linux script executable:
   ```bash
   chmod +x jellyfin_log_analyzer.sh
   ```

## Usage

**Note**: All commands should be run from within the `jellyfin-log-analyzer` folder.

### Windows

Use the batch file wrapper for the easiest experience:

```cmd
# Navigate to the folder first
cd jellyfin-log-analyzer

# Show help and examples
jellyfin_log_analyzer.bat

# Scan for all error types
jellyfin_log_analyzer.bat --all

# Scan for specific error types
jellyfin_log_analyzer.bat --transcoding --playback

# Get more errors per category
jellyfin_log_analyzer.bat --networking --max-errors 5

# Use custom output file
jellyfin_log_analyzer.bat --all --output my_errors.txt
```

### Linux

Use the shell script wrapper:

```bash
# Navigate to the folder first
cd jellyfin-log-analyzer

# Show help and examples
./jellyfin_log_analyzer.sh

# Scan for all error types
./jellyfin_log_analyzer.sh --all

# Scan for specific error types
./jellyfin_log_analyzer.sh --transcoding --playback

# For system-wide installations, you may need sudo
sudo ./jellyfin_log_analyzer.sh --all

# Use custom log location
./jellyfin_log_analyzer.sh --all --log-path /custom/path/logs/
```

### Direct Python Usage

You can also run the Python script directly:

```bash
# Navigate to the folder first
cd jellyfin-log-analyzer

# Linux/macOS
python3 jellyfin_log_analyzer.py --all

# Windows
python jellyfin_log_analyzer.py --all
```

## Command Line Options

### Error Categories
- `--networking`: Scan for networking errors
- `--transcoding`: Scan for transcoding errors
- `--directstream`: Scan for DirectStream events
- `--playback`: Scan for playback errors
- `--authentication`: Scan for authentication errors
- `--database`: Scan for database errors
- `--plugin`: Scan for plugin errors
- `--general`: Scan for general errors
- `--all`: Scan for all error types

### Configuration
- `--log-path PATH`: Specify custom log file path (can be used multiple times)
- `--output FILE`: Output file for error report (default: auto-generated based on selected categories)
- `--max-errors N`: Maximum errors per category (default: 2)

#### Dynamic Output Filenames
When `--output` is not specified, the script automatically generates filenames based on selected categories:
- `--transcoding` → `jellyfin_log_transcoding.txt`
- `--networking` → `jellyfin_log_networking.txt`
- `--transcoding --playback` → `jellyfin_log_playback_transcoding.txt` (alphabetically sorted)
- `--all` → `jellyfin_log_all.txt`

### Information
- `--list-logs`: List detected log files and exit
- `--environment`: Show detected environment information and exit
- `--verbose`: Enable verbose output
- `--help`: Show help message

## Environment Variables

You can set these environment variables to customize log detection:

- `JELLYFIN_LOG_DIR`: Direct path to log directory
- `JELLYFIN_DATA_DIR`: Jellyfin data directory (script will check `data/log/`)
- `JELLYFIN_CONFIG_DIR`: Jellyfin config directory (script will check `config/log/`)

### Examples:

```bash
# Linux/macOS
export JELLYFIN_LOG_DIR="/custom/jellyfin/logs"
./jellyfin_log_analyzer.sh --all

# Windows
set JELLYFIN_LOG_DIR=C:\Custom\Jellyfin\Logs
jellyfin_log_analyzer.bat --all
```

## Examples

### Basic Usage

```bash
# Scan for all types of errors (2 per category)
./jellyfin_log_analyzer.sh --all

# Focus on transcoding issues
./jellyfin_log_analyzer.sh --transcoding --max-errors 5

# Check networking and playback problems
./jellyfin_log_analyzer.sh --networking --playback
```

### Advanced Usage

```bash
# Use custom log location
./jellyfin_log_analyzer.sh --all --log-path /var/log/jellyfin/jellyfin.log

# Multiple log files
./jellyfin_log_analyzer.sh --all --log-path /path/to/log1.log --log-path /path/to/log2.log

# Custom output with verbose logging
./jellyfin_log_analyzer.sh --transcoding --output transcoding_issues.txt --verbose
```

### Troubleshooting

```bash
# See what environment is detected
./jellyfin_log_analyzer.sh --environment

# List all detected log files
./jellyfin_log_analyzer.sh --list-logs

# Check if logs are accessible (Linux)
sudo ./jellyfin_log_analyzer.sh --list-logs
```

## Output Format

The script generates a detailed text report with:

- **Header**: Analysis timestamp and log files processed
- **Error Categories**: Grouped by type (networking, transcoding, etc.)
- **Error Details**: For each error:
  - File location and line number
  - Timestamp and log level
  - Category and full message
  - Exception details (if available)
  - Raw log line

### Sample Output

```
JELLYFIN LOG ANALYSIS REPORT
==================================================
Generated: 2024-01-15 14:30:22
Log files analyzed: /var/log/jellyfin/jellyfin.log

TRANSCODING
------------------------------

Transcoding Event (lines 1234-1234, time 2024-01-15 14:25:10.123000):
Play Method: Transcode (v:h264 a:direct)
User: Media Server 7
Event User ID: 4e08753f52384d35bca5e1ba104e2f21
Client: Android TV
Device: SHIELD
Media: Example Movie - s01e01 - Episode Title
Item ID: 489af7db3b5678576a9f7682ea71b001
Item Type: Episode
Transcode Reasons: Burning ASS subtitles into video stream; Client requires H.264 video codec; Bandwidth limited to 5803 kbps
--------------------------------------------------
```

## Docker Usage

The script works seamlessly in Docker environments:

```bash
# From a separate container with both the analyzer and Jellyfin logs mounted
docker run --rm -v "$(pwd)/jellyfin-log-analyzer:/app" -v /path/to/jellyfin/logs:/logs -w /app python:3 python jellyfin_log_analyzer.py --all --log-path /logs

# From inside a Jellyfin container (if you've copied the script into the container)
python3 /path/to/jellyfin_log_analyzer.py --all

# Using docker-compose to analyze logs from a Jellyfin service
docker run --rm -v "$(pwd)/jellyfin-log-analyzer:/app" -v jellyfin_logs:/logs -w /app python:3 python jellyfin_log_analyzer.py --all --log-path /logs
```

## Troubleshooting

### No Log Files Found

1. Check environment detection:
   ```bash
   ./jellyfin_log_analyzer.sh --environment
   ```

2. List what the script is looking for:
   ```bash
   ./jellyfin_log_analyzer.sh --list-logs
   ```

3. Specify custom log path:
   ```bash
   ./jellyfin_log_analyzer.sh --all --log-path /path/to/your/jellyfin.log
   ```

### Permission Issues (Linux)

If you get permission errors accessing `/var/log/jellyfin/`:

```bash
# Run with sudo
sudo ./jellyfin_log_analyzer.sh --all

# Or add your user to the jellyfin group
sudo usermod -a -G jellyfin $USER
```

### Python Not Found

- **Windows**: Install Python from [python.org](https://python.org) and ensure it's in your PATH
- **Linux**: Install Python 3:
  ```bash
  # Ubuntu/Debian
  sudo apt update && sudo apt install python3
  
  # CentOS/RHEL
  sudo yum install python3
  
  # Fedora
  sudo dnf install python3
  ```

## Contributing

Feel free to submit issues or pull requests to improve the script. Common areas for enhancement:

- Additional error patterns for better detection
- Support for more installation types
- Performance improvements for large log files
- Additional output formats (JSON, CSV, etc.)

## License

This script is provided as-is for analyzing Jellyfin logs. Use at your own discretion.
