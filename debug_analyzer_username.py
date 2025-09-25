#!/usr/bin/env python3
import sys
import re
sys.path.append('.')

from jellyfin_log_analyzer import JellyfinLogAnalyzer

# Create analyzer instance
analyzer = JellyfinLogAnalyzer(['jellyfin.log'])

# Parse the log file
print("=== Parsing log file ===")
entries = []
with open('jellyfin.log', 'r') as f:
    for line in f:
        entry = analyzer.parse_log_line(line)
        if entry:
            entries.append(entry)

print(f"Parsed {len(entries)} log entries")

# Find a specific transcoding event to debug
print("\n=== Finding transcoding events ===")
transcoding_events = []
for i, entry in enumerate(entries):
    if analyzer.is_transcoding_event(entry):
        # Extract details using the actual analyzer method
        details = analyzer.extract_transcoding_details_with_context(entry, entries, i)
        if details.get('event_user_id') == '4e08753f52384d35bca5e1ba104e2f21':
            print(f"Found transcoding event at index {i} (line {i+1})")
            print(f"Event details: {details}")
            
            # Check if username was extracted
            if details.get('username'):
                print(f"✅ Username found: {details['username']}")
            else:
                print("❌ Username not found")
                
                # Debug the search process
                print(f"Searching for User Data Sync lines around index {i}")
                search_start = max(0, i - 1000)
                search_end = min(len(entries), i + 1000)
                
                found_sync_lines = 0
                for j in range(search_start, search_end):
                    sync_entry = entries[j]
                    if 'User Data Sync' in sync_entry.message:
                        found_sync_lines += 1
                        if '4e08753f52384d35bca5e1ba104e2f21' in sync_entry.message:
                            print(f"✅ Found matching User Data Sync at line {j+1}: {sync_entry.message}")
                            
                            # Test regex on this line
                            username_match = re.search(r'User "([^"]+)" \("([^"]+)"\)', sync_entry.message)
                            if username_match:
                                print(f"✅ Regex matched: {username_match.group(1)} ({username_match.group(2)})")
                            else:
                                print("❌ Regex didn't match")
                
                print(f"Total User Data Sync lines found in range: {found_sync_lines}")
            
            break
