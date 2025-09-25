#!/usr/bin/env python3
import sys
import re
sys.path.append('.')

from jellyfin_log_analyzer import JellyfinLogAnalyzer

# Create analyzer instance
analyzer = JellyfinLogAnalyzer(['jellyfin.log'])

target_user_id = "4e08753f52384d35bca5e1ba104e2f21"

print("=== Looking for StartPlaybackTimer lines ===")

# Parse and look for StartPlaybackTimer entries
entries = []
with open('jellyfin.log', 'r') as f:
    for line in f:
        entry = analyzer.parse_log_line(line)
        if entry:
            entries.append(entry)

# Find StartPlaybackTimer entries
startplayback_entries = []
for i, entry in enumerate(entries):
    if 'StartPlaybackTimer' in entry.message:
        startplayback_entries.append((i, entry))

print(f"Found {len(startplayback_entries)} StartPlaybackTimer entries")

# Show some examples and test extraction
for i, (index, entry) in enumerate(startplayback_entries[:10]):
    print(f"\nStartPlaybackTimer {i+1} at line {index+1}:")
    print(f"Message: {entry.message}")
    
    # Test if it's considered a transcoding event
    is_transcoding = analyzer.is_transcoding_event(entry)
    print(f"Is transcoding event: {is_transcoding}")
    
    # Test extraction
    details = analyzer.extract_transcoding_details(entry)
    print(f"Extracted details: {details}")
    
    # Check if it contains our target user ID
    if target_user_id in entry.message:
        print(f"✅ Contains target user ID!")
        
        # Test the regex patterns manually
        field_patterns = {
            'event_user_id': r'event_user_id\s*[:=]\s*"([^"]+)"',
            'session_user_id': r'session_user_id\s*[:=]\s*"([^"]+)"',
        }
        
        for field_name, pattern in field_patterns.items():
            match = re.search(pattern, entry.message, re.IGNORECASE)
            if match:
                print(f"  {field_name}: {match.group(1)}")
