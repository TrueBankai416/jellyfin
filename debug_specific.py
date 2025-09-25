#!/usr/bin/env python3
import sys
import re
sys.path.append('.')

from jellyfin_log_analyzer import JellyfinLogAnalyzer

# Create analyzer instance
analyzer = JellyfinLogAnalyzer(['jellyfin.log'])

# Parse the log file
entries = []
with open('jellyfin.log', 'r') as f:
    for line in f:
        entry = analyzer.parse_log_line(line)
        if entry:
            entries.append(entry)

print(f"Parsed {len(entries)} entries")

target_user_id = "4e08753f52384d35bca5e1ba104e2f21"

# Look for any entry that contains the target user ID
print(f"\n=== Looking for entries with target user ID ===")
found_entries = []

for i, entry in enumerate(entries):
    if target_user_id in entry.message:
        found_entries.append((i, entry))
        if len(found_entries) <= 5:  # Show first 5
            print(f"Entry {i} (line {i+1}): {entry.message}")

print(f"\nFound {len(found_entries)} entries with target user ID")

# Now look specifically for transcoding events using the analyzer's method
print(f"\n=== Looking for transcoding events ===")
transcoding_count = 0

for i, entry in enumerate(entries):
    if analyzer.is_transcoding_event(entry):
        details = analyzer.extract_transcoding_details(entry)
        if details.get('event_user_id') == target_user_id or details.get('session_user_id') == target_user_id:
            transcoding_count += 1
            if transcoding_count <= 3:
                print(f"Transcoding event {i} (line {i+1}): {entry.message}")
                print(f"Details: {details}")

print(f"\nFound {transcoding_count} transcoding events with target user ID")
