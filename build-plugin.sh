#!/bin/bash

# Build script for creating plugin releases

echo "Building Missing Episode Alert Plugin for Jellyfin Plugin Catalog..."

# Check if .NET 8.0 SDK is installed
if ! command -v dotnet &> /dev/null; then
    echo "Error: .NET SDK is not installed. Please install .NET 8.0 SDK first."
    exit 1
fi

# Create releases directory
mkdir -p releases/v1.0.0

# Build the plugin in Release mode
echo "Building plugin in Release mode..."
cd Jellyfin.Plugin.MissingEpisodeAlert
dotnet build --configuration Release

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    
    # Copy the DLL to releases directory
    cp bin/Release/net8.0/Jellyfin.Plugin.MissingEpisodeAlert.dll ../releases/v1.0.0/
    
    echo "Plugin DLL copied to releases/v1.0.0/"
    echo ""
    echo "📦 Release package created!"
    echo "Location: releases/v1.0.0/Jellyfin.Plugin.MissingEpisodeAlert.dll"
    echo ""
    echo "Next steps:"
    echo "1. Upload the DLL to GitHub releases"
    echo "2. Update the checksum in manifest.json"
    echo "3. Add your repository URL to Jellyfin: Dashboard > Plugins > Repositories"
    echo "   Repository URL: https://raw.githubusercontent.com/TrueBankai416/jellyfin/main/manifest.json"
else
    echo "❌ Build failed!"
    exit 1
fi
