#!/usr/bin/env python3
"""
Blade Song Detector - With WebSocket Connection
Connects to LedFx WebSocket API and sends track info with position/duration data
"""

import asyncio
import os
import argparse
import platform
import subprocess
import json
import shutil
import sys
import base64
import time
from pathlib import Path
from urllib.parse import quote
from datetime import datetime

# PIL for album art rendering
try:
    from PIL import Image
    PIL_AVAILABLE = True
    PIL_ERROR = None
except ImportError as e:
    PIL_AVAILABLE = False
    PIL_ERROR = str(e)

# WebSocket connection
try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("⚠️  websockets not installed. Install with: pip install websockets")

# Global WebSocket connection
ws_connection = None
client_id = None

# Global mode selection
USE_PROTOCOL = False

# ANSI color codes for terminal output - BLADE THEME
# Change these values to switch the entire theme!
class Colors:
    # Semantic color names - BLOOD & STEEL PALETTE
    PRIMARY = '\033[38;5;243m'     # Main theme color (Medium Grey)
    SECONDARY = '\033[38;5;196m'   # Secondary theme color (Blood Red)
    ACCENT = '\033[38;5;220m'      # Accent highlights (Golden Yellow)
    SUCCESS = '\033[38;5;203m'     # Success/Active state (Light Red/Pink)
    WARNING = '\033[38;5;214m'     # Warning state (Orange/Yellow)
    ERROR = '\033[38;5;196m'       # Error state (Blood Red)
    TEXT_PRIMARY = '\033[38;5;248m' # Primary text (Light Grey)
    TEXT_DIM = '\033[2m'           # Dimmed text
    SEPARATOR = '\033[38;5;237m'   # Separator lines (Dark Grey)
    BG_ACCENT = '\033[48;5;232m'   # Background accent (Near Black)
    
    # Formatting
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# TERMINAL PLUS WIDGET CONFIGURATION
# These values dynamically adjust based on terminal width
class WidgetConfig:
    @staticmethod
    def get_terminal_width():
        """Get current terminal width"""
        try:
            return shutil.get_terminal_size().columns
        except:
            return 120  # Fallback default
    
    @staticmethod
    def get_album_art_width():
        """Width of album artwork - scales with terminal"""
        term_width = WidgetConfig.get_terminal_width()
        # Album art gets 30-40% of terminal width, clamped between 40-80
        width = int(term_width * 0.35)
        return max(40, min(80, width))
    
    @staticmethod
    def get_progress_bar_width():
        """Width of progress bar - scales with terminal"""
        term_width = WidgetConfig.get_terminal_width()
        album_width = WidgetConfig.get_album_art_width()
        # Progress bar uses remaining space minus padding
        # Need buffer for: spacing (2), timestamps (5+5), separators, ANSI codes safety (15)
        width = term_width - album_width - 35
        return max(40, min(80, width))
    
    @staticmethod
    def get_title_max_width():
        """Maximum width for title text - scales with terminal"""
        term_width = WidgetConfig.get_terminal_width()
        album_width = WidgetConfig.get_album_art_width()
        # Title uses remaining space minus padding, minimum 80
        width = term_width - album_width - 30
        return max(80, width)
    
    # Keep static property for font height
    TITLE_FONT_HEIGHT = 5       # Height of title font (lines)

def format_time(seconds):
    """Format seconds into MM:SS or HH:MM:SS"""
    if seconds is None:
        return "N/A"
    from datetime import timedelta
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
    """Print a separator line - Blade style"""
    print(f"{Colors.SEPARATOR}{char * width}{Colors.ENDC}")

def print_header(text):
    """Print a header - Blade style"""
    print(f"\n{Colors.BOLD}{Colors.SECONDARY}» {text}{Colors.ENDC}")

def print_field(label, value, color=None):
    """Print a labeled field - Blade style"""
    if color is None:
        color = Colors.PRIMARY
    if value:
        print(f"{Colors.TEXT_DIM}{Colors.TEXT_PRIMARY}{label:17s}{Colors.ENDC} {color}{value}{Colors.ENDC}")
    else:
        print(f"{Colors.TEXT_DIM}{Colors.TEXT_PRIMARY}{label:17s}{Colors.ENDC} {Colors.TEXT_DIM}---{Colors.ENDC}")

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
    
    # Indent to match field alignment (18 chars for progress bar)
    indent = " " * 18
    
    print(f"\n{Colors.TEXT_DIM}{Colors.TEXT_PRIMARY}{'Progress:':17s}{Colors.ENDC}")
    print(f"{indent}{Colors.TEXT_PRIMARY}{pos_str}{Colors.ENDC} {Colors.SUCCESS}{bar}{Colors.ENDC} {Colors.TEXT_PRIMARY}{dur_str}{Colors.ENDC}")
    # Center the percentage under the progress bar
    bar_start = len(indent) + len(pos_str) + 1
    bar_center = bar_start + (width // 2)
    print(f"{' ' * bar_center}{Colors.SECONDARY}▸ {percentage:.1f}%{Colors.ENDC}")

def rgb_to_ansi(r, g, b):
    """Convert RGB values to ANSI 256-color code"""
    levels = [0, 95, 135, 175, 215, 255]
    
    def closest_level(value):
        return min(range(6), key=lambda i: abs(levels[i] - value))
    
    r_idx = closest_level(r)
    g_idx = closest_level(g)
    b_idx = closest_level(b)
    
    color_code = 16 + 36 * r_idx + 6 * g_idx + b_idx
    return color_code

def text_to_ansi_art(text, max_width=60):
    """Convert text to simple consistent block font - uppercase only"""
    # Ultra-simple consistent 5-line block font
    patterns = {
        'A': [' ███  ', '█   █ ', '█████ ', '█   █ ', '█   █ '],
        'B': ['████  ', '█   █ ', '████  ', '█   █ ', '████  '],
        'C': [' ███  ', '█     ', '█     ', '█     ', ' ███  '],
        'D': ['████  ', '█   █ ', '█   █ ', '█   █ ', '████  '],
        'E': ['█████ ', '█     ', '███   ', '█     ', '█████ '],
        'F': ['█████ ', '█     ', '███   ', '█     ', '█     '],
        'G': [' ███  ', '█     ', '█  ██ ', '█   █ ', ' ███  '],
        'H': ['█   █ ', '█   █ ', '█████ ', '█   █ ', '█   █ '],
        'I': ['█████ ', '  █   ', '  █   ', '  █   ', '█████ '],
        'J': ['  ███ ', '   █  ', '   █  ', '█  █  ', ' ██   '],
        'K': ['█   █ ', '█  █  ', '███   ', '█  █  ', '█   █ '],
        'L': ['█     ', '█     ', '█     ', '█     ', '█████ '],
        'M': ['█   █ ', '██ ██ ', '█ █ █ ', '█   █ ', '█   █ '],
        'N': ['█   █ ', '██  █ ', '█ █ █ ', '█  ██ ', '█   █ '],
        'O': [' ███  ', '█   █ ', '█   █ ', '█   █ ', ' ███  '],
        'P': ['████  ', '█   █ ', '████  ', '█     ', '█     '],
        'Q': [' ███  ', '█   █ ', '█   █ ', '█  █  ', ' ██ █ '],
        'R': ['████  ', '█   █ ', '████  ', '█  █  ', '█   █ '],
        'S': [' ███  ', '█     ', ' ███  ', '    █ ', '████  '],
        'T': ['█████ ', '  █   ', '  █   ', '  █   ', '  █   '],
        'U': ['█   █ ', '█   █ ', '█   █ ', '█   █ ', ' ███  '],
        'V': ['█   █ ', '█   █ ', '█   █ ', ' █ █  ', '  █   '],
        'W': ['█   █ ', '█   █ ', '█ █ █ ', '██ ██ ', '█   █ '],
        'X': ['█   █ ', ' █ █  ', '  █   ', ' █ █  ', '█   █ '],
        'Y': ['█   █ ', ' █ █  ', '  █   ', '  █   ', '  █   '],
        'Z': ['█████ ', '   █  ', '  █   ', ' █    ', '█████ '],
        '0': [' ███  ', '█   █ ', '█ █ █ ', '█   █ ', ' ███  '],
        '1': ['  █   ', ' ██   ', '  █   ', '  █   ', '█████ '],
        '2': [' ███  ', '█   █ ', '   █  ', '  █   ', '█████ '],
        '3': ['████  ', '    █ ', ' ███  ', '    █ ', '████  '],
        '4': ['█   █ ', '█   █ ', '█████ ', '    █ ', '    █ '],
        '5': ['█████ ', '█     ', '████  ', '    █ ', '████  '],
        '6': [' ███  ', '█     ', '████  ', '█   █ ', ' ███  '],
        '7': ['█████ ', '    █ ', '   █  ', '  █   ', '  █   '],
        '8': [' ███  ', '█   █ ', ' ███  ', '█   █ ', ' ███  '],
        '9': [' ███  ', '█   █ ', ' ████ ', '    █ ', ' ███  '],
        ' ': ['      ', '      ', '      ', '      ', '      '],
        '-': ['      ', '      ', '█████ ', '      ', '      '],
        '(': ['  █   ', ' █    ', ' █    ', ' █    ', '  █   '],
        ')': ['  █   ', '   █  ', '   █  ', '   █  ', '  █   '],
        '.': ['      ', '      ', '      ', '      ', '  █   '],
        ',': ['      ', '      ', '      ', '   █  ', '  █   '],
        '!': ['  █   ', '  █   ', '  █   ', '      ', '  █   '],
        '?': [' ███  ', '█   █ ', '   █  ', '      ', '  █   '],
        '\'': [' █    ', '  █   ', '      ', '      ', '      '],
        '"': ['█ █   ', '█ █   ', '      ', '      ', '      '],
        '&': [' ██   ', '█  █  ', ' ██   ', '█  █  ', ' ██ █ '],
    }
    
    # Truncate text if too long
    if len(text) > max_width // 7:  # Each char is ~7 units wide
        text = text[:max_width // 7 - 1] + '…'
    
    # Build 5 lines - force uppercase for consistent clean look
    lines = ['', '', '', '', '']
    for char in text.upper():
        if char in patterns:
            pattern = patterns[char]
            for i in range(5):
                lines[i] += pattern[i] + ' '
        else:
            # Unknown character, use space
            for i in range(5):
                lines[i] += '      '
    
    return lines

def render_album_art_ansi(image_path, width=None):
    """Render album art as ANSI colored blocks - returns list of lines for side-by-side layout"""
    if width is None:
        width = WidgetConfig.get_album_art_width()
    
    if not PIL_AVAILABLE or not os.path.exists(image_path):
        return None
    
    try:
        img = Image.open(image_path)
        aspect_ratio = img.height / img.width
        height = int(width * aspect_ratio * 0.5)
        
        img = img.resize((width, height), Image.Resampling.LANCZOS)
        img = img.convert('RGB')
        pixels = img.load()
        
        # Build lines for album art
        lines = []
        lines.append(f"{Colors.SEPARATOR}{'─' * width}{Colors.ENDC}")
        
        for y in range(height):
            line = ""
            for x in range(width):
                r, g, b = pixels[x, y]
                color_code = rgb_to_ansi(r, g, b)
                line += f"\033[48;5;{color_code}m \033[0m"
            lines.append(line)
        
        lines.append(f"{Colors.SEPARATOR}{'─' * width}{Colors.ENDC}")
        return lines
    except Exception:
        return None

def display_player_widget(info, artwork_lines, scroll_offset=0):
    """Display a compact music player widget with album art on left, info on right"""
    if not info:
        return
    
    # Branding text at the top
    print(f"\033[38;5;235mBlade Song Detector{Colors.ENDC}")
    
    # Build info lines for right side
    info_lines = []
    info_lines.append("")  # spacing
    
    # Artist (no label, just value)
    artist = info.get("artist", "Unknown Artist")
    info_lines.append(f"{Colors.ACCENT}{artist}{Colors.ENDC}")
    info_lines.append("")
    
    # Title as ANSI art (larger appearance)
    title = info.get("title", "Unknown Title")
    title_lines = text_to_ansi_art(title, max_width=999999)  # Don't truncate, we'll scroll instead
    
    # Check if scrolling is needed
    title_width = len(title_lines[0]) if title_lines else 0
    max_title_width = WidgetConfig.get_title_max_width()
    needs_scroll = title_width > max_title_width
    
    if needs_scroll:
        # Apply horizontal scroll by slicing each line
        scrolled_lines = []
        for line in title_lines:
            # Add some spacing at the end and loop around
            extended_line = line + "     " + line  # Add spacing then repeat for seamless loop
            visible_part = extended_line[scroll_offset:scroll_offset + max_title_width]
            scrolled_lines.append(visible_part)
        title_lines = scrolled_lines
    
    for line in title_lines:
        info_lines.append(f"{Colors.BOLD}{Colors.SUCCESS}{line}{Colors.ENDC}")
    info_lines.append("")
    info_lines.append("")  # Extra spacing before progress bar
    
    # Progress bar (no label)
    position = info.get("position")
    duration = info.get("duration")
    
    if position is not None and duration is not None and duration > 0:
        progress = position / duration
        bar_width = WidgetConfig.get_progress_bar_width()
        filled = int(bar_width * progress)
        bar = "█" * filled + "░" * (bar_width - filled)
        
        pos_str = format_time(position)
        dur_str = format_time(duration)
        
        info_lines.append(f"{Colors.TEXT_PRIMARY}{pos_str}{Colors.ENDC} {Colors.SUCCESS}{bar}{Colors.ENDC} {Colors.TEXT_PRIMARY}{dur_str}{Colors.ENDC}")
    
    # Print side-by-side with vertical centering
    if artwork_lines:
        # Calculate vertical centering
        art_height = len(artwork_lines)
        info_height = len(info_lines)
        
        if art_height > info_height:
            # Center info vertically
            padding_top = (art_height - info_height) // 2
            padding_bottom = art_height - info_height - padding_top
            info_lines = [''] * padding_top + info_lines + [''] * padding_bottom
        elif info_height > art_height:
            # Center art vertically
            padding_top = (info_height - art_height) // 2
            padding_bottom = info_height - art_height - padding_top
            art_width = WidgetConfig.get_album_art_width()
            artwork_lines = [' ' * art_width] * padding_top + artwork_lines + [' ' * art_width] * padding_bottom
        
        # Print side by side
        print()
        for art_line, info_line in zip(artwork_lines, info_lines):
            print(f"{art_line}  {info_line}")
        print()
    else:
        # No artwork, just print info
        print()
        for line in info_lines:
            print(line)
        print()

def display_media_info_terminal(info):
    """Display media information in terminal with nice formatting"""
    if not info:
        print(f"\n{Colors.WARNING}No active media session found{Colors.ENDC}")
        return
    
    
    print_separator("▬", 70)
    print(f"{Colors.BOLD}{Colors.SECONDARY}╔{'═' * 68}╗{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.SECONDARY}║{Colors.SUCCESS}{'⚡ BLADE MEDIA TRACKER ⚡':^66}{Colors.SECONDARY}║{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.SECONDARY}╚{'═' * 68}╝{Colors.ENDC}")
    print_separator("▬", 70)
    
    # Basic track info
    print_header("TRACK DATA")
    print_field("Title:", info.get("title"), Colors.ACCENT)
    print_field("Artist:", info.get("artist"), Colors.ACCENT)
    
    # Playback status
    print_header("STATUS")
    status = "▶ ACTIVE" if info.get("playing") else "⏸ PAUSED"
    status_color = Colors.SUCCESS if info.get("playing") else Colors.WARNING
    print_field("Status:", status, status_color)
    print_field("Platform:", f"{platform.system()}", Colors.TEXT_PRIMARY)
    
    # Timeline information
    position = info.get("position")
    duration = info.get("duration")
    
    if position is not None or duration is not None:
        print_header("TIMELINE")
        print_field("Position:", format_time(position), Colors.SUCCESS)
        print_field("Duration:", format_time(duration), Colors.TEXT_PRIMARY)
        
        if position is not None and duration is not None:
            remaining = duration - position
            print_field("Remaining:", format_time(remaining), Colors.SECONDARY)
            print_progress_bar(position, duration)
    
    print_separator("▬", 70)
    print(f"{Colors.TEXT_DIM}{Colors.TEXT_PRIMARY}[{time.strftime('%H:%M:%S')}]{Colors.ENDC} {Colors.SUCCESS}●{Colors.ENDC} {Colors.TEXT_DIM}SYSTEM ACTIVE{Colors.ENDC}\n")

async def listen_to_websocket():
    """Listen for incoming WebSocket messages and log them"""
    global ws_connection, client_id
    
    if not ws_connection:
        return
    
    try:
        async for message in ws_connection:
            if not message:
                continue
            
            try:
                data = json.loads(message)
                if data:
                    print(f"{Colors.ACCENT}▼{Colors.ENDC} {Colors.TEXT_DIM}WS RECEIVED: {json.dumps(data, indent=2)}{Colors.ENDC}")
                    
                    # Store client_id if received
                    if data.get('event_type') == 'client_id':
                        client_id = data.get('client_id')
                        print(f"🆔 Assigned Client ID: {client_id}")
            except json.JSONDecodeError as e:
                print(f"{Colors.WARNING}⚠ Parse error:{Colors.ENDC} {Colors.TEXT_DIM}{e}{Colors.ENDC}")
                print(f"{Colors.TEXT_DIM}    Raw message: {message}{Colors.ENDC}")
    except websockets.exceptions.ConnectionClosed:
        print(f"{Colors.WARNING}⚠ WebSocket connection closed{Colors.ENDC}")
        ws_connection = None
    except Exception as e:
        print(f"{Colors.ERROR}✖ WebSocket listener error:{Colors.ENDC} {Colors.TEXT_DIM}{e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        ws_connection = None

async def connect_to_ledfx():
    """Connect to LedFx WebSocket API at ws://localhost:8888/api/websocket"""
    global ws_connection
    
    if not WEBSOCKETS_AVAILABLE:
        print("❌ Cannot connect to LedFx: websockets module not installed")
        return None
    
    try:
        print(f"{Colors.ACCENT}▸{Colors.ENDC} {Colors.TEXT_DIM}Connecting to LedFx WebSocket at ws://localhost:8888/api/websocket...{Colors.ENDC}")
        ws_connection = await websockets.connect("ws://localhost:8888/api/websocket")
        print(f"{Colors.SUCCESS}✓ Connected{Colors.ENDC} {Colors.TEXT_DIM}- WebSocket link established{Colors.ENDC}")
        
        # Start listening in background
        asyncio.create_task(listen_to_websocket())
        
        return ws_connection
    except Exception as e:
        print(f"{Colors.ERROR}✖ Connection failed:{Colors.ENDC} {Colors.TEXT_DIM}{e}{Colors.ENDC}")
        ws_connection = None
        return None

async def send_to_websocket(data):
    """Send data to LedFx via WebSocket"""
    global ws_connection
    
    # Skip WebSocket in CC mode (protocol only)
    if USE_PROTOCOL:
        return False
    
    if not ws_connection:
        return False
    
    try:
        # Format message according to LedFx WebSocket schema
        message = {
            "id": 1,
            "type": "song_info",
            **data
        }
        message_str = json.dumps(message)
        print(f"{Colors.SUCCESS}▲{Colors.ENDC} {Colors.TEXT_DIM}WS SENDING: {message_str}{Colors.ENDC}")
        await ws_connection.send(message_str)
        return True
    except Exception as e:
        print(f"{Colors.ERROR}✖ Send failed:{Colors.ENDC} {Colors.TEXT_DIM}{e}{Colors.ENDC}")
        ws_connection = None
        return False

def parse_time_value(value):
    """Parse time values that may have 's' suffix (e.g., '5081.3s' -> 5081.3)"""
    if value is None:
        return None
    if isinstance(value, str):
        return float(value.rstrip('s'))
    return float(value)

# Platform-specific imports
if platform.system() == "Windows":
    from winsdk.windows.media.control import \
        GlobalSystemMediaTransportControlsSessionManager as MediaManager
    from winsdk.windows.storage.streams import DataReader
elif platform.system() == "Linux":
    try:
        import dbus
    except ImportError:
        print("⚠️  dbus-python not installed. Install with: pip install dbus-python")
        sys.exit(1)
elif platform.system() == "Darwin":
    # macOS - uses subprocess for AppleScript, no additional imports needed
    pass

async def get_windows_media_info():
    """Get current media info on Windows using WinSDK - WITH POSITION TRACKING"""
    sessions = await MediaManager.request_async()
    current_session = sessions.get_current_session()
    if current_session:
        info = await current_session.try_get_media_properties_async()
        
        # Get timeline properties for position tracking
        timeline = current_session.get_timeline_properties()
        playback_info = current_session.get_playback_info()
        
        # Get thumbnail/album art
        thumbnail_path = None
        if info.thumbnail:
            try:
                thumb_stream = await info.thumbnail.open_read_async()
                reader = DataReader(thumb_stream)
                await reader.load_async(thumb_stream.size)
                
                # Save thumbnail to LedFx assets directory
                appdata = Path(os.getenv('APPDATA'))
                assets_dir = appdata / ".ledfx" / "assets"
                assets_dir.mkdir(parents=True, exist_ok=True)
                thumbnail_path = assets_dir / "current_album_art.jpg"
                
                buffer = reader.read_buffer(thumb_stream.size)
                with open(thumbnail_path, 'wb') as f:
                    f.write(bytearray(buffer))
                
                reader.close()
                thumb_stream.close()
            except Exception as e:
                print(f"Failed to save album art: {e}")
        
        # Match song-detector-plus.py logic: always split title on ' - ' if present
        title_raw = info.title or "Unknown"
        if ' - ' in title_raw:
            parts = title_raw.split(' - ', 1)
            artist = parts[0].strip()
            title = parts[1].strip()
        else:
            artist = (info.artist or "Unknown").strip()
            title = title_raw.strip()
        # Clean up YouTube Music "Topic" artist suffix
        if artist.endswith(' - Topic'):
            artist = artist[:-8].strip()
        artist = artist.strip(' -')
        title = title.strip(' -')
        
        # Extract position and duration
        position_seconds = None
        duration_seconds = None
        is_playing = False
        
        if timeline:
            if hasattr(timeline, 'position') and timeline.position is not None:
                position_seconds = timeline.position.total_seconds()
            if hasattr(timeline, 'end_time') and timeline.end_time is not None and \
               hasattr(timeline, 'start_time') and timeline.start_time is not None:
                duration_seconds = (timeline.end_time - timeline.start_time).total_seconds()
        
        if playback_info:
            playback_status = playback_info.playback_status
            is_playing = (playback_status == 4)  # 4 = Playing
        
        return {
            "title": title,
            "artist": artist,
            "album": info.album_title if info.album_title else "",
            "thumbnail": str(thumbnail_path) if thumbnail_path else None,
            "position": position_seconds,
            "duration": duration_seconds,
            "playing": is_playing,
            "timestamp": time.time()
        }
    return None

def get_linux_media_info():
    """Get current media info on Linux using MPRIS D-Bus - WITH POSITION TRACKING"""
    try:
        session_bus = dbus.SessionBus()
        
        # Find all MPRIS media players
        players = [s for s in session_bus.list_names() if s.startswith('org.mpris.MediaPlayer2.')]
        
        if not players:
            return None
            
        # Use the first active player
        player_bus = session_bus.get_object(players[0], '/org/mpris/MediaPlayer2')
        properties = dbus.Interface(player_bus, 'org.freedesktop.DBus.Properties')
        metadata = properties.Get('org.mpris.MediaPlayer2.Player', 'Metadata')
        playback_status = properties.Get('org.mpris.MediaPlayer2.Player', 'PlaybackStatus')
        
        # Extract metadata
        title_raw = str(metadata.get('xesam:title', 'Unknown'))
        if ' - ' in title_raw:
            parts = title_raw.split(' - ', 1)
            artist = parts[0].strip()
            title = parts[1].strip()
        else:
            artist_list = metadata.get('xesam:artist', [])
            artist = str(artist_list[0]).strip() if artist_list and str(artist_list[0]).strip() else "Unknown"
            title = title_raw.strip()
        # Clean up YouTube Music "Topic" artist suffix
        if artist.endswith(' - Topic'):
            artist = artist[:-8].strip()
        artist = artist.strip(' -')
        title = title.strip(' -')
        album = str(metadata.get('xesam:album', ''))
        art_url = str(metadata.get('mpris:artUrl', ''))
        
        # Get position (in microseconds)
        position_seconds = None
        try:
            position_us = properties.Get('org.mpris.MediaPlayer2.Player', 'Position')
            position_seconds = position_us / 1_000_000
        except:
            pass
        
        # Duration (in microseconds)
        duration_us = metadata.get('mpris:length', None)
        duration_seconds = duration_us / 1_000_000 if duration_us else None
        
        # Playback status
        is_playing = (playback_status == 'Playing')
        
        # Download album art if available
        thumbnail_path = None
        if art_url:
            try:
                import urllib.request
                
                # Determine config directory
                config_home = os.getenv('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
                assets_dir = Path(config_home) / ".ledfx" / "assets"
                assets_dir.mkdir(parents=True, exist_ok=True)
                thumbnail_path = assets_dir / "current_album_art.jpg"
                
                # Download album art
                if art_url.startswith('file://'):
                    # Local file
                    import shutil
                    local_path = art_url.replace('file://', '')
                    shutil.copy(local_path, thumbnail_path)
                else:
                    # Remote URL
                    urllib.request.urlretrieve(art_url, thumbnail_path)
            except Exception as e:
                print(f"Failed to save album art: {e}")
        
        return {
            "title": title,
            "artist": artist,
            "album": album,
            "thumbnail": str(thumbnail_path) if thumbnail_path else None,
            "position": position_seconds,
            "duration": duration_seconds,
            "playing": is_playing,
            "timestamp": time.time()
        }
    except Exception as e:
        print(f"Failed to get media info: {e}")
        return None

def get_macos_media_info():
    """Get current media info on macOS - WITH POSITION TRACKING (if available)"""
    
    # Helper function to get script directory (works with PyInstaller)
    def get_resource_path(relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller"""
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, relative_path)
    
    def save_artwork(artwork_data):
        """Save base64-encoded artwork to file"""
        if not artwork_data:
            return None
        
        try:
            # Save to ~/.ledfx/assets/ (standard location, works with core)
            home = Path.home()
            assets_dir = home / ".ledfx" / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            thumbnail_path = assets_dir / "current_album_art.jpg"
            
            # Decode and save
            image_data = base64.b64decode(artwork_data)
            image_hash = hash(image_data) % 1000000  # Simple hash for comparison
            
            with open(thumbnail_path, 'wb') as f:
                f.write(image_data)
            
            return str(thumbnail_path)
        except Exception as e:
            print(f"❌ Failed to save album art: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    try:
        media_info = None
        
        # Strategy 1: Try system-installed media-control (if available)
        if shutil.which('media-control'):
            try:
                result = subprocess.run(
                    ['media-control', 'get'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    data = json.loads(result.stdout.strip())
                    if data and data.get('playing') and data.get('title'):
                        thumbnail_path = None
                        if data.get('artworkData'):
                            thumbnail_path = save_artwork(data['artworkData'])
                        
                        # Match song-detector-plus.py logic: always split title on ' - ' if present
                        title_raw = data.get('title', 'Unknown')
                        if ' - ' in title_raw:
                            parts = title_raw.split(' - ', 1)
                            artist = parts[0].strip()
                            title = parts[1].strip()
                        else:
                            artist = (data.get('artist', 'Unknown') or 'Unknown').strip()
                            title = title_raw.strip()
                        if artist.endswith(' - Topic'):
                            artist = artist[:-8].strip()
                        artist = artist.strip(' -')
                        title = title.strip(' -')
                        # Parse ISO timestamp or use current time
                        timestamp_str = data.get('timestamp')
                        if timestamp_str:
                            try:
                                from dateutil.parser import parse as parse_iso
                                timestamp = parse_iso(timestamp_str).timestamp()
                            except ImportError:
                                timestamp = time.time()
                        else:
                            timestamp = time.time()
                        media_info = {
                            "title": title,
                            "artist": artist,
                            "album": data.get('album', ''),
                            "thumbnail": thumbnail_path,
                            "position": parse_time_value(data.get('elapsedTime')),
                            "duration": parse_time_value(data.get('duration')),
                            "playing": data.get('playing', False),
                            "timestamp": timestamp,
                            "content_id": data.get('contentItemIdentifier')
                        }
            except Exception as e:
                print(f"media-control failed: {e}")
        
        # Strategy 2: Use bundled mediaremote-adapter framework
        if not media_info:
            try:
                framework_path = get_resource_path('MediaRemoteAdapter.framework')
                perl_script = get_resource_path('mediaremote-adapter.pl')
                
                if os.path.exists(framework_path) and os.path.exists(perl_script):
                    result = subprocess.run(
                        ['/usr/bin/perl', perl_script, framework_path, 'get'],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    
                    if result.returncode == 0 and result.stdout.strip():
                        data = json.loads(result.stdout.strip())
                        if data and data.get('playing') and data.get('title'):
                            thumbnail_path = None
                            if data.get('artworkData'):
                                thumbnail_path = save_artwork(data['artworkData'])
                            
                            # Match song-detector-plus.py logic: always split title on ' - ' if present
                            title_raw = data.get('title', 'Unknown')
                            if ' - ' in title_raw:
                                parts = title_raw.split(' - ', 1)
                                artist = parts[0].strip()
                                title = parts[1].strip()
                            else:
                                artist = (data.get('artist', 'Unknown') or 'Unknown').strip()
                                title = title_raw.strip()
                            if artist.endswith(' - Topic'):
                                artist = artist[:-8].strip()
                            artist = artist.strip(' -')
                            title = title.strip(' -')
                            # Parse ISO timestamp or use current time
                            timestamp_str = data.get('timestamp')
                            if timestamp_str:
                                try:
                                    from dateutil.parser import parse as parse_iso
                                    timestamp = parse_iso(timestamp_str).timestamp()
                                except ImportError:
                                    timestamp = time.time()
                            else:
                                timestamp = time.time()
                            media_info = {
                                "title": title,
                                "artist": artist,
                                "album": data.get('album', ''),
                                "thumbnail": thumbnail_path,
                                "position": parse_time_value(data.get('elapsedTime')),
                                "duration": parse_time_value(data.get('duration')),
                                "playing": data.get('playing', False),
                                "timestamp": timestamp,
                                "content_id": data.get('contentItemIdentifier')
                            }
            except Exception as e:
                print(f"bundled mediaremote-adapter failed: {e}")
        
        return media_info
        
    except Exception as e:
        print(f"Failed to get media info: {e}")
        return None

async def get_current_media_info():
    """Get current media info (OS-aware)"""
    if platform.system() == "Windows":
        return await get_windows_media_info()
    elif platform.system() == "Linux":
        return get_linux_media_info()
    elif platform.system() == "Darwin":
        return get_macos_media_info()
    else:
        print(f"⚠️  Unsupported OS: {platform.system()}")
        return None

def send_media_info(info, device_name):
    """Send media info via protocol handler - WITH POSITION DATA"""
    # Only send protocol if USE_PROTOCOL is enabled (LedFx CC mode)
    if USE_PROTOCOL:
        artist_title = f"{info['artist']} - {info['title']}"
        url = f"ledfx://song/{device_name}/{artist_title}"
        
        # Add just the filename (backend serves from ~/.ledfx/assets/)
        if info.get('thumbnail'):
            thumbnail_filename = Path(info['thumbnail']).name
            url += f"/{thumbnail_filename}"
        
        # Add position tracking query parameters
        query_params = []
        if info.get('position') is not None:
            query_params.append(f"position={info['position']}")
        if info.get('duration') is not None:
            query_params.append(f"duration={info['duration']}")
        if info.get('playing') is not None:
            query_params.append(f"playing={'true' if info['playing'] else 'false'}")
        if info.get('timestamp') is not None:
            query_params.append(f"timestamp={info['timestamp']}")    
        # Add cache-buster for thumbnail to force browser reload
        if info.get('thumbnail'):
            query_params.append(f"_cb={int(time.time() * 1000)}")    
        if query_params:
            url += "?" + "&".join(query_params)
        
        try:
            if platform.system() == "Windows":
                os.startfile(url)
            elif platform.system() == "Linux":
                subprocess.run(['xdg-open', url], check=False)
            elif platform.system() == "Darwin":
                subprocess.run(['open', url], check=False)
            else:
                print(f"⚠️  Cannot open URL on {platform.system()}")
                return
        except Exception as e:
            print(f"Failed to send: {url}, Error: {e}")
    
    # Show status with position if available
    if info.get('position') is not None and info.get('duration') is not None:
        pos_str = f"{int(info['position'] // 60):02d}:{int(info['position'] % 60):02d}"
        dur_str = f"{int(info['duration'] // 60):02d}:{int(info['duration'] % 60):02d}"
        status = "▶" if info.get('playing') else "⏸"
        print(f"{status} {info['artist']} - {info['title']} [{pos_str}/{dur_str}]")
    else:
        print(f"{info['artist']} - {info['title']}")

def should_send_update(current, previous):
    """Determine if we should send an update based on state changes"""
    if previous is None:
        return True
    
    # Track changed (use content_id for robust detection)
    curr_content_id = current.get('content_id')
    prev_content_id = previous.get('content_id')
    if curr_content_id and prev_content_id and curr_content_id != prev_content_id:
        return True
    
    # Fallback: Track changed (title/artist comparison)
    if current['title'] != previous['title'] or current['artist'] != previous['artist']:
        return True
    
    # Playback state changed (play/pause)
    if current.get('playing') != previous.get('playing'):
        return True
    
    # Artwork changed
    if current.get('thumbnail') != previous.get('thumbnail'):
        return True
    
    # Position jumped significantly (seek detected)
    curr_pos = current.get('position')
    prev_pos = previous.get('position')
    if curr_pos is not None and prev_pos is not None:
        # If position jumped more than 2 seconds (accounting for polling delay)
        time_diff = current.get('timestamp', 0) - previous.get('timestamp', 0)
        expected_pos = prev_pos + (time_diff if previous.get('playing') else 0)
        if abs(curr_pos - expected_pos) > 2.0:
            return True
    
    return False

async def monitor_media_info_terminal():
    """Monitor and display media info in terminal only"""
    try:
        while True:
            # Clear screen for fresh display
            print("\033[2J\033[H", end="")
            
            info = await get_current_media_info()
            if info:
                display_media_info_terminal(info)
            else:
                print(f"\n{Colors.TEXT_DIM}{Colors.TEXT_PRIMARY}[ NO SIGNAL DETECTED ]{Colors.ENDC}")
                print(f"{Colors.TEXT_DIM}{Colors.TEXT_PRIMARY}[{time.strftime('%H:%M:%S')}]{Colors.ENDC} {Colors.WARNING}●{Colors.ENDC} {Colors.TEXT_DIM}AWAITING MEDIA...{Colors.ENDC}\n")
            
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass

async def monitor_media_info_terminal_plus():
    """Monitor and display media info in terminal with album art - TERMINAL PLUS MODE"""
    artwork_path = os.path.expanduser(r"~\AppData\Roaming\.ledfx\assets\current_album_art.jpg")
    if platform.system() == "Linux":
        artwork_path = os.path.expanduser("~/.ledfx/assets/current_album_art.jpg")
    elif platform.system() == "Darwin":
        artwork_path = os.path.expanduser("~/Library/Application Support/.ledfx/assets/current_album_art.jpg")
    
    # Clear screen once before starting
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Track start time to calculate elapsed time when position isn't updating
    last_track_id = None
    track_start_time = None
    track_start_position = None
    scroll_offset = 0  # For horizontal title scrolling
    
    try:
        while True:
            # Clear screen for fresh display
            print("\033[2J\033[H", end="")
            
            info = await get_current_media_info()
            if info:
                # Track ID for detecting song changes
                current_track_id = f"{info.get('artist', '')}-{info.get('title', '')}"
                
                # If track changed, reset timing and scroll
                if current_track_id != last_track_id:
                    last_track_id = current_track_id
                    track_start_time = time.time()
                    track_start_position = info.get('position', 0) or 0
                    scroll_offset = 0  # Reset scroll for new track
                
                # If position isn't updating from API and track is playing, calculate manually
                if info.get('playing') and track_start_time is not None:
                    elapsed = time.time() - track_start_time
                    calculated_position = track_start_position + elapsed
                    
                    # Use calculated position if API position is 0 or not updating
                    api_position = info.get('position', 0) or 0
                    if api_position == 0 or abs(api_position - calculated_position) > 5:
                        info['position'] = calculated_position
                
                # Render album art and get lines
                artwork_lines = None
                if PIL_AVAILABLE and os.path.exists(artwork_path):
                    artwork_lines = render_album_art_ansi(artwork_path)
                
                # Display side-by-side widget with scroll
                display_player_widget(info, artwork_lines, scroll_offset)
                
                # Increment scroll offset for next frame (2 chars per update for smooth scroll)
                scroll_offset += 3
            else:
                print(f"\n{Colors.TEXT_DIM}{Colors.TEXT_PRIMARY}[ NO SIGNAL DETECTED ]{Colors.ENDC}")
                print(f"{Colors.TEXT_DIM}{Colors.TEXT_PRIMARY}[{time.strftime('%H:%M:%S')}]{Colors.ENDC} {Colors.WARNING}●{Colors.ENDC} {Colors.TEXT_DIM}AWAITING MEDIA...{Colors.ENDC}\n")
                last_track_id = None
                track_start_time = None
            
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass

async def monitor_media_info(device_name):
    # Connect to LedFx WebSocket only in Core mode (not in CC mode)
    if not USE_PROTOCOL:
        await connect_to_ledfx()
    
    if platform.system() == "Darwin":
        # macOS: Use streaming mode for real-time updates
        monitor_media_info_macos_stream(device_name)
    else:
        # Windows/Linux: Poll every second
        previous_info = None
        try:
            while True:
                info = await get_current_media_info()
                
                if should_send_update(info, previous_info) if info else previous_info is not None:
                    if info:
                        send_media_info(info, device_name)
                        # Also send to WebSocket if connected
                        await send_to_websocket(info)
                    else:
                        send_media_info({"artist": "Unknown", "title": "No media is currently playing"}, device_name)
                    previous_info = info
                elif info:
                    # Update internal state even if not sending
                    previous_info = info
                    
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            print(f"{Colors.TEXT_DIM}System terminated{Colors.ENDC}")

def monitor_media_info_macos_stream(device_name):
    """Monitor media info on macOS using stream mode for real-time updates"""
    
    def get_resource_path(relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller"""
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, relative_path)
    
    def save_artwork(artwork_data):
        """Save base64-encoded artwork to file"""
        if not artwork_data:
            return None
        
        try:
            # Save to ~/.ledfx/assets/ (standard location, works with core)
            home = Path.home()
            assets_dir = home / ".ledfx" / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            thumbnail_path = assets_dir / "current_album_art.jpg"
            
            image_data = base64.b64decode(artwork_data)
            
            with open(thumbnail_path, 'wb') as f:
                f.write(image_data)
            
            return str(thumbnail_path)
        except Exception as e:
            print(f"❌ Failed to save album art: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    previous_info = None
    process = None
    
    try:
        # Try system media-control first
        if shutil.which('media-control'):
            process = subprocess.Popen(
                ['media-control', 'stream'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
        else:
            # Use bundled mediaremote-adapter
            framework_path = get_resource_path('MediaRemoteAdapter.framework')
            perl_script = get_resource_path('mediaremote-adapter.pl')
            
            if os.path.exists(framework_path) and os.path.exists(perl_script):
                process = subprocess.Popen(
                    ['/usr/bin/perl', perl_script, framework_path, 'stream'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
        
        if not process:
            print("⚠️  No media-control method available on macOS")
            return
        
        # Read streaming output line by line
        for line in process.stdout:
            try:
                line = line.strip()
                if not line:
                    continue
                
                data = json.loads(line)
                
                # Check if it's a data payload (stream outputs multiple types)
                if data.get('type') == 'data':
                    payload = data.get('payload', {})
                    
                    # Skip empty payloads completely
                    if not payload:
                        continue
                    
                    # Check if media stopped playing
                    # BUT: Only if 'playing' field is explicitly present (diff:true may omit it)
                    if 'playing' in payload and not payload.get('playing'):
                        # Only send "no media" notification once when transitioning from playing
                        if previous_info is not None and previous_info.get('playing'):
                            send_media_info({"artist": "Unknown", "title": "No media is currently playing"}, device_name)
                            previous_info = None
                        continue
                    
                    # Early filter: ignore if no title AND not a diff:true event
                    # (diff:true events may contain only artwork)
                    if not payload.get('title') and not data.get('diff'):
                        continue
                    
                    # Parse artist
                    artist = payload.get('artist', 'Unknown')
                    if artist.endswith(' - Topic'):
                        artist = artist[:-8].strip()
                    
                    # Parse ISO timestamp or use current time
                    timestamp_str = payload.get('timestamp')
                    if timestamp_str:
                        try:
                            from dateutil.parser import parse as parse_iso
                            timestamp = parse_iso(timestamp_str).timestamp()
                        except ImportError:
                            timestamp = time.time()
                    else:
                        timestamp = time.time()
                    
                    # Build media_info - merge with previous to handle diff:true events
                    # BUT: Don't merge if track changed (different title/artist)
                    should_merge = False
                    if previous_info and data.get('diff'):
                        # Check if track changed before merging
                        prev_title = previous_info.get('title', '')
                        prev_artist = previous_info.get('artist', '')
                        curr_title = payload.get('title', prev_title)  # Use prev if not in payload
                        curr_artist = artist if artist != 'Unknown' else previous_info.get('artist', '')
                        
                        # Only merge if same track (title/artist unchanged)
                        if curr_title == prev_title and curr_artist == prev_artist:
                            should_merge = True
                    
                    if should_merge:
                        # diff:true - merge update with previous state (SAME track)
                        media_info = previous_info.copy()
                        
                        # Handle artwork if present in diff
                        if payload.get('artworkData'):
                            thumbnail_path = save_artwork(payload['artworkData'])
                            media_info['thumbnail'] = thumbnail_path
                        
                        # Update only fields that are present in payload
                        if 'title' in payload:
                            media_info['title'] = payload['title']
                        if artist != 'Unknown':
                            media_info['artist'] = artist
                        if 'album' in payload:
                            media_info['album'] = payload.get('album', '')
                        if 'elapsedTime' in payload:
                            media_info['position'] = parse_time_value(payload['elapsedTime'])
                        if 'duration' in payload:
                            media_info['duration'] = parse_time_value(payload['duration'])
                        if 'playing' in payload:
                            media_info['playing'] = payload['playing']
                        if timestamp_str:
                            media_info['timestamp'] = timestamp
                        if 'contentItemIdentifier' in payload:
                            media_info['content_id'] = payload['contentItemIdentifier']
                    else:
                        # diff:false or no previous - full update
                        # Handle artwork
                        thumbnail_path = None
                        if payload.get('artworkData'):
                            thumbnail_path = save_artwork(payload['artworkData'])
                        
                        media_info = {
                            "title": payload.get('title', 'Unknown'),
                            "artist": artist,
                            "album": payload.get('album', ''),
                            "thumbnail": thumbnail_path,
                            "position": parse_time_value(payload.get('elapsedTime')),
                            "duration": parse_time_value(payload.get('duration')),
                            "playing": payload.get('playing', False),
                            "timestamp": timestamp,
                            "content_id": payload.get('contentItemIdentifier')
                        }
                    
                    # Detect track change
                    track_changed = False
                    if previous_info:
                        prev_title = previous_info.get('title', '')
                        prev_artist = previous_info.get('artist', '')
                        prev_content_id = previous_info.get('content_id')
                        
                        curr_title = media_info.get('title', '')
                        curr_artist = media_info.get('artist', '')
                        curr_content_id = media_info.get('content_id')
                        
                        # Track changed if title/artist/contentId different
                        if (curr_title != prev_title or 
                            curr_artist != prev_artist or 
                            (curr_content_id and prev_content_id and curr_content_id != prev_content_id)):
                            track_changed = True
                    
                    # On track change: reset position to 0 and clear old duration
                    if track_changed:
                        media_info['position'] = 0
                        # Don't inherit old track's duration if new track has no duration
                        if media_info.get('duration', 0) == 0:
                            media_info['duration'] = 0
                    
                    # Calculate position based on timestamp (if playing and timestamp available)
                    if media_info.get('playing') and media_info.get('timestamp'):
                        elapsed_since_timestamp = time.time() - media_info['timestamp']
                        base_position = media_info.get('position', 0) or 0
                        calculated_position = base_position + elapsed_since_timestamp
                        media_info['position'] = calculated_position
                    
                    # Only send if position < duration (skip if at end)
                    # But allow 0 duration (unknown duration case)
                    duration = media_info.get('duration')
                    position = media_info.get('position')
                    
                    if duration and position and duration > 0 and position >= duration:
                        # Track at end, skip sending
                        previous_info = media_info
                        continue
                    
                    if should_send_update(media_info, previous_info):
                        send_media_info(media_info, device_name)
                        previous_info = media_info
                    else:
                        previous_info = media_info
                
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"{Colors.ERROR}✖ Stream error:{Colors.ENDC} {Colors.TEXT_DIM}{e}{Colors.ENDC}")
                continue
        
    except KeyboardInterrupt:
        print(f"\n{Colors.SUCCESS}✓ SYSTEM TERMINATED{Colors.ENDC} {Colors.TEXT_DIM}- Session ended{Colors.ENDC}")
    finally:
        if process:
            process.terminate()
            process.wait()

def show_menu(show_core_mode=False):
    """Display menu and return user selection"""
    # Clear screen before showing menu
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print(f"\n{Colors.BOLD}{Colors.SECONDARY}╔{'═' * 58}╗{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.SECONDARY}║{Colors.SUCCESS}{'⚡ BLADE SONG DETECTOR ⚡':^56}{Colors.SECONDARY}║{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.SECONDARY}╚{'═' * 58}╝{Colors.ENDC}")
    print(f"\n{Colors.TEXT_PRIMARY}{Colors.TEXT_DIM}Select operational mode:{Colors.ENDC}")
    print(f"  {Colors.SUCCESS}[1]{Colors.ENDC} {Colors.TEXT_PRIMARY}Terminal{Colors.ENDC} {Colors.TEXT_DIM}(Info){Colors.ENDC}")
    print(f"  {Colors.SUCCESS}[2]{Colors.ENDC} {Colors.TEXT_PRIMARY}Terminal Plus{Colors.ENDC} {Colors.TEXT_DIM}(Info + Album Art){Colors.ENDC}")
    print(f"  {Colors.SUCCESS}[3]{Colors.ENDC} {Colors.TEXT_PRIMARY}LedFx CC{Colors.ENDC} {Colors.TEXT_DIM}(Integration){Colors.ENDC}")
    if show_core_mode:
        print(f"  {Colors.SUCCESS}[4]{Colors.ENDC} {Colors.TEXT_PRIMARY}LedFx Core{Colors.ENDC} {Colors.TEXT_DIM}(Integration){Colors.ENDC}")
    print(f"\n{Colors.SEPARATOR}{'▬' * 60}{Colors.ENDC}")
    
    max_choice = 4 if show_core_mode else 3
    valid_choices = [str(i) for i in range(1, max_choice + 1)]
    
    while True:
        try:
            choice = input(f"{Colors.SECONDARY}▸{Colors.ENDC} Enter choice (1-{max_choice}): ").strip()
            if choice in valid_choices:
                return int(choice)
            print(f"{Colors.ERROR}✖{Colors.ENDC} {Colors.TEXT_DIM}Invalid choice. Please enter 1-{max_choice}.{Colors.ENDC}")
        except (KeyboardInterrupt, EOFError):
            print(f"\n{Colors.ERROR}✖ SYSTEM TERMINATED{Colors.ENDC}")
            sys.exit(0)

if __name__ == "__main__":
    # Check OS support
    if platform.system() not in ["Windows", "Linux", "Darwin"]:
        print(f"{Colors.ERROR}✖ Unsupported OS:{Colors.ENDC} {Colors.TEXT_DIM}{platform.system()}{Colors.ENDC}")
        print(f"{Colors.TEXT_DIM}Blade Song Detector only supports Windows, Linux, and macOS{Colors.ENDC}")
        sys.exit(1)
    
    # Parse arguments first to check for --core flag
    parser = argparse.ArgumentParser(description="Send media info with position tracking to a virtual device.")
    parser.add_argument("--device_name", type=str, help="The name of the virtual device to send the info to.")
    parser.add_argument("--core", action="store_true", help="Show advanced LedFx Core mode option in menu")
    args = parser.parse_args()
    
    # Show menu and get user choice
    choice = show_menu(show_core_mode=args.core)
    
    if choice == 1:
        # Terminal mode - display only
        print(f"\n{Colors.SEPARATOR}{'▬' * 60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.SECONDARY}▸{Colors.ENDC} {Colors.TEXT_PRIMARY}BLADE SONG DETECTOR{Colors.ENDC} {Colors.TEXT_DIM}- Terminal Mode{Colors.ENDC}")
        print(f"{Colors.TEXT_DIM}Displaying media information...{Colors.ENDC}")
        print(f"{Colors.SEPARATOR}{'▬' * 60}{Colors.ENDC}\n")
        print(f"{Colors.TEXT_DIM}OS: {platform.system()} | Mode: Terminal Display{Colors.ENDC}")
        print(f"{Colors.TEXT_DIM}Press {Colors.SECONDARY}Ctrl+C{Colors.TEXT_DIM} to terminate{Colors.ENDC}\n")
        try:
            asyncio.run(monitor_media_info_terminal())
        except KeyboardInterrupt:
            print(f"\n\n{Colors.SUCCESS}✓ SYSTEM TERMINATED{Colors.ENDC} {Colors.TEXT_DIM}- Session ended{Colors.ENDC}")
        sys.exit(0)
    elif choice == 2:
        # Terminal Plus mode - display with album art
        if not PIL_AVAILABLE:
            print(f"\n{Colors.ERROR}✖ PIL not available{Colors.ENDC}")
            if PIL_ERROR:
                print(f"{Colors.TEXT_DIM}Error: {PIL_ERROR}{Colors.ENDC}")
            print(f"{Colors.TEXT_DIM}Install with: pip install Pillow{Colors.ENDC}")
            sys.exit(1)
        print(f"\n{Colors.SEPARATOR}{'▬' * 60}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.SECONDARY}▸{Colors.ENDC} {Colors.TEXT_PRIMARY}BLADE SONG DETECTOR{Colors.ENDC} {Colors.TEXT_DIM}- Terminal Plus Mode{Colors.ENDC}")
        print(f"{Colors.TEXT_DIM}Displaying media information with album art...{Colors.ENDC}")
        print(f"{Colors.SEPARATOR}{'▬' * 60}{Colors.ENDC}\n")
        print(f"{Colors.TEXT_DIM}OS: {platform.system()} | Mode: Terminal Plus Display{Colors.ENDC}")
        print(f"{Colors.TEXT_DIM}Press {Colors.SECONDARY}Ctrl+C{Colors.TEXT_DIM} to terminate{Colors.ENDC}\n")
        try:
            asyncio.run(monitor_media_info_terminal_plus())
        except KeyboardInterrupt:
            print(f"\n\n{Colors.SUCCESS}✓ SYSTEM TERMINATED{Colors.ENDC} {Colors.TEXT_DIM}- Session ended{Colors.ENDC}")
        sys.exit(0)
    elif choice == 3:
        USE_PROTOCOL = True
        mode_name = f"{Colors.SECONDARY}LedFx CC{Colors.ENDC} {Colors.TEXT_DIM}(Protocol Handler){Colors.ENDC}"
    elif choice == 4:
        USE_PROTOCOL = False
        mode_name = f"{Colors.SUCCESS}LedFx Core{Colors.ENDC} {Colors.TEXT_DIM}(WebSocket Broadcast){Colors.ENDC}"

    device_name = args.device_name
    if not device_name:
        device_name = "ledfxcc"
    
    print(f"\n{Colors.SEPARATOR}{'▬' * 60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.SECONDARY}▸{Colors.ENDC} BLADE SONG DETECTOR - {mode_name}")
    print(f"{Colors.TEXT_DIM}Connecting to LedFx WebSocket API...{Colors.ENDC}")
    print(f"{Colors.SEPARATOR}{'▬' * 60}{Colors.ENDC}\n")
    print(f"{Colors.TEXT_DIM}OS: {platform.system()}{Colors.ENDC}")
    print(f"{Colors.TEXT_DIM}Monitoring media... Press {Colors.SECONDARY}Ctrl+C{Colors.TEXT_DIM} to stop{Colors.ENDC}\n")

    try:
        asyncio.run(monitor_media_info(device_name))
    except KeyboardInterrupt:
        print(f"\n{Colors.SUCCESS}✓ SYSTEM TERMINATED{Colors.ENDC} {Colors.TEXT_DIM}- User interrupt{Colors.ENDC}")
