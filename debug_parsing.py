#!/usr/bin/env python3
import sys
sys.path.append('.')

from jellyfin_log_analyzer import JellyfinLogAnalyzer

# Create analyzer instance
analyzer = JellyfinLogAnalyzer(['jellyfin.log'])

target_user_id = "4e08753f52384d35bca5e1ba104e2f21"

print("=== Checking raw log lines vs parsed entries ===")

# Check raw lines first
raw_sync_count = 0
raw_transcoding_count = 0

with open('jellyfin.log', 'r') as f:
    for line_num, line in enumerate(f, 1):
        if 'User Data Sync' in line and target_user_id in line:
            raw_sync_count += 1
            if raw_sync_count <= 3:
                print(f"Raw sync line {line_num}: {line.strip()}")
        
        if 'StartPlaybackTimer' in line and target_user_id in line:
            raw_transcoding_count += 1
            if raw_transcoding_count <= 3:
                print(f"Raw transcoding line {line_num}: {line.strip()}")

print(f"\nRaw file analysis:")
print(f"User Data Sync lines with target user ID: {raw_sync_count}")
print(f"StartPlaybackTimer lines with target user ID: {raw_transcoding_count}")

# Now check parsed entries
print(f"\n=== Checking parsed entries ===")
entries = []
with open('jellyfin.log', 'r') as f:
    for line_num, line in enumerate(f, 1):
        entry = analyzer.parse_log_line(line)
        if entry:
            entries.append((line_num, entry))
            
            # Check if this entry contains our target
            if target_user_id in entry.message:
                if 'User Data Sync' in entry.message:
                    print(f"Parsed sync entry at line {line_num}: {entry.message}")
                elif 'StartPlaybackTimer' in entry.message:
                    print(f"Parsed transcoding entry at line {line_num}: {entry.message}")

print(f"\nParsed {len(entries)} entries total")
