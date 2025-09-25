#!/usr/bin/env python3
import sys
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

print(f"Total entries: {len(entries)}")

# Find User Data Sync lines with our target user ID
target_user_id = "4e08753f52384d35bca5e1ba104e2f21"
sync_lines = []

for i, entry in enumerate(entries):
    if 'User Data Sync' in entry.message and target_user_id in entry.message:
        sync_lines.append((i, entry.message))

print(f"\nFound {len(sync_lines)} User Data Sync lines with target user ID:")
for i, message in sync_lines:
    print(f"Line {i+1}: {message}")

# Find transcoding events with the same user ID
transcoding_lines = []
for i, entry in enumerate(entries):
    if analyzer.is_transcoding_event(entry):
        details = analyzer.extract_transcoding_details(entry)
        if details.get('event_user_id') == target_user_id or details.get('session_user_id') == target_user_id:
            transcoding_lines.append((i, entry.message))

print(f"\nFound {len(transcoding_lines)} transcoding events with target user ID:")
for i, message in transcoding_lines[:3]:  # Show first 3
    print(f"Line {i+1}: {message[:100]}...")

# Check distances
if sync_lines and transcoding_lines:
    print(f"\nDistance analysis:")
    for sync_i, _ in sync_lines:
        for trans_i, _ in transcoding_lines[:3]:
            distance = abs(sync_i - trans_i)
            print(f"Sync line {sync_i+1} to transcoding line {trans_i+1}: {distance} lines apart")
