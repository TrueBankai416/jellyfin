#!/usr/bin/env python3
import re

# Test the regex pattern
test_line = '[2025-09-25 00:43:16.386 -04:00] [INF] User Data Sync: User "Media Server 7" ("4e08753f52384d35bca5e1ba104e2f21") posted 2 updates'

print("Testing regex pattern:")
print(f"Test line: {test_line}")

# Test the regex
username_match = re.search(r'User "([^"]+)" \("([^"]+)"\)', test_line)
if username_match:
    username = username_match.group(1)
    sync_user_id = username_match.group(2)
    print(f"✅ Match found!")
    print(f"Username: {username}")
    print(f"User ID: {sync_user_id}")
else:
    print("❌ No match found")

# Test if the search would work
target_user_id = "4e08753f52384d35bca5e1ba104e2f21"
if username_match and username_match.group(2) == target_user_id:
    print(f"✅ User ID matches target: {target_user_id}")
else:
    print(f"❌ User ID doesn't match target: {target_user_id}")
