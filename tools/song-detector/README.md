# Song Detector

Cross-platform music detection tool that sends now-playing info to LedFx.

## Variants

### Song Detector (Basic)
`song-detector.py` - Captures and sends:
- Artist & title → LED matrix text display
- Album artwork → LED matrix image visualization
- Auto-extracted colors → gradients for virtuals (keeps effect running)

### Song Detector Plus (Advanced)
`song-detector-plus.py` - Everything from Basic, plus:
- Real-time playback position & duration
- Built-in player controls
- **Song Triggers** - auto-apply specific scenes when songs play

## Supported Platforms

- **Windows** - Media session API
- **macOS** - Custom MediaRemote adapter (see below)
- **Linux** - MPRIS D-Bus integration

## Supported Players

- Spotify
- Apple Music / iTunes
- YouTube Music
- VLC, foobar2000, and more

## macOS Implementation

Uses a custom `MediaRemoteAdapter.framework` for reliable media control.

See `MACOS-IMPLEMENTATION.md` and `LICENSE-mediaremote-adapter` for details.

Based on [media-control](https://github.com/qier222/media-control) with LedFx-specific enhancements.

## Building

Windows:
```bash
build.bat
```

Builds both `song-detector.exe` and `song-detector-plus.exe` using PyInstaller.

## Integration

Bundled with **LedFx CC** (Desktop App):
- Download & install from CC settings
- Auto-start configuration
- Protocol handler for Spotify callbacks

