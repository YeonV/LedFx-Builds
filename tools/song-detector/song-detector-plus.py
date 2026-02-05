#!/usr/bin/env python3
"""
Song Detector Plus - With Position Tracking
Sends track info AND position/duration data to LedFx via protocol handler
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
        exit(1)
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
        
        # Extract artist and title from the title field itself
        # YouTube titles are usually formatted as "Artist - Song Title"
        title_raw = info.title or "Unknown"
        
        if ' - ' in title_raw:
            # Split at first dash to get artist and title
            parts = title_raw.split(' - ', 1)
            artist = parts[0].strip()
            title = parts[1].strip()
        else:
            # Fallback to using the info fields
            artist = info.artist or "Unknown"
            title = title_raw
        
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
            "album": info.album_title,
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
        title = str(metadata.get('xesam:title', 'Unknown'))
        artist_list = metadata.get('xesam:artist', [])
        artist = str(artist_list[0]) if artist_list else 'Unknown'
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
        try:
            # Determine assets directory
            home = Path.home()
            assets_dir = home / "Library" / "Application Support" / ".ledfx" / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            thumbnail_path = assets_dir / "current_album_art.jpg"
            
            # Decode and save
            image_data = base64.b64decode(artwork_data)
            with open(thumbnail_path, 'wb') as f:
                f.write(image_data)
            
            return str(thumbnail_path)
        except Exception as e:
            print(f"Failed to save album art: {e}")
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
                        
                        media_info = {
                            "title": data.get('title', 'Unknown'),
                            "artist": data.get('artist', 'Unknown'),
                            "album": data.get('album', ''),
                            "thumbnail": thumbnail_path,
                            "position": data.get('elapsedTime'),  # May be available from MediaRemote
                            "duration": data.get('duration'),     # May be available from MediaRemote
                            "playing": data.get('playing', False),
                            "timestamp": time.time()
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
                            
                            media_info = {
                                "title": data.get('title', 'Unknown'),
                                "artist": data.get('artist', 'Unknown'),
                                "album": data.get('album', ''),
                                "thumbnail": thumbnail_path,
                                "position": data.get('elapsedTime'),  # May be available
                                "duration": data.get('duration'),     # May be available
                                "playing": data.get('playing', False),
                                "timestamp": time.time()
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
    url = f"ledfx://song/{device_name}/{info['artist']} - {info['title']}"
    
    # Add URI-encoded thumbnail path if available
    if info.get('thumbnail'):
        url += f"/{quote(str(info['thumbnail']), safe='')}"
    
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
        
        # Show status with position if available
        if info.get('position') is not None and info.get('duration') is not None:
            pos_str = f"{int(info['position'] // 60):02d}:{int(info['position'] % 60):02d}"
            dur_str = f"{int(info['duration'] // 60):02d}:{int(info['duration'] % 60):02d}"
            status = "▶" if info.get('playing') else "⏸"
            print(f"{status} {info['artist']} - {info['title']} [{pos_str}/{dur_str}]")
        else:
            print(f"{info['artist']} - {info['title']}")
    except Exception as e:
        print(f"Failed to send: {url}, Error: {e}")

def should_send_update(current, previous):
    """Determine if we should send an update based on state changes"""
    if previous is None:
        return True
    
    # Track changed
    if current['title'] != previous['title'] or current['artist'] != previous['artist']:
        return True
    
    # Playback state changed (play/pause)
    if current.get('playing') != previous.get('playing'):
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

async def monitor_media_info(device_name):
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
                    else:
                        send_media_info({"artist": "Unknown", "title": "No media is currently playing"}, device_name)
                    previous_info = info
                elif info:
                    # Update internal state even if not sending
                    previous_info = info
                    
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            print("Song Detector Plus exited.")

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
        try:
            home = Path.home()
            assets_dir = home / "Library" / "Application Support" / ".ledfx" / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            thumbnail_path = assets_dir / "current_album_art.jpg"
            
            image_data = base64.b64decode(artwork_data)
            with open(thumbnail_path, 'wb') as f:
                f.write(image_data)
            
            return str(thumbnail_path)
        except Exception as e:
            print(f"Failed to save album art: {e}")
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
                    
                    if payload and payload.get('playing') and payload.get('title'):
                        thumbnail_path = None
                        if payload.get('artworkData'):
                            thumbnail_path = save_artwork(payload['artworkData'])
                        
                        media_info = {
                            "title": payload.get('title', 'Unknown'),
                            "artist": payload.get('artist', 'Unknown'),
                            "album": payload.get('album', ''),
                            "thumbnail": thumbnail_path,
                            "position": payload.get('elapsedTime'),
                            "duration": payload.get('duration'),
                            "playing": payload.get('playing', False),
                            "timestamp": time.time()
                        }
                        
                        if should_send_update(media_info, previous_info):
                            send_media_info(media_info, device_name)
                            previous_info = media_info
                        else:
                            previous_info = media_info
                    else:
                        # No media playing
                        if previous_info is not None:
                            send_media_info({"artist": "Unknown", "title": "No media is currently playing"}, device_name)
                            previous_info = None
                
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"Error processing stream: {e}")
                continue
        
    except KeyboardInterrupt:
        print("Song Detector Plus exited.")
    finally:
        if process:
            process.terminate()
            process.wait()

if __name__ == "__main__":
    # Check OS support
    if platform.system() not in ["Windows", "Linux", "Darwin"]:
        print(f"⚠️  Unsupported operating system: {platform.system()}")
        print("Song Detector Plus only supports Windows, Linux, and macOS")
        exit(1)
    
    parser = argparse.ArgumentParser(description="Send media info with position tracking to a virtual device.")
    parser.add_argument("--device_name", type=str, help="The name of the virtual device to send the info to.")
    args = parser.parse_args()

    device_name = args.device_name
    if not device_name:
        device_name = "ledfxcc"
    
    print("\n" + "=" * 60)
    print("        >> Song Detector Plus (with Position Tracking)")
    print("              >> Press Ctrl+Alt+T in LedFx CC")
    print("=" * 60 + "\n")
    print(f"OS: {platform.system()} | Monitoring media with position... (Ctrl+C to stop)")
    print("")

    try:
        asyncio.run(monitor_media_info(device_name))
    except KeyboardInterrupt:
        print("Program interrupted by user.")
