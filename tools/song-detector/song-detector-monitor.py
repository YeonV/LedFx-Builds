#!/usr/bin/env python3
"""
Song Detector Plus - Advanced Media Information Display
Shows comprehensive media information including position tracking across all platforms
"""

import asyncio
import platform
import sys
import time
from datetime import timedelta, datetime

# Platform-specific imports
if platform.system() == "Windows":
    from winsdk.windows.media.control import \
        GlobalSystemMediaTransportControlsSessionManager as MediaManager
elif platform.system() == "Linux":
    try:
        import dbus
    except ImportError:
        print("⚠️  dbus-python not installed. Install with: pip install dbus-python")
        sys.exit(1)
elif platform.system() == "Darwin":
    import subprocess
    import ctypes
    from pathlib import Path

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def format_time(seconds):
    """Format seconds into MM:SS or HH:MM:SS"""
    if seconds is None:
        return "N/A"
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"

def print_separator(char="═", width=60):
    """Print a separator line"""
    print(f"{Colors.OKCYAN}{char * width}{Colors.ENDC}")

def print_header(text):
    """Print a header"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{text}{Colors.ENDC}")

def print_field(label, value, color=Colors.OKBLUE):
    """Print a labeled field"""
    if value:
        print(f"{color}{label:20s}{Colors.ENDC} {value}")
    else:
        print(f"{color}{label:20s}{Colors.ENDC} {Colors.WARNING}N/A{Colors.ENDC}")

def print_progress_bar(position, duration, width=40):
    """Print a progress bar for playback position"""
    if position is None or duration is None or duration == 0:
        return
    
    progress = position / duration
    filled = int(width * progress)
    bar = "█" * filled + "░" * (width - filled)
    percentage = progress * 100
    
    pos_str = format_time(position)
    dur_str = format_time(duration)
    
    print(f"\n{Colors.OKCYAN}Progress:{Colors.ENDC}")
    print(f"{pos_str} {Colors.OKGREEN}{bar}{Colors.ENDC} {dur_str}")
    print(f"{' ' * 20}{percentage:.1f}%")

async def get_windows_media_info():
    """Get comprehensive media info on Windows using SMTC"""
    try:
        sessions = await MediaManager.request_async()
        current_session = sessions.get_current_session()
        
        if not current_session:
            return None
        
        # Get media properties
        info = await current_session.try_get_media_properties_async()
        
        # Get timeline properties
        timeline = current_session.get_timeline_properties()
        
        # Get playback info
        playback_info = current_session.get_playback_info()
        
        # Convert position/duration from TimeSpan to seconds
        position_seconds = None
        duration_seconds = None
        last_updated_time = None
        
        if timeline:
            # timeline properties return timedelta objects
            if hasattr(timeline, 'position') and timeline.position is not None:
                position_seconds = timeline.position.total_seconds()
            if hasattr(timeline, 'end_time') and timeline.end_time is not None and hasattr(timeline, 'start_time') and timeline.start_time is not None:
                duration_seconds = (timeline.end_time - timeline.start_time).total_seconds()
            if hasattr(timeline, 'last_updated_time') and timeline.last_updated_time is not None:
                last_updated_time = timeline.last_updated_time
        
        # Get playback status
        status = "Unknown"
        is_playing = False
        if playback_info:
            playback_status = playback_info.playback_status
            status_map = {
                0: "Closed",
                1: "Opened", 
                2: "Changing",
                3: "Stopped",
                4: "Playing",
                5: "Paused"
            }
            status = status_map.get(playback_status, f"Unknown ({playback_status})")
            is_playing = (playback_status == 4)  # 4 = Playing
        
        # If playing, interpolate position based on elapsed time since last update
        if is_playing and position_seconds is not None and last_updated_time is not None:
            try:
                # last_updated_time is a datetime object
                now = datetime.now(last_updated_time.tzinfo)
                elapsed = (now - last_updated_time).total_seconds()
                position_seconds += elapsed
                # Don't exceed duration
                if duration_seconds and position_seconds > duration_seconds:
                    position_seconds = duration_seconds
            except Exception:
                pass  # If interpolation fails, just use the raw position
        
        return {
            "title": info.title or "Unknown",
            "artist": info.artist or "Unknown",
            "album": info.album_title or "Unknown",
            "album_artist": info.album_artist or None,
            "track_number": info.track_number or None,
            "genres": list(info.genres) if info.genres else None,
            "position": position_seconds,
            "duration": duration_seconds,
            "status": status,
            "subtitle": info.subtitle or None,
            "platform": "Windows SMTC",
            "timeline_start": timeline.start_time.total_seconds() if timeline and hasattr(timeline, 'start_time') and timeline.start_time is not None else None,
            "timeline_end": timeline.end_time.total_seconds() if timeline and hasattr(timeline, 'end_time') and timeline.end_time is not None else None,
            "min_seek": timeline.min_seek_time.total_seconds() if timeline and hasattr(timeline, 'min_seek_time') and timeline.min_seek_time is not None else None,
            "max_seek": timeline.max_seek_time.total_seconds() if timeline and hasattr(timeline, 'max_seek_time') and timeline.max_seek_time is not None else None,
            "is_playing": is_playing,
        }
    except Exception as e:
        print(f"{Colors.FAIL}Error getting Windows media info: {e}{Colors.ENDC}")
        return None

def get_linux_media_info():
    """Get comprehensive media info on Linux using MPRIS2"""
    try:
        bus = dbus.SessionBus()
        
        # Find all MPRIS2 players
        players = [name for name in bus.list_names() if name.startswith("org.mpris.MediaPlayer2.")]
        
        if not players:
            return None
        
        # Use the first active player (could be enhanced to check playback status)
        player_name = players[0]
        player = bus.get_object(player_name, "/org/mpris/MediaPlayer2")
        properties = dbus.Interface(player, "org.freedesktop.DBus.Properties")
        
        # Get metadata
        metadata = properties.Get("org.mpris.MediaPlayer2.Player", "Metadata")
        playback_status = properties.Get("org.mpris.MediaPlayer2.Player", "PlaybackStatus")
        
        # Get position (in microseconds)
        try:
            position_us = properties.Get("org.mpris.MediaPlayer2.Player", "Position")
            position_seconds = position_us / 1_000_000
        except:
            position_seconds = None
        
        # Extract metadata
        title = metadata.get("xesam:title", "Unknown")
        artist = metadata.get("xesam:artist", ["Unknown"])
        if isinstance(artist, list):
            artist = ", ".join(artist)
        album = metadata.get("xesam:album", "Unknown")
        album_artist = metadata.get("xesam:albumArtist", None)
        track_number = metadata.get("xesam:trackNumber", None)
        genres = metadata.get("xesam:genre", None)
        
        # Duration (in microseconds)
        duration_us = metadata.get("mpris:length", None)
        duration_seconds = duration_us / 1_000_000 if duration_us else None
        
        return {
            "title": title,
            "artist": artist,
            "album": album,
            "album_artist": album_artist[0] if isinstance(album_artist, list) and album_artist else album_artist,
            "track_number": track_number,
            "genres": genres,
            "position": position_seconds,
            "duration": duration_seconds,
            "status": playback_status,
            "player_name": player_name.replace("org.mpris.MediaPlayer2.", ""),
            "platform": "Linux MPRIS2",
            "art_url": metadata.get("mpris:artUrl", None),
        }
    except Exception as e:
        print(f"{Colors.FAIL}Error getting Linux media info: {e}{Colors.ENDC}")
        return None

def get_macos_media_info():
    """Get comprehensive media info on macOS using MediaRemote framework"""
    try:
        # Load MediaRemoteAdapter if available
        adapter_path = Path(__file__).parent / "MediaRemoteAdapter.framework" / "MediaRemoteAdapter"
        
        if not adapter_path.exists():
            print(f"{Colors.WARNING}MediaRemoteAdapter.framework not found. Using basic AppleScript fallback.{Colors.ENDC}")
            return get_macos_media_info_applescript()
        
        # Load the adapter library
        lib = ctypes.CDLL(str(adapter_path))
        
        # Define function signatures
        lib.getCurrentTrackInfo.restype = ctypes.c_char_p
        lib.getElapsedTime.restype = ctypes.c_double
        lib.getDuration.restype = ctypes.c_double
        lib.isPlaying.restype = ctypes.c_bool
        
        # Get track info JSON
        track_info_json = lib.getCurrentTrackInfo()
        if not track_info_json:
            return None
        
        import json
        track_info = json.loads(track_info_json.decode('utf-8'))
        
        # Get timing info
        elapsed_time = lib.getElapsedTime()
        duration = lib.getDuration()
        is_playing = lib.isPlaying()
        
        return {
            "title": track_info.get("title", "Unknown"),
            "artist": track_info.get("artist", "Unknown"),
            "album": track_info.get("album", "Unknown"),
            "album_artist": track_info.get("albumArtist", None),
            "position": elapsed_time if elapsed_time >= 0 else None,
            "duration": duration if duration > 0 else None,
            "status": "Playing" if is_playing else "Paused",
            "platform": "macOS MediaRemote",
            "app_name": track_info.get("appName", None),
            "art_available": track_info.get("hasArtwork", False),
        }
    except Exception as e:
        print(f"{Colors.WARNING}MediaRemote error: {e}. Falling back to AppleScript.{Colors.ENDC}")
        return get_macos_media_info_applescript()

def get_macos_media_info_applescript():
    """Fallback method using AppleScript (limited info)"""
    try:
        # Try Spotify first
        script = '''
        if application "Spotify" is running then
            tell application "Spotify"
                if player state is playing or player state is paused then
                    set trackInfo to {name of current track, artist of current track, album of current track, player position, duration of current track, player state as string}
                    return trackInfo
                end if
            end tell
        end if
        return ""
        '''
        
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        if result.stdout.strip():
            parts = result.stdout.strip().split(", ")
            if len(parts) >= 6:
                return {
                    "title": parts[0],
                    "artist": parts[1],
                    "album": parts[2],
                    "position": float(parts[3]),
                    "duration": float(parts[4]) / 1000,  # Spotify returns milliseconds
                    "status": parts[5],
                    "platform": "macOS AppleScript (Spotify)",
                }
        
        return None
    except Exception as e:
        print(f"{Colors.FAIL}Error getting macOS media info: {e}{Colors.ENDC}")
        return None

async def get_media_info():
    """Get media info for current platform"""
    system = platform.system()
    
    if system == "Windows":
        return await get_windows_media_info()
    elif system == "Linux":
        return get_linux_media_info()
    elif system == "Darwin":
        return get_macos_media_info()
    else:
        print(f"{Colors.FAIL}Unsupported platform: {system}{Colors.ENDC}")
        return None

def display_media_info(info):
    """Display media information in a nicely formatted way"""
    if not info:
        print(f"\n{Colors.WARNING}No active media session found{Colors.ENDC}")
        return
    
    # Clear screen (optional - commented out for scrollback)
    # print("\033[2J\033[H")
    
    print_separator("═", 70)
    print(f"{Colors.BOLD}{Colors.HEADER}{'🎵  MEDIA INFORMATION':^70}{Colors.ENDC}")
    print_separator("═", 70)
    
    # Basic track info
    print_header("Track Information")
    print_field("Title:", info.get("title"))
    print_field("Artist:", info.get("artist"))
    print_field("Album:", info.get("album"))
    
    if info.get("album_artist"):
        print_field("Album Artist:", info.get("album_artist"))
    if info.get("track_number"):
        print_field("Track Number:", str(info.get("track_number")))
    if info.get("subtitle"):
        print_field("Subtitle:", info.get("subtitle"))
    if info.get("genres"):
        genres = info.get("genres")
        if isinstance(genres, list):
            genres = ", ".join(genres)
        print_field("Genres:", genres)
    
    # Playback status
    print_header("Playback Status")
    status = info.get("status", "Unknown")
    status_color = Colors.OKGREEN if "playing" in status.lower() else Colors.WARNING
    print_field("Status:", status, status_color)
    
    # Platform info
    print_field("Platform:", info.get("platform"))
    if info.get("player_name"):
        print_field("Player:", info.get("player_name"))
    if info.get("app_name"):
        print_field("Application:", info.get("app_name"))
    
    # Timeline information
    position = info.get("position")
    duration = info.get("duration")
    
    if position is not None or duration is not None:
        print_header("Timeline")
        print_field("Position:", format_time(position))
        print_field("Duration:", format_time(duration))
        
        if position is not None and duration is not None:
            remaining = duration - position
            print_field("Remaining:", format_time(remaining))
            print_progress_bar(position, duration)
    
    # Advanced timeline info (Windows SMTC)
    if info.get("timeline_start") is not None:
        print_header("Advanced Timeline Info")
        print_field("Start Time:", format_time(info.get("timeline_start")))
        print_field("End Time:", format_time(info.get("timeline_end")))
        print_field("Min Seek Time:", format_time(info.get("min_seek")))
        print_field("Max Seek Time:", format_time(info.get("max_seek")))
    
    # Additional info
    if info.get("art_url"):
        print_header("Additional")
        print_field("Album Art URL:", info.get("art_url"))
    if info.get("art_available"):
        print_header("Additional")
        print_field("Album Art:", "Available")
    
    print_separator("═", 70)
    print(f"{Colors.OKCYAN}Last updated: {time.strftime('%H:%M:%S')}{Colors.ENDC}\n")

async def main():
    """Main function"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}Song Detector Plus{Colors.ENDC}")
    print(f"{Colors.OKCYAN}Platform: {platform.system()}{Colors.ENDC}")
    print(f"{Colors.WARNING}Press Ctrl+C to exit{Colors.ENDC}\n")
    
    try:
        # Continuous monitoring - updates every second
        while True:
            # Clear screen for fresh display
            print("\033[2J\033[H", end="")
            
            info = await get_media_info()
            display_media_info(info)
            await asyncio.sleep(1)
        
    except (KeyboardInterrupt, asyncio.CancelledError):
        print(f"\n\n{Colors.OKGREEN}Exited gracefully. Goodbye! 👋{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.FAIL}Error: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # Suppress traceback on Ctrl+C
