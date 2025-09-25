#!/usr/bin/env python3
"""
Jellyfin Log Analyzer
A comprehensive script to extract and analyze different types of errors from Jellyfin logs.
"""

import argparse
import json
import re
import os
import sys
from datetime import datetime, timezone
from typing import List, Dict, Optional
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class LogEntry:
    """Represents a single log entry"""
    timestamp: str
    level: str
    message: str
    category: str = ""
    exception: str = ""
    raw_line: str = ""

class ErrorPattern:
    """Defines patterns for different types of errors"""
    
    NETWORKING = [
        r"connection.*(?:timeout|refused|reset|failed)",
        r"dns.*(?:resolution|lookup).*failed",
        r"network.*(?:unreachable|error|failure)",
        r"socket.*(?:error|exception|closed)",
        r"http.*(?:request|response).*(?:failed|error|timeout)",
        r"ssl.*(?:handshake|certificate).*(?:failed|error)",
    ]
    
    TRANSCODING = [
        # Error patterns
        r"transcode.*(?:failed|error|exception)",
        r"ffmpeg.*(?:error|failed|exception|exited.*code\s*\d+)",
        r"hardware.*acceleration.*(?:failed|unavailable|error)",
        r"codec.*(?:not.*supported|failed|error)",
        r"video.*(?:encoding|decoding).*(?:failed|error)",
        r"audio.*(?:encoding|decoding).*(?:failed|error)",
        r"subtitle.*(?:encoding|extraction).*(?:failed|error)",
        # Transcoding event patterns (not errors, but transcoding activity)
        r"play_method.*=.*transcode",
        r"ffmpeg.*-i\s+file:",
        r"started.*transcod",
        r"transcod.*start",
        r"h264_nvenc|libx264|hevc_nvenc|libx265",  # Video encoders
        r"libfdk_aac|aac|ac3|eac3",  # Audio encoders
        r"scale_cuda|scale=|vf.*scale",  # Video scaling
    ]
    
    DIRECTSTREAM = [
        # DirectStream event patterns (remuxing/container changes)
        r"play_method.*=.*directstream",
        r"directstream.*start",
        r"started.*directstream",
        r"remux.*start",
        r"started.*remux",
    ]
    
    PLAYBACK = [
        r"playback.*(?:failed|error|stopped)",
        r"stream.*(?:failed|error|unavailable|corrupted)",
        r"seeking.*(?:failed|error)",
        r"media.*(?:format|container).*(?:unsupported|error)",
        r"buffer.*(?:underrun|overflow|error)",
        r"session.*(?:failed|terminated|error)",
    ]
    
    AUTHENTICATION = [
        r"authentication.*(?:failed|error|invalid)",
        r"login.*(?:failed|invalid|error)",
        r"token.*(?:invalid|expired|error)",
        r"authorization.*(?:failed|denied|error)",
        r"user.*(?:not.*found|invalid|locked)",
        r"password.*(?:incorrect|invalid|failed)",
    ]
    
    DATABASE = [
        r"database.*(?:error|exception|corruption|locked)",
        r"sqlite.*(?:error|exception|busy|locked)",
        r"sql.*(?:syntax|error|exception)",
        r"migration.*(?:failed|error)",
        r"schema.*(?:error|invalid|corruption)",
    ]
    
    PLUGIN = [
        r"plugin.*(?:failed|error|exception|load)",
        r"assembly.*(?:load|loading).*(?:failed|error)",
        r"dependency.*(?:missing|failed|error)",
        r"configuration.*(?:invalid|error|missing)",
    ]
    
    GENERAL = [
        r"unhandled.*exception",
        r"critical.*error",
        r"fatal.*error",
        r"system.*error",
        r"out.*of.*memory",
        r"disk.*(?:full|space|error)",
    ]

class JellyfinLogAnalyzer:
    """Main class for analyzing Jellyfin logs"""
    
    def __init__(self, log_paths: List[str]):
        self.log_paths = log_paths
        self.error_patterns = {
            'networking': ErrorPattern.NETWORKING,
            'transcoding': ErrorPattern.TRANSCODING,
            'directstream': ErrorPattern.DIRECTSTREAM,
            'playback': ErrorPattern.PLAYBACK,
            'authentication': ErrorPattern.AUTHENTICATION,
            'database': ErrorPattern.DATABASE,
            'plugin': ErrorPattern.PLUGIN,
            'general': ErrorPattern.GENERAL,
        }
        self.found_errors = defaultdict(list)
    
    def parse_log_line(self, line: str) -> Optional[LogEntry]:
        """Parse a single log line into a LogEntry object"""
        line = line.strip()
        if not line:
            return None
        
        # Try to parse JSON format first (newer Jellyfin versions)
        if line.startswith('{'):
            try:
                data = json.loads(line)
                return LogEntry(
                    timestamp=data.get('@t', ''),
                    level=data.get('@l', ''),
                    message=data.get('@m', ''),
                    category=data.get('SourceContext', ''),
                    exception=data.get('@x', ''),
                    raw_line=line
                )
            except json.JSONDecodeError:
                pass
        
        # Try to parse standard format: [timestamp] [level] [category] message
        match = re.match(r'\[([^\]]+)\]\s*\[([^\]]+)\]\s*\[([^\]]+)\]\s*(.*)', line)
        if match:
            timestamp, level, category, message = match.groups()
            return LogEntry(
                timestamp=timestamp,
                level=level.strip(),
                message=message.strip(),
                category=category.strip(),
                raw_line=line
            )
        
        # Try to parse format: [timestamp] [level] category: message
        match = re.match(r'\[([^\]]+)\]\s*\[([^\]]+)\]\s*([^:]*?):\s*(.*)', line)
        if match:
            timestamp, level, category, message = match.groups()
            return LogEntry(
                timestamp=timestamp,
                level=level.strip(),
                message=message.strip(),
                category=category.strip(),
                raw_line=line
            )
        
        # Special case for FFmpeg command lines: [timestamp] [level] "ffmpeg command..."
        match = re.match(r'\[([^\]]+)\]\s*\[([^\]]+)\]\s*(.*)', line)
        if match:
            timestamp, level, message = match.groups()
            # Check if this looks like an FFmpeg command
            if 'ffmpeg' in message.lower():
                return LogEntry(
                    timestamp=timestamp,
                    level=level.strip(),
                    message=message.strip(),
                    category="FFmpeg",
                    raw_line=line
                )
            else:
                return LogEntry(
                    timestamp=timestamp,
                    level=level.strip(),
                    message=message.strip(),
                    category="",
                    raw_line=line
                )
        
        # Fallback: treat entire line as message
        return LogEntry(
            timestamp='',
            level='',
            message=line,
            raw_line=line
        )
    
    def is_error_line(self, entry: LogEntry) -> bool:
        """Check if a log entry represents an error"""
        if not entry:
            return False
        
        # Check log level - include Jellyfin's abbreviated levels
        error_levels = ['ERROR', 'ERR', 'FATAL', 'FTL', 'CRITICAL']
        if entry.level.upper() in error_levels:
            return True
        
        # Check for FFmpeg non-zero exit codes (often logged at non-error levels)
        exit_code_match = re.search(r'exited\s+with\s+code\s+(\d+)', entry.message, re.IGNORECASE)
        if exit_code_match:
            exit_code = int(exit_code_match.group(1))
            if exit_code != 0:
                return True
        
        # Check for error keywords in message
        error_keywords = ['error', 'exception', 'failed', 'failure', 'critical', 'fatal']
        message_lower = entry.message.lower()
        return any(keyword in message_lower for keyword in error_keywords)
    
    def is_transcoding_event(self, entry: LogEntry) -> bool:
        """Check if a log entry represents a transcoding event (not necessarily an error)"""
        if not entry:
            return False
        
        # Check for transcoding-specific patterns (exclude analysis/refresh operations)
        transcoding_patterns = [
            r"(?:PlayMethod|Play\s*method|play_method)\s*[:=].*transcode",  # Only actual transcoding, not DirectPlay
            r"ffmpeg.*-i\s*(?:[\"']?(?:file:|pipe:|https?://|concat:)|\S)",  # FFmpeg with input (will be filtered by exclusions)
            r"(?:h264_nvenc|libx264|hevc_nvenc|libx265)",  # Video encoders indicate transcoding
            r"started.*transcod",
            r"transcod.*start",
            r"StartPlaybackTimer\s*:\s*(?:event_|session_)",  # StartPlaybackTimer data lines
        ]
        
        full_text = f"{entry.message} {entry.category}".lower()
        
        # Exclude ffprobe commands (media analysis, not transcoding)
        if 'ffprobe' in full_text:
            return False
        
        # Exclude DirectPlay events (not transcoding) - handle both "DirectPlay" and "Direct Play"
        if re.search(r'direct\s*play', full_text):
            return False
        
        return any(re.search(pattern, full_text, re.IGNORECASE) for pattern in transcoding_patterns)
    
    def is_directstream_event(self, entry: LogEntry) -> bool:
        """Check if a log entry represents a DirectStream event (remuxing/container changes)"""
        if not entry:
            return False
        
        # Check for DirectStream-specific patterns
        directstream_patterns = [
            r"(?:PlayMethod|Play\s*method|play_method)\s*[:=].*directstream",  # DirectStream play method
            r"directstream.*start",
            r"started.*directstream",
            r"remux.*start",
            r"started.*remux",
        ]
        
        full_text = f"{entry.message} {entry.category}".lower()
        
        # Exclude ffprobe commands (media analysis, not DirectStream)
        if 'ffprobe' in full_text:
            return False
        
        return any(re.search(pattern, full_text, re.IGNORECASE) for pattern in directstream_patterns)
    
    def extract_transcoding_details(self, entry: LogEntry) -> Dict[str, str]:
        """Extract detailed transcoding information from log entry"""
        details = {}
        message = entry.message
        
        # Extract all the specific fields the user requested
        field_patterns = {
            'event_playing_id': r'event_playing_id\s*[:=]\s*"([^"]+)"',
            'event_user_id': r'event_user_id\s*[:=]\s*"([^"]+)"',
            'event_user_id_int': r'event_user_id_int\s*[:=]\s*(\d+)',
            'session_playing_id': r'session_playing_id\s*[:=]\s*"([^"]+)"',
            'session_user_id': r'session_user_id\s*[:=]\s*"([^"]+)"',
            'play_method': r'(?:PlayMethod|Play\s*method|play_method)\s*[:=]\s*"([^"]+)"',
            'client': r'(?:e\.)?ClientName\s*[:=]\s*"([^"]+)"',
            'device': r'(?:e\.)?DeviceName\s*[:=]\s*"([^"]+)"',
            'media': r'(?:e\.)?ItemName\s*[:=]\s*"([^"]+)"',
            'item_id': r'(?:e\.)?ItemId\s*[:=]\s*"([^"]+)"',
            'item_type': r'(?:e\.)?ItemType\s*[:=]\s*"([^"]+)"',
        }
        
        # Extract all fields using patterns
        for field_name, pattern in field_patterns.items():
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                details[field_name] = match.group(1)
        
        # Legacy user extraction for backward compatibility
        if 'event_user_id' in details and 'user' not in details:
            details['user'] = f"User ID: {details['event_user_id']}"
        
        # Extract FFmpeg command and analyze transcode reasons
        if 'ffmpeg' in message.lower() or 'ffmpeg' in entry.category.lower():
            details['ffmpeg_command'] = message
            details.update(self.analyze_ffmpeg_command(message))
        
        return details
    
    def extract_transcoding_details_with_context(self, entry: LogEntry, all_entries: List[LogEntry], current_index: int) -> Dict[str, str]:
        """Extract detailed transcoding information from log entry and related context lines"""
        details = {}
        line_numbers = []
        
        # Start with details from the current entry
        details.update(self.extract_transcoding_details(entry))
        
        # Look for related lines with the same timestamp (relaxed from same timestamp + category)
        entry_timestamp = entry.timestamp
        
        if entry_timestamp:
            # Search around the current entry for related lines (within a reasonable range)
            search_start = max(0, current_index - 20)  # Look back up to 20 lines
            search_end = min(len(all_entries), current_index + 20)  # Look forward up to 20 lines
            
            for i in range(search_start, search_end):
                related_entry = all_entries[i]
                
                # Check if this entry is related (same timestamp)
                if related_entry.timestamp == entry_timestamp:
                    line_numbers.append(i + 1)  # Line numbers are 1-based
                    
                    # Extract additional details from this related entry
                    related_details = self.extract_transcoding_details(related_entry)
                    
                    # Merge details, but don't overwrite existing ones
                    for key, value in related_details.items():
                        if key not in details and value:
                            details[key] = value
        
        # Add line range and time range information
        if line_numbers:
            details['line_range'] = f"{min(line_numbers)}-{max(line_numbers)}"
            
            # Also track time range from related entries
            timestamps = []
            for i in range(search_start, search_end):
                related_entry = all_entries[i]
                if related_entry.timestamp == entry_timestamp:
                    timestamps.append(related_entry.timestamp)
            
            if timestamps:
                # All timestamps should be the same, but let's be safe
                unique_timestamps = list(set(timestamps))
                if len(unique_timestamps) == 1:
                    details['time_range'] = unique_timestamps[0]
                else:
                    details['time_range'] = f"{min(unique_timestamps)} - {max(unique_timestamps)}"
        
        # Extract username from User Data Sync lines (search broader context)
        user_id = details.get('event_user_id') or details.get('session_user_id')
        if user_id and not details.get('username'):
            # Search broader context for User Data Sync lines (up to 1000 lines before/after)
            broad_search_start = max(0, current_index - 1000)
            broad_search_end = min(len(all_entries), current_index + 1000)
            
            for i in range(broad_search_start, broad_search_end):
                sync_entry = all_entries[i]
                if 'User Data Sync' in sync_entry.message:
                    # Pattern: User "Username" ("UserID")
                    username_match = re.search(r'User "([^"]+)" \("([^"]+)"\)', sync_entry.message)
                    if username_match:
                        username = username_match.group(1)
                        sync_user_id = username_match.group(2)
                        if sync_user_id == user_id:
                            details['username'] = username
                            break
        
        return details
    
    def analyze_ffmpeg_command(self, ffmpeg_cmd: str) -> Dict[str, str]:
        """Analyze FFmpeg command to determine transcode reasons (prioritizing root causes)"""
        reasons = {}
        primary_reasons = []
        
        # PRIMARY REASON 1: Subtitle burning (most common direct play blocker)
        if 'filter_complex' in ffmpeg_cmd and 'subtitles=' in ffmpeg_cmd:
            if '.ass' in ffmpeg_cmd:
                primary_reasons.append("Burning ASS subtitles into video stream")
            elif '.srt' in ffmpeg_cmd:
                primary_reasons.append("Burning SRT subtitles into video stream")
            elif '.vtt' in ffmpeg_cmd:
                primary_reasons.append("Burning WebVTT subtitles into video stream")
            else:
                primary_reasons.append("Burning subtitles into video stream")
        elif 'overlay_cuda' in ffmpeg_cmd or 'overlay=' in ffmpeg_cmd:
            primary_reasons.append("Overlaying subtitles onto video")
        
        # PRIMARY REASON 2: Resolution scaling (client can't handle source resolution)
        scale_match = re.search(r'scale(?:_cuda)?=(?:w=)?(\d+)(?::h=|:)(\d+)', ffmpeg_cmd)
        if scale_match:
            width, height = scale_match.groups()
            primary_reasons.append(f"Client requires {width}x{height} resolution")
        
        # PRIMARY REASON 3: Audio format incompatibility
        audio_copy = '-codec:a:0 copy' in ffmpeg_cmd or '-c:a copy' in ffmpeg_cmd
        if not audio_copy:
            if 'libfdk_aac' in ffmpeg_cmd or 'aac' in ffmpeg_cmd:
                primary_reasons.append("Client requires AAC audio format")
            elif 'ac3' in ffmpeg_cmd:
                primary_reasons.append("Client requires AC3 audio format")
            
            # Audio channel conversion
            ac_match = re.search(r'-ac (\d+)', ffmpeg_cmd)
            if ac_match:
                channels = ac_match.group(1)
                primary_reasons.append(f"Client requires {channels} audio channels")
        
        # PRIMARY REASON 4: Video codec incompatibility
        if 'h264_nvenc' in ffmpeg_cmd or 'libx264' in ffmpeg_cmd:
            primary_reasons.append("Client requires H.264 video codec")
        elif 'hevc_nvenc' in ffmpeg_cmd or 'libx265' in ffmpeg_cmd:
            primary_reasons.append("Client requires H.265/HEVC video codec")
        
        # PRIMARY REASON 5: Bitrate limiting (bandwidth constraint)
        bitrate_match = re.search(r'-b:v\s+(\d+)([kKmM]?)', ffmpeg_cmd)
        if bitrate_match:
            bitrate_value = int(bitrate_match.group(1))
            unit = bitrate_match.group(2).lower()
            
            if unit == 'k':
                bitrate_kbps = bitrate_value
            elif unit == 'm':
                bitrate_kbps = bitrate_value * 1000
            else:
                bitrate_kbps = bitrate_value // 1000  # Assume bits, convert to kbps
            
            primary_reasons.append(f"Bandwidth limited to {bitrate_kbps} kbps")
        
        # SECONDARY TECHNICAL DETAILS (implementation, not root cause)
        technical_details = []
        
        # Hardware acceleration detection
        hwaccel_match = re.search(r'-hwaccel\s+(\w+)', ffmpeg_cmd)
        if hwaccel_match:
            accel_type = hwaccel_match.group(1).upper()
            technical_details.append(f"Using {accel_type} hardware acceleration")
        elif 'hwaccel' in ffmpeg_cmd:
            technical_details.append("Using hardware acceleration")
        
        # Combine primary reasons and technical details
        if primary_reasons:
            reasons['primary_reasons'] = "; ".join(primary_reasons)
        
        if technical_details:
            reasons['technical_details'] = "; ".join(technical_details)
        
        # For backward compatibility, create combined reason
        all_reasons = primary_reasons + technical_details
        if all_reasons:
            reasons['combined'] = "; ".join(all_reasons)
        
        return reasons
    
    def correlate_transcoding_events(self, events: List[Dict], verbose: bool = False) -> List[Dict]:
        """Correlate related transcoding events into sessions using improved logic"""
        sessions = {}
        
        for event in events:
            entry = event['entry']
            transcoding_details = event.get('transcoding_details', {})
            
            # Try to extract session/item identifier with priority order
            session_id = None
            
            # Priority 1: Use session/event IDs from transcoding details with time-based grouping
            for id_field in ['event_playing_id', 'session_playing_id', 'item_id']:
                if transcoding_details.get(id_field):
                    # Add timestamp to session ID to prevent merging events hours apart
                    timestamp = event.get('timestamp')
                    if timestamp:
                        # Group by session ID + 5-minute time buckets to separate distant events
                        time_bucket = int(timestamp.timestamp() // 300)  # 300 seconds = 5 minutes
                        session_id = f"{transcoding_details[id_field]}_{time_bucket}"
                    else:
                        session_id = transcoding_details[id_field]
                    break
            
            # Priority 2: Look for IDs in the message
            if not session_id:
                item_id_match = re.search(r'(?:ItemId|playing_id|event_playing_id|session_playing_id)\s*=\s*"([^"]+)"', entry.message)
                if item_id_match:
                    session_id = item_id_match.group(1)
            
            # Priority 3: Look for media file path as fallback identifier
            if not session_id:
                # Try different file path patterns
                file_match = re.search(r'file:\\"([^"]+)\\"', entry.message)  # JSON escaped
                if not file_match:
                    file_match = re.search(r'file:"([^"]+)"', entry.message)  # Regular quotes
                if not file_match:
                    file_match = re.search(r'file:([^"\s]+)', entry.message)  # No quotes
                
                if file_match:
                    # Use just the filename as session identifier
                    import os
                    session_id = os.path.basename(file_match.group(1))
            
            # Priority 4: Use timestamp-based grouping with very conservative window (30 seconds for transcoding)
            if not session_id:
                timestamp = event.get('timestamp')
                if timestamp:
                    # Group events within 30 seconds of each other (using rounding to fix bucket boundaries)
                    session_id = f"time_{int((timestamp.timestamp() + 15) // 30)}"  # 30 seconds with rounding
                else:
                    session_id = f"unknown_{len(sessions)}"
            
            if session_id not in sessions:
                sessions[session_id] = {
                    'events': [],
                    'combined_details': {},
                    'latest_timestamp': None,
                    'earliest_timestamp': None
                }
            
            sessions[session_id]['events'].append(event)
            
            # Update timestamp range
            event_timestamp = event.get('timestamp')
            if event_timestamp:
                if not sessions[session_id]['latest_timestamp'] or event_timestamp > sessions[session_id]['latest_timestamp']:
                    sessions[session_id]['latest_timestamp'] = event_timestamp
                if not sessions[session_id]['earliest_timestamp'] or event_timestamp < sessions[session_id]['earliest_timestamp']:
                    sessions[session_id]['earliest_timestamp'] = event_timestamp
        
        # Try to merge sessions that might be related but got different IDs
        # Only merge sessions with strong correlation signals (same file path or very close timing)
        session_list = list(sessions.items())
        merged_sessions = {}
        
        for session_id, session_data in session_list:
            merged = False
            session_timestamp = session_data['latest_timestamp']
            
            # Only merge if we have strong indicators they're the same session
            for existing_id, existing_data in merged_sessions.items():
                existing_timestamp = existing_data['latest_timestamp']
                
                # Only merge if timestamps are within 30 seconds AND we have strong correlation signals
                if (session_timestamp and existing_timestamp and 
                    abs((session_timestamp - existing_timestamp).total_seconds()) <= 30):
                    
                    # Check for correlation signals (file paths or session IDs)
                    session_has_file = any('file:' in event['entry'].message for event in session_data['events'])
                    existing_has_file = any('file:' in event['entry'].message for event in existing_data['events'])
                    
                    # Check for session ID correlation
                    session_has_id = any(event.get('transcoding_details', {}).get('event_playing_id') for event in session_data['events'])
                    existing_has_id = any(event.get('transcoding_details', {}).get('event_playing_id') for event in existing_data['events'])
                    
                    # Merge if: both have file paths OR one has file path and other has session ID (FFmpeg + StartPlaybackTimer case)
                    should_merge = False
                    
                    # Helper function for cross-platform basename extraction
                    def _basename_any_os(path):
                        import re
                        return re.split(r'[\\/]', path)[-1]
                    
                    if session_has_file and existing_has_file:
                        # Extract file paths to compare (both have file paths)
                        session_files = set()
                        existing_files = set()
                        
                        for event in session_data['events']:
                            file_match = re.search(r'file:["\']?([^"\']+)["\']?', event['entry'].message)
                            if file_match:
                                session_files.add(_basename_any_os(file_match.group(1)))
                        
                        for event in existing_data['events']:
                            file_match = re.search(r'file:["\']?([^"\']+)["\']?', event['entry'].message)
                            if file_match:
                                existing_files.add(_basename_any_os(file_match.group(1)))
                        
                        # Merge if they share the same file
                        if session_files & existing_files:  # Intersection check
                            should_merge = True
                    
                    elif (session_has_file and existing_has_id) or (existing_has_file and session_has_id):
                        # One has file path, other has session ID (FFmpeg + StartPlaybackTimer case)
                        # This is common and should be merged if they're close in time
                        should_merge = True
                    
                    elif session_has_id and existing_has_id:
                        # Both have session IDs - check if they match AND are close in time
                        session_ids = set()
                        existing_ids = set()
                        
                        for event in session_data['events']:
                            details = event.get('transcoding_details', {})
                            for id_field in ['event_playing_id', 'session_playing_id', 'item_id']:
                                if details.get(id_field):
                                    session_ids.add(details[id_field])
                        
                        for event in existing_data['events']:
                            details = event.get('transcoding_details', {})
                            for id_field in ['event_playing_id', 'session_playing_id', 'item_id']:
                                if details.get(id_field):
                                    existing_ids.add(details[id_field])
                        
                        # Only merge if they share session ID AND are within 5 minutes (not hours apart)
                        if session_ids & existing_ids:
                            time_diff = abs((session_timestamp - existing_timestamp).total_seconds())
                            if time_diff <= 300:  # 5 minutes max for same session ID
                                should_merge = True
                    
                    if should_merge:
                        existing_data['events'].extend(session_data['events'])
                        if session_timestamp > existing_timestamp:
                            existing_data['latest_timestamp'] = session_timestamp
                        if session_data['earliest_timestamp'] < existing_data['earliest_timestamp']:
                            existing_data['earliest_timestamp'] = session_data['earliest_timestamp']
                        merged = True
                        break
            
            if not merged:
                merged_sessions[session_id] = session_data
        
        # Combine details from all events in each merged session
        correlated_sessions = []
        for session_id, session_data in merged_sessions.items():
            combined_details = {}
            
            # Merge details from all events in the session
            for event in session_data['events']:
                event_details = event.get('transcoding_details', {})
                for key, value in event_details.items():
                    if key not in combined_details and value:
                        combined_details[key] = value
            
            # Create a representative event for the session
            representative_event = session_data['events'][0]  # Use first event as base
            representative_event['transcoding_details'] = combined_details
            representative_event['timestamp'] = session_data['latest_timestamp']
            representative_event['session_id'] = session_id
            # Force event type to transcoding_event for correlated sessions
            representative_event['event_type'] = 'transcoding_event'
            
            # Add time range information for correlated sessions (with conservative limits)
            if session_data['earliest_timestamp'] and session_data['latest_timestamp']:
                # Calculate time difference
                time_diff = session_data['latest_timestamp'] - session_data['earliest_timestamp']
                
                # If time range is more than 10 minutes, something went wrong - use single timestamp
                if time_diff.total_seconds() > 600:  # 10 minutes
                    # Use the most recent timestamp for overly broad ranges
                    combined_details['time_range'] = str(session_data['latest_timestamp'])
                elif session_data['earliest_timestamp'] != session_data['latest_timestamp']:
                    combined_details['time_range'] = f"{session_data['earliest_timestamp']} - {session_data['latest_timestamp']}"
                else:
                    combined_details['time_range'] = str(session_data['latest_timestamp'])
            
            # Add line range from all events in the session (with conservative limits)
            line_numbers = []
            for event in session_data['events']:
                if 'line_number' in event:
                    line_numbers.append(event['line_number'])
            
            if line_numbers:
                min_line = min(line_numbers)
                max_line = max(line_numbers)
                line_diff = max_line - min_line
                
                # If line range is more than 1000 lines, something went wrong - use smaller range
                if line_diff > 1000:
                    # Use just the first and last few lines instead of massive range
                    combined_details['line_range'] = f"{min_line}-{min_line + 10}...{max_line - 10}-{max_line}"
                else:
                    combined_details['line_range'] = f"{min_line}-{max_line}"
            
            correlated_sessions.append(representative_event)
        
        # Sort by timestamp (latest first)
        correlated_sessions.sort(key=lambda x: x.get('timestamp') or datetime.min, reverse=True)
        
        return correlated_sessions
    
    def parse_timestamp(self, entry: LogEntry) -> Optional[datetime]:
        """Parse timestamp from log entry and normalize to naive UTC"""
        if not entry.timestamp:
            return None
        
        # Try parsing JSON format timestamp (@t field) - handles both positive and negative offsets
        if 'T' in entry.timestamp:
            # Use regex to properly handle both positive and negative timezone offsets
            iso_match = re.match(r'^(?P<dt>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)(?P<tz>Z|[+-]\d{2}:\d{2})$', entry.timestamp)
            if iso_match:
                try:
                    dt_part = iso_match.group('dt')
                    tz_part = iso_match.group('tz')
                    
                    # Handle fractional seconds with more than 6 digits (Python limitation)
                    if '.' in dt_part:
                        date_part, dot, frac_part = dt_part.partition('.')
                        # Keep only digits and truncate to 6 digits max
                        frac_digits = re.sub(r'[^0-9].*$', '', frac_part)[:6]
                        dt_part = f"{date_part}.{frac_digits}"
                    
                    # Normalize Z to +00:00
                    if tz_part == 'Z':
                        tz_part = '+00:00'
                    
                    # Reconstruct and parse
                    timestamp_str = dt_part + tz_part
                    parsed_dt = datetime.fromisoformat(timestamp_str)
                    
                    # Convert to naive UTC to avoid aware/naive mixing issues
                    return parsed_dt.astimezone(timezone.utc).replace(tzinfo=None)
                except ValueError:
                    pass
        
        # Try parsing standard log format timestamps (treat as naive UTC)
        timestamp_patterns = [
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})',  # 2024-01-15 14:25:10.123
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})',         # 2024-01-15 14:25:10
            r'(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})',         # 01/15/2024 14:25:10
        ]
        
        for pattern in timestamp_patterns:
            match = re.search(pattern, entry.timestamp)
            if match:
                timestamp_str = match.group(1)
                try:
                    if '.' in timestamp_str:
                        return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
                    elif '-' in timestamp_str:
                        return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    elif '/' in timestamp_str:
                        return datetime.strptime(timestamp_str, '%m/%d/%Y %H:%M:%S')
                except ValueError:
                    continue
        
        return None

    def categorize_error(self, entry: LogEntry, selected_categories: List[str]) -> List[str]:
        """Categorize an error entry based on patterns"""
        categories = []
        # Include category field for better classification (e.g., MediaBrowser.MediaEncoding)
        full_text = f"{entry.message} {entry.exception} {entry.category}".lower()
        
        for category in selected_categories:
            if category in self.error_patterns:
                patterns = self.error_patterns[category]
                for pattern in patterns:
                    if re.search(pattern, full_text, re.IGNORECASE):
                        categories.append(category)
                        break
        
        # If no specific category matches but 'general' is selected, add to general
        if not categories and 'general' in selected_categories:
            categories.append('general')
        
        return categories
    
    def analyze_logs(self, categories: List[str], max_errors_per_category: int = 2, verbose: bool = False):
        """Analyze log files and extract errors"""
        if verbose:
            print(f"Analyzing logs for categories: {', '.join(categories)}")
        
        # Collect all errors first, then sort by timestamp to get the latest ones
        all_errors = defaultdict(list)
        
        for log_path in self.log_paths:
            if not os.path.exists(log_path):
                print(f"Warning: Log file not found: {log_path}")
                continue
            
            if verbose:
                print(f"Processing: {log_path}")
            
            try:
                # First pass: collect all entries
                all_entries = []
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        entry = self.parse_log_line(line)
                        if entry:
                            all_entries.append((entry, line_num))
                
                # Second pass: process entries with context
                for i, (entry, line_num) in enumerate(all_entries):
                    # Check for regular errors
                    if self.is_error_line(entry):
                        error_categories = self.categorize_error(entry, categories)
                        
                        for category in error_categories:
                            error_info = {
                                'entry': entry,
                                'file': log_path,
                                'line_number': line_num,
                                'timestamp': self.parse_timestamp(entry),
                                'event_type': 'error'
                            }
                            all_errors[category].append(error_info)
                    
                    # Special handling for transcoding events (if transcoding category is selected)
                    elif 'transcoding' in categories and self.is_transcoding_event(entry):
                        # Extract details from this entry and look for related context lines
                        transcoding_details = self.extract_transcoding_details_with_context(entry, [e[0] for e in all_entries], i)
                        error_info = {
                            'entry': entry,
                            'file': log_path,
                            'line_number': line_num,
                            'timestamp': self.parse_timestamp(entry),
                            'event_type': 'transcoding_event',
                            'transcoding_details': transcoding_details
                        }
                        all_errors['transcoding'].append(error_info)
                    
                    # Special handling for DirectStream events (if directstream category is selected)
                    elif 'directstream' in categories and self.is_directstream_event(entry):
                        directstream_details = self.extract_transcoding_details(entry)  # Reuse same extraction logic
                        error_info = {
                            'entry': entry,
                            'file': log_path,
                            'line_number': line_num,
                            'timestamp': self.parse_timestamp(entry),
                            'event_type': 'directstream_event',
                            'directstream_details': directstream_details
                        }
                        all_errors['directstream'].append(error_info)
            
            except Exception as e:
                print(f"Error reading {log_path}: {e}")
        
        # Sort errors by timestamp and keep only the latest N per category
        for category, errors in all_errors.items():
            # Special handling for transcoding events - correlate related events
            if category == 'transcoding':
                correlated_events = self.correlate_transcoding_events(errors, verbose)
                # For transcoding analysis, show newest 10 events (reasonable limit for output file)
                self.found_errors[category] = correlated_events[:10]
            else:
                # Sort by timestamp (newest first), with None timestamps at the end
                errors.sort(key=lambda x: x['timestamp'] or datetime.min, reverse=True)
                # Keep only the latest max_errors_per_category
                self.found_errors[category] = errors[:max_errors_per_category]
    
    def generate_report(self, output_file: str):
        """Generate a formatted report of found errors"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("JELLYFIN LOG ANALYSIS REPORT\n")
                f.write("=" * 50 + "\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Log files analyzed: {', '.join(self.log_paths)}\n\n")
                
                if not self.found_errors:
                    f.write("No errors found matching the specified criteria.\n")
                    return
                
                for category, errors in self.found_errors.items():
                    if category == 'transcoding':
                        f.write(f"\n{category.upper()}\n")  # Just "TRANSCODING" not "TRANSCODING ERRORS"
                    elif category == 'directstream':
                        f.write(f"\nDIRECT STREAM\n")  # Just "DIRECT STREAM" not "DIRECT STREAM ERRORS"
                    else:
                        f.write(f"\n{category.upper()} ERRORS\n")
                    f.write("-" * 30 + "\n")
                    
                    if not errors:
                        f.write("No errors found in this category.\n")
                        continue
                    
                    for i, error_info in enumerate(errors, 1):
                        entry = error_info['entry']
                        event_type = error_info.get('event_type', 'error')
                        
                        # Simplified format for transcoding and DirectStream events
                        if event_type == 'transcoding_event':
                            # Include line range and time range if available
                            details = error_info.get('transcoding_details', {})
                            line_range = details.get('line_range', '')
                            time_range = details.get('time_range', '')
                            
                            header_parts = []
                            if line_range:
                                header_parts.append(f"lines {line_range}")
                            if time_range:
                                header_parts.append(f"time {time_range}")
                            
                            if header_parts:
                                f.write(f"\nTranscoding Event ({', '.join(header_parts)}):\n")
                            else:
                                f.write(f"\nTranscoding Event:\n")
                        elif event_type == 'directstream_event':
                            f.write(f"\nDirectStream Event:\n")
                        else:
                            f.write(f"\nError #{i}:\n")
                            f.write(f"File: {error_info['file']}\n")
                            f.write(f"Line: {error_info['line_number']}\n")
                            f.write(f"Timestamp: {entry.timestamp}\n")
                            f.write(f"Level: {entry.level}\n")
                            f.write(f"Category: {entry.category}\n")
                        
                        # Enhanced transcoding information with all requested fields
                        if event_type == 'transcoding_event' and 'transcoding_details' in error_info:
                            details = error_info['transcoding_details']
                            
                            # Display all the specific fields the user requested
                            field_display_names = {
                                'play_method': 'Play Method',
                                'username': 'User',
                                'event_playing_id': 'Event Playing ID',
                                'event_user_id': 'Event User ID',
                                'event_user_id_int': 'Event User ID Int',
                                'session_playing_id': 'Session Playing ID',
                                'session_user_id': 'Session User ID',
                                'client': 'Client',
                                'device': 'Device',
                                'media': 'Media',
                                'item_id': 'Item ID',
                                'item_type': 'Item Type',
                            }
                            
                            # Display fields in the order requested by user
                            for field_key, display_name in field_display_names.items():
                                if details.get(field_key):
                                    f.write(f"{display_name}: {details[field_key]}\n")
                            
                            # Legacy user field for backward compatibility
                            if details.get('user') and not details.get('event_user_id'):
                                f.write(f"User: {details['user']}\n")
                            
                            # Transcode reasons (prioritizing root causes)
                            if details.get('primary_reasons'):
                                f.write(f"Transcode Reasons: {details['primary_reasons']}\n")
                            elif details.get('combined'):
                                f.write(f"Transcode Reasons: {details['combined']}\n")
                            
                            # Display FFmpeg command if available
                            if details.get('ffmpeg_command'):
                                f.write(f"FFmpeg Command: {details['ffmpeg_command']}\n")
                        
                        # Enhanced DirectStream information
                        elif event_type == 'directstream_event' and 'directstream_details' in error_info:
                            details = error_info['directstream_details']
                            
                            if details.get('play_method'):
                                f.write(f"Play Method: {details['play_method']}\n")
                            if details.get('user'):
                                f.write(f"User: {details['user']}\n")
                            if details.get('client'):
                                f.write(f"Client: {details['client']}\n")
                            if details.get('device'):
                                f.write(f"Device: {details['device']}\n")
                            if details.get('media'):
                                f.write(f"Media: {details['media']}\n")
                            
                            # DirectStream reasons (if any - usually just container/format changes)
                            if details.get('primary_reasons'):
                                f.write(f"DirectStream Reasons: {details['primary_reasons']}\n")
                            elif details.get('combined'):
                                f.write(f"DirectStream Reasons: {details['combined']}\n")
                        
                        # Only show technical details for regular errors, not transcoding/DirectStream events
                        if event_type not in ['transcoding_event', 'directstream_event']:
                            f.write(f"Message: {entry.message}\n")
                            
                            if entry.exception:
                                f.write(f"Exception: {entry.exception}\n")
                            
                            f.write(f"Raw line: {entry.raw_line}\n")
                        
                        f.write("-" * 50 + "\n")
            
            print(f"Report saved to: {output_file}")
        except (OSError, IOError) as e:
            print(f"Error: Unable to write report to {output_file}: {e}")
            print("Please check that the directory exists and is writable.")
            sys.exit(1)

def detect_environment() -> str:
    """Detect the current environment (docker, native, etc.)"""
    # Check if running in Docker
    if os.path.exists('/.dockerenv'):
        return 'docker'
    
    # Check /proc/1/cgroup for Docker (lightweight check)
    try:
        with open('/proc/1/cgroup', 'r') as f:
            if 'docker' in f.read():
                return 'docker'
    except (OSError, IOError):
        pass
    
    # Check if running as Windows service
    if os.name == 'nt':
        service_path = os.path.expandvars(r'%PROGRAMDATA%\Jellyfin\Server')
        if os.path.exists(service_path):
            return 'windows_service'
        return 'windows_native'
    
    # Check for systemd service on Linux
    if os.path.exists('/etc/systemd/system/jellyfin.service') or os.path.exists('/lib/systemd/system/jellyfin.service'):
        return 'linux_service'
    
    return 'native'

def find_jellyfin_logs(verbose: bool = False) -> List[str]:
    """Dynamically find Jellyfin log files based on environment and common locations"""
    log_files = []
    environment = detect_environment()
    
    if verbose:
        print(f"Detected environment: {environment}")
    
    # Check environment variables first
    jellyfin_log_dir = os.environ.get('JELLYFIN_LOG_DIR')
    jellyfin_data_dir = os.environ.get('JELLYFIN_DATA_DIR')
    jellyfin_config_dir = os.environ.get('JELLYFIN_CONFIG_DIR')
    
    # JELLYFIN_LOG_DIR should be used as-is (it's already the log directory)
    if jellyfin_log_dir:
        expanded_path = os.path.expanduser(os.path.expandvars(jellyfin_log_dir))
        if os.path.exists(expanded_path):
            log_files.extend(_scan_directory_for_logs(expanded_path))
    
    # For DATA_DIR and CONFIG_DIR, check if they have a 'log' subdirectory
    if jellyfin_data_dir:
        log_path = os.path.join(os.path.expanduser(os.path.expandvars(jellyfin_data_dir)), 'log')
        if os.path.exists(log_path):
            log_files.extend(_scan_directory_for_logs(log_path))
    
    if jellyfin_config_dir:
        log_path = os.path.join(os.path.expanduser(os.path.expandvars(jellyfin_config_dir)), 'log')
        if os.path.exists(log_path):
            log_files.extend(_scan_directory_for_logs(log_path))
    
    # Environment-specific paths
    if environment == 'docker':
        docker_paths = [
            "/config/log/",
            "/config/logs/",
            "/jellyfin/config/log/",
            "/jellyfin/log/",
            "/data/log/",
            "/data/logs/",
            "/app/jellyfin/log/",
            "/usr/lib/jellyfin/log/",
            "/var/log/jellyfin/",
        ]
        for path in docker_paths:
            if os.path.exists(path):
                log_files.extend(_scan_directory_for_logs(path))
    
    elif environment == 'windows_service':
        windows_service_paths = [
            os.path.expandvars(r'%PROGRAMDATA%\Jellyfin\Server\log'),
            os.path.expandvars(r'%PROGRAMDATA%\Jellyfin\log'),
        ]
        for path in windows_service_paths:
            if os.path.exists(path):
                log_files.extend(_scan_directory_for_logs(path))
    
    elif environment == 'windows_native':
        windows_native_paths = [
            os.path.expandvars(r'%APPDATA%\Jellyfin\log'),
            os.path.expandvars(r'%LOCALAPPDATA%\Jellyfin\log'),
            os.path.expanduser(r'~\AppData\Roaming\Jellyfin\log'),
            os.path.expanduser(r'~\AppData\Local\Jellyfin\log'),
        ]
        for path in windows_native_paths:
            if os.path.exists(path):
                log_files.extend(_scan_directory_for_logs(path))
    
    elif environment == 'linux_service':
        linux_service_paths = [
            "/var/log/jellyfin/",          # Current logs - check first
            "/var/lib/jellyfin/log/",
            "/etc/jellyfin/log/",          # Legacy/old logs - check last
        ]
        for path in linux_service_paths:
            if os.path.exists(path):
                log_files.extend(_scan_directory_for_logs(path))
    
    # Common fallback paths for all environments
    fallback_paths = [
        # Linux user installations
        "~/.config/jellyfin/log/",
        "~/.local/share/jellyfin/log/",
        "~/jellyfin/log/",
        "/opt/jellyfin/log/",
        "/usr/share/jellyfin/log/",
        "/var/log/jellyfin/",  # Add as fallback in case environment detection misses it
        
        # Windows fallbacks
        os.path.expandvars(r'%USERPROFILE%\jellyfin\log') if os.name == 'nt' else None,
        
        # Current directory and relative paths
        "./log/",
        "./logs/",
        "../log/",
        "../logs/",
        "./jellyfin/log/",
        "./config/log/",
        
        # Snap installations
        "~/snap/jellyfin/current/.config/jellyfin/log/",
        
        # Flatpak installations
        "~/.var/app/org.jellyfin.JellyfinServer/config/jellyfin/log/",
    ]
    
    for path in fallback_paths:
        if path is None:
            continue
        expanded_path = os.path.expanduser(os.path.expandvars(path))
        if os.path.exists(expanded_path):
            log_files.extend(_scan_directory_for_logs(expanded_path))
    
    # Remove duplicates while preserving order
    seen = set()
    unique_log_files = []
    for log_file in log_files:
        abs_path = os.path.abspath(log_file)
        if abs_path not in seen:
            seen.add(abs_path)
            unique_log_files.append(log_file)
    
    return unique_log_files

def resolve_to_log_files(paths: List[str]) -> List[str]:
    """Resolve a list of paths (files or directories) to actual log files"""
    resolved_files = []
    
    for path in paths:
        # Expand environment variables and user home
        expanded_path = os.path.expanduser(os.path.expandvars(path))
        
        if os.path.isdir(expanded_path):
            # If it's a directory, scan for log files
            log_files = _scan_directory_for_logs(expanded_path)
            resolved_files.extend(log_files)
        elif os.path.isfile(expanded_path):
            # If it's a file, check if it looks like a log file
            if _is_log_file(os.path.basename(expanded_path)):
                resolved_files.append(expanded_path)
            else:
                print(f"Warning: {path} doesn't appear to be a log file, including anyway")
                resolved_files.append(expanded_path)
        else:
            print(f"Warning: Path not found: {path}")
    
    return resolved_files

def _scan_directory_for_logs(directory: str) -> List[str]:
    """Scan a directory for log files"""
    log_files = []
    try:
        if os.path.isdir(directory):
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                if os.path.isfile(file_path) and _is_log_file(file):
                    log_files.append(file_path)
        elif os.path.isfile(directory) and _is_log_file(os.path.basename(directory)):
            log_files.append(directory)
    except (PermissionError, OSError) as e:
        print(f"Warning: Cannot access {directory}: {e}")
    
    return log_files

def _is_log_file(filename: str) -> bool:
    """Check if a file is likely a log file"""
    filename_lower = filename.lower()
    
    # Must have a log-like extension
    log_extensions = ['.log', '.txt']
    if not any(filename_lower.endswith(ext) for ext in log_extensions):
        return False
    
    # Check for specific Jellyfin log patterns or generic log names
    jellyfin_patterns = [
        'jellyfin',
        'server',
        'log',  # Generic log files like log.txt
    ]
    
    # Accept files with jellyfin-specific patterns, generic log names, or ffmpeg transcode logs
    if any(pattern in filename_lower for pattern in jellyfin_patterns):
        return True
    
    # Accept FFmpeg transcode log files
    if filename_lower.startswith('ffmpeg'):
        return True
    
    return False

def generate_output_filename(categories: List[str]) -> str:
    """Generate output filename based on selected categories"""
    if not categories:
        return 'jellyfin_errors.txt'
    
    # Special case for all categories
    all_categories = ['authentication', 'database', 'directstream', 'general', 'networking', 'playback', 'plugin', 'transcoding']
    if sorted(categories) == all_categories:
        return 'jellyfin_log_all.txt'
    
    # Sort categories for consistent naming
    sorted_categories = sorted(categories)
    category_string = '_'.join(sorted_categories)
    return f'jellyfin_log_{category_string}.txt'

def get_interactive_log_path() -> Optional[str]:
    """Interactively ask user for log path when auto-detection fails"""
    try:
        print("\nNo log files detected automatically.")
        print("Common Jellyfin log locations:")
        print("  Linux:   /var/log/jellyfin/")
        print("  Windows: %PROGRAMDATA%\\Jellyfin\\Server\\log\\")
        print("  Docker:  /config/log/")
        print()
        
        path = input("Please enter the path to your Jellyfin log directory (or press Enter to exit): ").strip()
        
        if not path:
            return None
        
        # Expand environment variables and user home
        expanded_path = os.path.expanduser(os.path.expandvars(path))
        
        if not os.path.exists(expanded_path):
            print(f"Warning: Path does not exist: {expanded_path}")
            retry = input("Would you like to try again? (y/N): ").strip().lower()
            if retry in ['y', 'yes']:
                return get_interactive_log_path()
            return None
        
        return expanded_path
        
    except (KeyboardInterrupt, EOFError):
        print("\nOperation cancelled by user.")
        return None

def main():
    parser = argparse.ArgumentParser(
        description="""
Analyze Jellyfin logs and extract errors by category.

This script automatically detects your Jellyfin installation type (Docker, native, 
Windows service, etc.) and searches for log files in appropriate locations.

Supported environments:
  • Docker containers (various mount points)
  • Linux native installations (/var/log/jellyfin/)
  • Linux user installations (~/.local/share/jellyfin/)
  • Windows service installations (%PROGRAMDATA%\\Jellyfin\\)
  • Windows user installations (%APPDATA%\\Jellyfin\\)
  • Snap and Flatpak installations
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all                                    # Scan for all error types
  %(prog)s --networking --transcoding               # Scan specific categories
  %(prog)s --all --log-path /custom/path/logs/      # Use custom log location
  %(prog)s --playback --output playback_errors.txt # Custom output file
  %(prog)s --transcoding --max-errors 5             # Get more errors per type
  %(prog)s --list-logs                              # Show detected log files
  %(prog)s --environment                            # Show detected environment
  %(prog)s --interactive --transcoding              # Interactive path input
  %(prog)s --no-auto-detect --log-path /logs/       # Disable auto-detection

Environment Variables (optional):
  JELLYFIN_LOG_DIR     - Custom log directory
  JELLYFIN_DATA_DIR    - Jellyfin data directory (will check data/log/)
  JELLYFIN_CONFIG_DIR  - Jellyfin config directory (will check config/log/)
        """
    )
    
    # Error category options
    parser.add_argument('--networking', action='store_true',
                       help='Scan for networking errors')
    parser.add_argument('--transcoding', action='store_true',
                       help='Scan for transcoding errors')
    parser.add_argument('--directstream', action='store_true',
                       help='Scan for DirectStream events (remuxing/container changes)')
    parser.add_argument('--playback', action='store_true',
                       help='Scan for playback errors')
    parser.add_argument('--authentication', action='store_true',
                       help='Scan for authentication errors')
    parser.add_argument('--database', action='store_true',
                       help='Scan for database errors')
    parser.add_argument('--plugin', action='store_true',
                       help='Scan for plugin errors')
    parser.add_argument('--general', action='store_true',
                       help='Scan for general errors')
    parser.add_argument('--all', action='store_true',
                       help='Scan for all error types')
    
    # Configuration options
    parser.add_argument('--log-path', action='append',
                       help='Path to log file (can be used multiple times)')
    parser.add_argument('--output', '-o',
                       help='Output file for error report (default: auto-generated based on categories)')
    parser.add_argument('--max-errors', type=int, default=2,
                       help='Maximum errors per category (default: 2)')
    parser.add_argument('--no-auto-detect', action='store_true',
                       help='Disable automatic log detection, use only specified --log-path')
    
    # Information options
    parser.add_argument('--list-logs', action='store_true',
                       help='List detected log files and exit')
    parser.add_argument('--environment', action='store_true',
                       help='Show detected environment information and exit')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--interactive', action='store_true',
                       help='Enable interactive mode for path input when auto-detection fails')
    
    args = parser.parse_args()
    
    # Handle information-only options
    if args.environment:
        environment = detect_environment()
        print(f"Detected environment: {environment}")
        
        # Show environment variables
        env_vars = ['JELLYFIN_LOG_DIR', 'JELLYFIN_DATA_DIR', 'JELLYFIN_CONFIG_DIR']
        print("\nEnvironment variables:")
        for var in env_vars:
            value = os.environ.get(var)
            if value:
                print(f"  {var} = {value}")
            else:
                print(f"  {var} = (not set)")
        
        sys.exit(0)
    
    if args.list_logs:
        log_paths = find_jellyfin_logs(verbose=True)
        if log_paths:
            print("Detected log files:")
            for i, log_path in enumerate(log_paths, 1):
                size = "unknown size"
                try:
                    size = f"{os.path.getsize(log_path):,} bytes"
                except OSError:
                    pass
                print(f"  {i}. {log_path} ({size})")
        else:
            print("No log files detected.")
            print("Use --log-path to specify custom log file locations.")
        sys.exit(0)
    
    # Determine which categories to scan
    categories = []
    if args.all:
        categories = ['networking', 'transcoding', 'directstream', 'playback', 'authentication', 
                     'database', 'plugin', 'general']
    else:
        if args.networking:
            categories.append('networking')
        if args.transcoding:
            categories.append('transcoding')
        if args.directstream:
            categories.append('directstream')
        if args.playback:
            categories.append('playback')
        if args.authentication:
            categories.append('authentication')
        if args.database:
            categories.append('database')
        if args.plugin:
            categories.append('plugin')
        if args.general:
            categories.append('general')
    
    if not categories:
        print("Error: No error categories specified. Use --help for options.")
        sys.exit(1)
    
    # Determine log file paths
    if args.no_auto_detect:
        # Use only specified paths, no auto-detection
        log_paths = resolve_to_log_files(args.log_path or [])
    else:
        # Use specified paths if provided, otherwise auto-detect
        if args.log_path:
            log_paths = resolve_to_log_files(args.log_path)
        else:
            log_paths = find_jellyfin_logs(args.verbose)
    
    # If no log paths found, handle based on interactive flag
    if not log_paths:
        if args.interactive:
            interactive_path = get_interactive_log_path()
            if interactive_path:
                # Scan the interactive path for log files
                log_files = _scan_directory_for_logs(interactive_path)
                if log_files:
                    log_paths = log_files
                else:
                    print(f"No log files found in: {interactive_path}")
        
        if not log_paths:
            print("Error: No log files found.")
            print("Use --log-path to specify log file locations, or try:")
            print("  --interactive   to enter paths interactively")
            print("  --list-logs     to see what the script is looking for")
            print("  --environment   to see detected environment info")
            sys.exit(1)
    
    if args.verbose:
        print(f"Using log files:")
        for log_path in log_paths:
            print(f"  - {log_path}")
        print()
    
    # Generate output filename if not provided
    output_file = args.output if args.output else generate_output_filename(categories)
    
    # Analyze logs
    analyzer = JellyfinLogAnalyzer(log_paths)
    analyzer.analyze_logs(categories, args.max_errors, args.verbose)
    analyzer.generate_report(output_file)
    
    # Print summary
    total_items = sum(len(errors) for errors in analyzer.found_errors.values())
    print(f"\nSummary:")
    
    # Count errors vs transcoding events vs directstream events
    total_errors = 0
    total_transcoding_events = 0
    total_directstream_events = 0
    
    for category, items in analyzer.found_errors.items():
        error_count = sum(1 for item in items if item.get('event_type', 'error') == 'error')
        transcoding_count = sum(1 for item in items if item.get('event_type', 'error') == 'transcoding_event')
        directstream_count = sum(1 for item in items if item.get('event_type', 'error') == 'directstream_event')
        
        total_errors += error_count
        total_transcoding_events += transcoding_count
        total_directstream_events += directstream_count
        
        if category == 'transcoding' and transcoding_count > 0:
            print(f"  {category}: {error_count} errors, {transcoding_count} transcoding events")
        elif category == 'directstream' and directstream_count > 0:
            print(f"  {category}: {error_count} errors, {directstream_count} DirectStream events")
        else:
            print(f"  {category}: {len(items)} errors")
    
    # Show totals if there are any events
    if total_transcoding_events > 0 or total_directstream_events > 0:
        total_parts = [f"{total_errors} errors"]
        if total_transcoding_events > 0:
            total_parts.append(f"{total_transcoding_events} transcoding events")
        if total_directstream_events > 0:
            total_parts.append(f"{total_directstream_events} DirectStream events")
        print(f"Total: {', '.join(total_parts)}")
    
    if total_errors > 0 or total_transcoding_events > 0 or total_directstream_events > 0:
        print(f"\nDetailed report saved to: {output_file}")
    else:
        print("\nNo errors, transcoding events, or DirectStream events found matching the specified criteria.")

if __name__ == "__main__":
    main()
