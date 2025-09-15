#!/bin/bash

# Build script for Missing Episode Alert Plugin

echo "Building Missing Episode Alert Plugin for Jellyfin..."

# Check if .NET 8.0 SDK is installed
if ! command -v dotnet &> /dev/null; then
    echo "Error: .NET SDK is not installed. Please install .NET 8.0 SDK first."
    exit 1
fi

# Check .NET version
DOTNET_VERSION=$(dotnet --version)
echo "Using .NET SDK version: $DOTNET_VERSION"

# Build the plugin
echo "Building plugin..."
cd Jellyfin.Plugin.MissingEpisodeAlert

dotnet build --configuration Release

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo "Plugin DLL location: bin/Release/net8.0/Jellyfin.Plugin.MissingEpisodeAlert.dll"
    echo ""
    echo "Installation Instructions:"
    echo "1. Copy the DLL to your Jellyfin plugins directory"
    echo "2. Restart Jellyfin server"
    echo "3. Configure the plugin in Dashboard > Plugins > Missing Episode Alert"
else
    echo "❌ Build failed!"
    exit 1
fi
