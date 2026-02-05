# macOS Media Detection Implementation

## Summary
Added full macOS support to song-detector with Chrome/YouTube background tab detection and album artwork extraction.

## Problem Solved
macOS's standard `MPNowPlayingInfoCenter` API doesn't capture media from Chrome/YouTube unless the tab is active. Users need background tab detection to work seamlessly.

## Solution: mediaremote-adapter
Used [mediaremote-adapter](https://github.com/ungive/mediaremote-adapter) - a BSD 3-Clause licensed tool that bypasses Apple's MediaRemote entitlement restrictions by using the system's Perl binary (`/usr/bin/perl`) which has the necessary entitlements.

## Technical Implementation

### Architecture
**Two-tier fallback system:**
1. **Strategy 1**: Check for system-installed `media-control` (Homebrew)
2. **Strategy 2**: Use bundled `MediaRemoteAdapter.framework` (always works)

### Key Files Added
```
tools/song-detector/
├── MediaRemoteAdapter.framework/     # Compiled framework (x86_64 + arm64)
├── mediaremote-adapter.pl            # Perl interface script
└── LICENSE-mediaremote-adapter       # BSD 3-Clause license
```

### Code Changes: song-detector.py
```python
import base64  # Added for album art decoding

def get_macos_media_info():
    def get_resource_path(relative_path):
        # PyInstaller compatibility - finds bundled resources
        try:
            base_path = sys._MEIPASS  # PyInstaller temp dir
        except Exception:
            base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, relative_path)
    
    def save_artwork(artwork_data):
        # Decode base64 album art and save to:
        # ~/Library/Application Support/.ledfx/assets/current_album_art.jpg
        image_data = base64.b64decode(artwork_data)
        # ... save to file ...
    
    # Strategy 1: System media-control
    if shutil.which('media-control'):
        result = subprocess.run(['media-control', 'get'], ...)
        data = json.loads(result.stdout)
        # Extract: title, artist, album, artworkData
    
    # Strategy 2: Bundled framework
    if not media_info:
        framework_path = get_resource_path('MediaRemoteAdapter.framework')
        perl_script = get_resource_path('mediaremote-adapter.pl')
        result = subprocess.run(['/usr/bin/perl', perl_script, framework_path, 'get'], ...)
        data = json.loads(result.stdout)
        # Extract same fields + decode artwork
```

### PyInstaller Configuration: song-detector.spec
```python
import platform
import os

datas = []
if platform.system() == 'Darwin':
    framework_path = os.path.join(os.path.dirname(SPECPATH), 'MediaRemoteAdapter.framework')
    perl_script = os.path.join(os.path.dirname(SPECPATH), 'mediaremote-adapter.pl')
    
    datas.append((framework_path, 'MediaRemoteAdapter.framework'))
    datas.append((perl_script, '.'))

a = Analysis(['song-detector.py'], datas=datas, ...)
```

### CI/CD: BuildSongDetector.yml
```yaml
matrix:
  include:
    - os: macos-latest
      artifact_name: song-detector-macos

- name: Install dependencies (macOS)
  if: matrix.os == 'macos-latest'
  run: poetry install --no-interaction

- name: Build with PyInstaller
  run: poetry run pyinstaller song-detector.spec  # Uses .spec file now
```

## How It Works
1. User runs `song-detector-macos`
2. Python calls `/usr/bin/perl mediaremote-adapter.pl FRAMEWORK_PATH get`
3. Perl script dynamically loads `MediaRemoteAdapter.framework`
4. Framework accesses private `MediaRemote.framework` APIs
5. Returns JSON: `{playing, title, artist, album, artworkData, ...}`
6. Python decodes base64 `artworkData` and saves as JPEG
7. Sends URI: `ledfx://song/{device}/{artist} - {title}/{thumbnail_path}`

## Why This Works
- `/usr/bin/perl` is a system binary with MediaRemote entitlements
- Dynamically loading the framework bypasses app-level entitlement checks
- Works with any media source: Chrome, YouTube, Spotify, Music.app, etc.
- No user installation required (framework is bundled)

## Building MediaRemoteAdapter.framework
```bash
# Clone repo
git clone https://github.com/ungive/mediaremote-adapter
cd mediaremote-adapter

# Install cmake
brew install cmake

# Build
mkdir build && cd build
cmake ..
make

# Output: MediaRemoteAdapter.framework (ad-hoc signed)
```

## Album Art Storage
- **Windows**: `%APPDATA%\.ledfx\assets\current_album_art.jpg`
- **Linux**: `~/.config/.ledfx/assets/current_album_art.jpg`
- **macOS**: `~/Library/Application Support/.ledfx/assets/current_album_art.jpg`

## Testing
```bash
cd tools/song-detector
python3 song-detector.py --device_name test

# Verify album art saved
ls -lh ~/Library/Application\ Support/.ledfx/assets/
open ~/Library/Application\ Support/.ledfx/assets/current_album_art.jpg
```

## Important Notes
1. Framework is **universal binary** (x86_64 + arm64) - works on Intel and Apple Silicon
2. **Ad-hoc signed** - no Apple Developer certificate needed
3. **No external dependencies** - Perl is built-in on macOS
4. **BSD 3-Clause licensed** - compatible with our use case
5. Hybrid approach prefers system `media-control` if installed, but always has bundled fallback

## Artifacts Produced
- `song-detector.exe` (Windows)
- `song-detector-linux` (Linux)
- `song-detector-macos` (macOS - new!)

## License Attribution
MediaRemoteAdapter is © 2025 Jonas van den Berg, BSD 3-Clause License.
See `LICENSE-mediaremote-adapter` for full text.
