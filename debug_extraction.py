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

# Find a transcoding event manually
target_user_id = "4e08753f52384d35bca5e1ba104e2f21"

for i, entry in enumerate(entries):
    if 'StartPlaybackTimer' in entry.message and 'event_user_id' in entry.message and target_user_id in entry.message:
        print(f"\nFound StartPlaybackTimer at index {i} (line {i+1})")
        print(f"Message: {entry.message}")
        
        # Extract basic details first
        details = analyzer.extract_transcoding_details(entry)
        print(f"Basic details: {details}")
        
        # Now test the username extraction logic manually
        user_id = details.get('event_user_id') or details.get('session_user_id')
        print(f"User ID to search for: {user_id}")
        
        if user_id:
            # Search for User Data Sync lines
            broad_search_start = max(0, i - 1000)
            broad_search_end = min(len(entries), i + 1000)
            
            print(f"Searching range: {broad_search_start} to {broad_search_end}")
            
            found_sync = False
            for j in range(broad_search_start, broad_search_end):
                sync_entry = entries[j]
                if 'User Data Sync' in sync_entry.message:
                    print(f"Found User Data Sync at index {j}: {sync_entry.message}")
                    
                    # Test regex
                    username_match = re.search(r'User "([^"]+)" \("([^"]+)"\)', sync_entry.message)
                    if username_match:
                        username = username_match.group(1)
                        sync_user_id = username_match.group(2)
                        print(f"Regex match: {username} ({sync_user_id})")
                        
                        if sync_user_id == user_id:
                            print(f"✅ MATCH! Username: {username}")
                            found_sync = True
                            break
            
            if not found_sync:
                print("❌ No matching User Data Sync found")
        
        break
