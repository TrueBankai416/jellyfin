#!/bin/bash
# Jellyfin Log Analyzer - Linux Shell Wrapper
# This script makes it easy to run the Jellyfin log analyzer on Linux

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        print_error "Python is not installed or not in PATH"
        echo "Please install Python 3:"
        echo "  Ubuntu/Debian: sudo apt update && sudo apt install python3"
        echo "  CentOS/RHEL:   sudo yum install python3"
        echo "  Fedora:        sudo dnf install python3"
        echo "  Arch:          sudo pacman -S python"
        exit 1
    else
        PYTHON_CMD="python"
    fi
else
    PYTHON_CMD="python3"
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if the Python script exists
if [[ ! -f "$SCRIPT_DIR/jellyfin_log_analyzer.py" ]]; then
    print_error "jellyfin_log_analyzer.py not found in $SCRIPT_DIR"
    exit 1
fi

# Make the Python script executable if it isn't already
if [[ ! -x "$SCRIPT_DIR/jellyfin_log_analyzer.py" ]]; then
    chmod +x "$SCRIPT_DIR/jellyfin_log_analyzer.py"
fi

# If no arguments provided, show help and common usage examples
if [[ $# -eq 0 ]]; then
    echo
    print_info "Jellyfin Log Analyzer - Linux"
    echo "=============================="
    echo
    echo "Common usage examples:"
    echo
    echo "  $0 --all                          (scan for all error types)"
    echo "  $0 --transcoding --playback       (scan for specific errors)"
    echo "  $0 --networking --max-errors 5    (get more errors per type)"
    echo "  $0 --help                         (show all options)"
    echo
    echo "The script will automatically detect your Jellyfin installation"
    echo "and find log files in common Linux locations including:"
    echo "  • Native installations (/var/log/jellyfin/)"
    echo "  • Docker containers (/config/log/)"
    echo "  • User installations (~/.local/share/jellyfin/log/)"
    echo "  • Snap/Flatpak installations"
    echo
    exit 0
fi

# Check for common permission issues
if [[ -d "/var/log/jellyfin" && ! -r "/var/log/jellyfin" ]]; then
    print_warning "Cannot read /var/log/jellyfin/ - you may need to run with sudo"
    echo "Try: sudo $0 $*"
fi

# Run the Python script with all provided arguments
print_info "Running Jellyfin Log Analyzer..."
$PYTHON_CMD "$SCRIPT_DIR/jellyfin_log_analyzer.py" "$@"
status=$?

# Check exit status
if [[ $status -eq 0 ]]; then
    print_success "Analysis completed successfully!"
else
    print_error "Script execution failed"
    exit $status
fi
