#!/usr/bin/env python3
"""
Jellyfin Log Analyzer
A comprehensive script to extract and analyze different types of errors from Jellyfin logs.
"""

import argparse
import json
import re
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class LogEntry:
    """Represents a single log entry"""
    timestamp: str
    level: str
    message: str
    category: str = ""
    exception: str = ""
    raw_line: str = ""

class ErrorPattern:
    """Defines patterns for different types of errors"""
    
    NETWORKING = [
        r"connection.*(?:timeout|refused|reset|failed)",
        r"dns.*(?:resolution|lookup).*failed",
        r"network.*(?:unreachable|error|failure)",
        r"socket.*(?:error|exception|closed)",
        r"http.*(?:request|response).*(?:failed|error|timeout)",
        r"ssl.*(?:handshake|certificate).*(?:failed|error)",
    ]
    
    TRANSCODING = [
        r"transcode.*(?:failed|error|exception)",
        r"ffmpeg.*(?:error|failed|exception)",
        r"hardware.*acceleration.*(?:failed|unavailable|error)",
        r"codec.*(?:not.*supported|failed|error)",
        r"video.*(?:encoding|decoding).*(?:failed|error)",
        r"audio.*(?:encoding|decoding).*(?:failed|error)",
        r"subtitle.*(?:encoding|extraction).*(?:failed|error)",
    ]
    
    PLAYBACK = [
        r"playback.*(?:failed|error|stopped)",
        r"stream.*(?:failed|error|unavailable|corrupted)",
        r"seeking.*(?:failed|error)",
        r"media.*(?:format|container).*(?:unsupported|error)",
        r"buffer.*(?:underrun|overflow|error)",
        r"session.*(?:failed|terminated|error)",
    ]
    
    AUTHENTICATION = [
        r"authentication.*(?:failed|error|invalid)",
        r"login.*(?:failed|invalid|error)",
        r"token.*(?:invalid|expired|error)",
        r"authorization.*(?:failed|denied|error)",
        r"user.*(?:not.*found|invalid|locked)",
        r"password.*(?:incorrect|invalid|failed)",
    ]
    
    DATABASE = [
        r"database.*(?:error|exception|corruption|locked)",
        r"sqlite.*(?:error|exception|busy|locked)",
        r"sql.*(?:syntax|error|exception)",
        r"migration.*(?:failed|error)",
        r"schema.*(?:error|invalid|corruption)",
    ]
    
    PLUGIN = [
        r"plugin.*(?:failed|error|exception|load)",
        r"assembly.*(?:load|loading).*(?:failed|error)",
        r"dependency.*(?:missing|failed|error)",
        r"configuration.*(?:invalid|error|missing)",
    ]
    
    GENERAL = [
        r"unhandled.*exception",
        r"critical.*error",
        r"fatal.*error",
        r"system.*error",
        r"out.*of.*memory",
        r"disk.*(?:full|space|error)",
    ]

class JellyfinLogAnalyzer:
    """Main class for analyzing Jellyfin logs"""
    
    def __init__(self, log_paths: List[str]):
        self.log_paths = log_paths
        self.error_patterns = {
            'networking': ErrorPattern.NETWORKING,
            'transcoding': ErrorPattern.TRANSCODING,
            'playback': ErrorPattern.PLAYBACK,
            'authentication': ErrorPattern.AUTHENTICATION,
            'database': ErrorPattern.DATABASE,
            'plugin': ErrorPattern.PLUGIN,
            'general': ErrorPattern.GENERAL,
        }
        self.found_errors = defaultdict(list)
    
    def parse_log_line(self, line: str) -> Optional[LogEntry]:
        """Parse a single log line into a LogEntry object"""
        line = line.strip()
        if not line:
            return None
        
        # Try to parse JSON format first (newer Jellyfin versions)
        if line.startswith('{'):
            try:
                data = json.loads(line)
                return LogEntry(
                    timestamp=data.get('@t', ''),
                    level=data.get('@l', ''),
                    message=data.get('@m', ''),
                    category=data.get('SourceContext', ''),
                    exception=data.get('@x', ''),
                    raw_line=line
                )
            except json.JSONDecodeError:
                pass
        
        # Try to parse standard format: [timestamp] [level] category: message
        match = re.match(r'\[([^\]]+)\]\s*\[([^\]]+)\]\s*([^:]*?):\s*(.*)', line)
        if match:
            timestamp, level, category, message = match.groups()
            return LogEntry(
                timestamp=timestamp,
                level=level.strip(),
                message=message.strip(),
                category=category.strip(),
                raw_line=line
            )
        
        # Fallback: treat entire line as message
        return LogEntry(
            timestamp='',
            level='',
            message=line,
            raw_line=line
        )
    
    def is_error_line(self, entry: LogEntry) -> bool:
        """Check if a log entry represents an error"""
        if not entry:
            return False
        
        # Check log level
        if entry.level.upper() in ['ERROR', 'FATAL', 'CRITICAL']:
            return True
        
        # Check for error keywords in message
        error_keywords = ['error', 'exception', 'failed', 'failure', 'critical', 'fatal']
        message_lower = entry.message.lower()
        return any(keyword in message_lower for keyword in error_keywords)
    
    def categorize_error(self, entry: LogEntry, selected_categories: List[str]) -> List[str]:
        """Categorize an error entry based on patterns"""
        categories = []
        full_text = f"{entry.message} {entry.exception}".lower()
        
        for category in selected_categories:
            if category in self.error_patterns:
                patterns = self.error_patterns[category]
                for pattern in patterns:
                    if re.search(pattern, full_text, re.IGNORECASE):
                        categories.append(category)
                        break
        
        return categories
    
    def analyze_logs(self, categories: List[str], max_errors_per_category: int = 2):
        """Analyze log files and extract errors"""
        print(f"Analyzing logs for categories: {', '.join(categories)}")
        
        for log_path in self.log_paths:
            if not os.path.exists(log_path):
                print(f"Warning: Log file not found: {log_path}")
                continue
            
            print(f"Processing: {log_path}")
            
            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        entry = self.parse_log_line(line)
                        
                        if entry and self.is_error_line(entry):
                            error_categories = self.categorize_error(entry, categories)
                            
                            for category in error_categories:
                                if len(self.found_errors[category]) < max_errors_per_category:
                                    self.found_errors[category].append({
                                        'entry': entry,
                                        'file': log_path,
                                        'line_number': line_num
                                    })
            
            except Exception as e:
                print(f"Error reading {log_path}: {e}")
    
    def generate_report(self, output_file: str):
        """Generate a formatted report of found errors"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("JELLYFIN LOG ANALYSIS REPORT\n")
            f.write("=" * 50 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Log files analyzed: {', '.join(self.log_paths)}\n\n")
            
            if not self.found_errors:
                f.write("No errors found matching the specified criteria.\n")
                return
            
            for category, errors in self.found_errors.items():
                f.write(f"\n{category.upper()} ERRORS\n")
                f.write("-" * 30 + "\n")
                
                if not errors:
                    f.write("No errors found in this category.\n")
                    continue
                
                for i, error_info in enumerate(errors, 1):
                    entry = error_info['entry']
                    f.write(f"\nError #{i}:\n")
                    f.write(f"File: {error_info['file']}\n")
                    f.write(f"Line: {error_info['line_number']}\n")
                    f.write(f"Timestamp: {entry.timestamp}\n")
                    f.write(f"Level: {entry.level}\n")
                    f.write(f"Category: {entry.category}\n")
                    f.write(f"Message: {entry.message}\n")
                    
                    if entry.exception:
                        f.write(f"Exception: {entry.exception}\n")
                    
                    f.write(f"Raw line: {entry.raw_line}\n")
                    f.write("-" * 50 + "\n")
        
        print(f"Report saved to: {output_file}")

def detect_environment() -> str:
    """Detect the current environment (docker, native, etc.)"""
    # Check if running in Docker
    if os.path.exists('/.dockerenv'):
        return 'docker'
    
    # Check for Docker-specific environment variables
    if any(var in os.environ for var in ['JELLYFIN_DATA_DIR', 'JELLYFIN_CONFIG_DIR', 'JELLYFIN_LOG_DIR']):
        return 'docker'
    
    # Check if running as Windows service
    if os.name == 'nt':
        service_path = os.path.expandvars(r'%PROGRAMDATA%\Jellyfin\Server')
        if os.path.exists(service_path):
            return 'windows_service'
        return 'windows_native'
    
    # Check for systemd service on Linux
    if os.path.exists('/etc/systemd/system/jellyfin.service') or os.path.exists('/lib/systemd/system/jellyfin.service'):
        return 'linux_service'
    
    return 'native'

def find_jellyfin_logs() -> List[str]:
    """Dynamically find Jellyfin log files based on environment and common locations"""
    log_files = []
    environment = detect_environment()
    
    print(f"Detected environment: {environment}")
    
    # Check environment variables first
    env_log_paths = [
        os.environ.get('JELLYFIN_LOG_DIR'),
        os.environ.get('JELLYFIN_DATA_DIR'),
        os.environ.get('JELLYFIN_CONFIG_DIR'),
    ]
    
    for env_path in env_log_paths:
        if env_path:
            log_path = os.path.join(env_path, 'log') if not env_path.endswith('log') else env_path
            if os.path.exists(log_path):
                log_files.extend(_scan_directory_for_logs(log_path))
    
    # Environment-specific paths
    if environment == 'docker':
        docker_paths = [
            "/config/log/",
            "/config/logs/",
            "/jellyfin/config/log/",
            "/jellyfin/log/",
            "/data/log/",
            "/data/logs/",
            "/app/jellyfin/log/",
            "/usr/lib/jellyfin/log/",
            "/var/log/jellyfin/",
        ]
        for path in docker_paths:
            if os.path.exists(path):
                log_files.extend(_scan_directory_for_logs(path))
    
    elif environment == 'windows_service':
        windows_service_paths = [
            os.path.expandvars(r'%PROGRAMDATA%\Jellyfin\Server\log'),
            os.path.expandvars(r'%PROGRAMDATA%\Jellyfin\log'),
        ]
        for path in windows_service_paths:
            if os.path.exists(path):
                log_files.extend(_scan_directory_for_logs(path))
    
    elif environment == 'windows_native':
        windows_native_paths = [
            os.path.expandvars(r'%APPDATA%\Jellyfin\log'),
            os.path.expandvars(r'%LOCALAPPDATA%\Jellyfin\log'),
            os.path.expanduser(r'~\AppData\Roaming\Jellyfin\log'),
            os.path.expanduser(r'~\AppData\Local\Jellyfin\log'),
        ]
        for path in windows_native_paths:
            if os.path.exists(path):
                log_files.extend(_scan_directory_for_logs(path))
    
    elif environment == 'linux_service':
        linux_service_paths = [
            "/var/log/jellyfin/",
            "/var/lib/jellyfin/log/",
            "/etc/jellyfin/log/",
        ]
        for path in linux_service_paths:
            if os.path.exists(path):
                log_files.extend(_scan_directory_for_logs(path))
    
    # Common fallback paths for all environments
    fallback_paths = [
        # Linux user installations
        "~/.config/jellyfin/log/",
        "~/.local/share/jellyfin/log/",
        "~/jellyfin/log/",
        "/opt/jellyfin/log/",
        "/usr/share/jellyfin/log/",
        
        # Windows fallbacks
        os.path.expandvars(r'%USERPROFILE%\jellyfin\log') if os.name == 'nt' else None,
        
        # Current directory and relative paths
        "./log/",
        "./logs/",
        "../log/",
        "../logs/",
        "./jellyfin/log/",
        "./config/log/",
        
        # Snap installations
        "~/snap/jellyfin/current/.config/jellyfin/log/",
        
        # Flatpak installations
        "~/.var/app/org.jellyfin.JellyfinServer/config/jellyfin/log/",
    ]
    
    for path in fallback_paths:
        if path is None:
            continue
        expanded_path = os.path.expanduser(os.path.expandvars(path))
        if os.path.exists(expanded_path):
            log_files.extend(_scan_directory_for_logs(expanded_path))
    
    # Remove duplicates while preserving order
    seen = set()
    unique_log_files = []
    for log_file in log_files:
        abs_path = os.path.abspath(log_file)
        if abs_path not in seen:
            seen.add(abs_path)
            unique_log_files.append(log_file)
    
    return unique_log_files

def _scan_directory_for_logs(directory: str) -> List[str]:
    """Scan a directory for log files"""
    log_files = []
    try:
        if os.path.isdir(directory):
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                if os.path.isfile(file_path) and _is_log_file(file):
                    log_files.append(file_path)
        elif os.path.isfile(directory) and _is_log_file(os.path.basename(directory)):
            log_files.append(directory)
    except (PermissionError, OSError) as e:
        print(f"Warning: Cannot access {directory}: {e}")
    
    return log_files

def _is_log_file(filename: str) -> bool:
    """Check if a file is likely a log file"""
    log_extensions = ['.log', '.txt']
    log_patterns = [
        'jellyfin',
        'server',
        'error',
        'debug',
        'info',
        'warn',
        'trace',
    ]
    
    filename_lower = filename.lower()
    
    # Check extension
    if any(filename_lower.endswith(ext) for ext in log_extensions):
        return True
    
    # Check for log-like patterns in filename
    if any(pattern in filename_lower for pattern in log_patterns):
        return True
    
    return False

def main():
    parser = argparse.ArgumentParser(
        description="""
Analyze Jellyfin logs and extract errors by category.

This script automatically detects your Jellyfin installation type (Docker, native, 
Windows service, etc.) and searches for log files in appropriate locations.

Supported environments:
  • Docker containers (various mount points)
  • Linux native installations (/var/log/jellyfin/)
  • Linux user installations (~/.local/share/jellyfin/)
  • Windows service installations (%PROGRAMDATA%\\Jellyfin\\)
  • Windows user installations (%APPDATA%\\Jellyfin\\)
  • Snap and Flatpak installations
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all                                    # Scan for all error types
  %(prog)s --networking --transcoding               # Scan specific categories
  %(prog)s --all --log-path /custom/path/logs/      # Use custom log location
  %(prog)s --playback --output playback_errors.txt # Custom output file
  %(prog)s --transcoding --max-errors 5             # Get more errors per type
  %(prog)s --list-logs                              # Show detected log files
  %(prog)s --environment                            # Show detected environment

Environment Variables (optional):
  JELLYFIN_LOG_DIR     - Custom log directory
  JELLYFIN_DATA_DIR    - Jellyfin data directory (will check data/log/)
  JELLYFIN_CONFIG_DIR  - Jellyfin config directory (will check config/log/)
        """
    )
    
    # Error category options
    parser.add_argument('--networking', action='store_true',
                       help='Scan for networking errors')
    parser.add_argument('--transcoding', action='store_true',
                       help='Scan for transcoding errors')
    parser.add_argument('--playback', action='store_true',
                       help='Scan for playback errors')
    parser.add_argument('--authentication', action='store_true',
                       help='Scan for authentication errors')
    parser.add_argument('--database', action='store_true',
                       help='Scan for database errors')
    parser.add_argument('--plugin', action='store_true',
                       help='Scan for plugin errors')
    parser.add_argument('--general', action='store_true',
                       help='Scan for general errors')
    parser.add_argument('--all', action='store_true',
                       help='Scan for all error types')
    
    # Configuration options
    parser.add_argument('--log-path', action='append',
                       help='Path to log file (can be used multiple times)')
    parser.add_argument('--output', '-o', default='jellyfin_errors.txt',
                       help='Output file for error report (default: jellyfin_errors.txt)')
    parser.add_argument('--max-errors', type=int, default=2,
                       help='Maximum errors per category (default: 2)')
    
    # Information options
    parser.add_argument('--list-logs', action='store_true',
                       help='List detected log files and exit')
    parser.add_argument('--environment', action='store_true',
                       help='Show detected environment information and exit')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Handle information-only options
    if args.environment:
        environment = detect_environment()
        print(f"Detected environment: {environment}")
        
        # Show environment variables
        env_vars = ['JELLYFIN_LOG_DIR', 'JELLYFIN_DATA_DIR', 'JELLYFIN_CONFIG_DIR']
        print("\nEnvironment variables:")
        for var in env_vars:
            value = os.environ.get(var)
            if value:
                print(f"  {var} = {value}")
            else:
                print(f"  {var} = (not set)")
        
        sys.exit(0)
    
    if args.list_logs:
        log_paths = find_jellyfin_logs()
        if log_paths:
            print("Detected log files:")
            for i, log_path in enumerate(log_paths, 1):
                size = "unknown size"
                try:
                    size = f"{os.path.getsize(log_path):,} bytes"
                except OSError:
                    pass
                print(f"  {i}. {log_path} ({size})")
        else:
            print("No log files detected.")
            print("Use --log-path to specify custom log file locations.")
        sys.exit(0)
    
    # Determine which categories to scan
    categories = []
    if args.all:
        categories = ['networking', 'transcoding', 'playback', 'authentication', 
                     'database', 'plugin', 'general']
    else:
        if args.networking:
            categories.append('networking')
        if args.transcoding:
            categories.append('transcoding')
        if args.playback:
            categories.append('playback')
        if args.authentication:
            categories.append('authentication')
        if args.database:
            categories.append('database')
        if args.plugin:
            categories.append('plugin')
        if args.general:
            categories.append('general')
    
    if not categories:
        print("Error: No error categories specified. Use --help for options.")
        sys.exit(1)
    
    # Determine log file paths
    log_paths = args.log_path if args.log_path else find_jellyfin_logs()
    
    if not log_paths:
        print("Error: No log files found.")
        print("Use --log-path to specify log file locations, or try:")
        print("  --list-logs     to see what the script is looking for")
        print("  --environment   to see detected environment info")
        sys.exit(1)
    
    if args.verbose:
        print(f"Using log files:")
        for log_path in log_paths:
            print(f"  - {log_path}")
        print()
    
    # Analyze logs
    analyzer = JellyfinLogAnalyzer(log_paths)
    analyzer.analyze_logs(categories, args.max_errors)
    analyzer.generate_report(args.output)
    
    # Print summary
    total_errors = sum(len(errors) for errors in analyzer.found_errors.values())
    print(f"\nSummary:")
    print(f"Total errors found: {total_errors}")
    for category, errors in analyzer.found_errors.items():
        print(f"  {category}: {len(errors)} errors")
    
    if total_errors > 0:
        print(f"\nDetailed report saved to: {args.output}")
    else:
        print("\nNo errors found matching the specified criteria.")

if __name__ == "__main__":
    main()
