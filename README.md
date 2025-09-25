# Jellyfin Tools Collection

A collection of tools for analyzing and troubleshooting Jellyfin media server.

## Available Tools

### 🔍 [Jellyfin Log Analyzer](./jellyfin-log-analyzer/)

A comprehensive log analysis tool that extracts and analyzes different types of errors and events from Jellyfin logs.

**Key Features:**
- Enhanced transcoding analysis with root cause detection
- Username extraction for user-friendly display
- Cross-platform compatibility (Windows, Linux, Docker)
- Automatic environment detection
- Multiple error categories (networking, transcoding, playback, etc.)

**Quick Start:**
```bash
cd jellyfin-log-analyzer
./jellyfin_log_analyzer.sh --transcoding
```

See the [full documentation](./jellyfin-log-analyzer/README.md) for detailed usage instructions.

---

## Contributing

Each tool has its own directory with dedicated documentation. Feel free to contribute improvements or add new tools to help the Jellyfin community!

## License

This project is open source. Please check individual tool directories for specific license information.
