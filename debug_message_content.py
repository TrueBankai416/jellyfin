#!/usr/bin/env python3
import sys
sys.path.append('.')

from jellyfin_log_analyzer import JellyfinLogAnalyzer

# Create analyzer instance
analyzer = JellyfinLogAnalyzer(['jellyfin.log'])

target_user_id = "4e08753f52384d35bca5e1ba104e2f21"

print("=== Checking message content during parsing ===")

with open('jellyfin.log', 'r') as f:
    for line_num, line in enumerate(f, 1):
        if line_num == 832:  # We know this line has User Data Sync
            print(f"Raw line {line_num}: {line.strip()}")
            
            entry = analyzer.parse_log_line(line)
            if entry:
                print(f"Parsed message: {entry.message}")
                print(f"Target user ID in raw line: {target_user_id in line}")
                print(f"Target user ID in parsed message: {target_user_id in entry.message}")
                print(f"Message length - Raw: {len(line)}, Parsed: {len(entry.message)}")
            else:
                print("Entry was None!")
            break
