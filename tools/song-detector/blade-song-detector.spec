# -*- mode: python ; coding: utf-8 -*-
import platform
import os

block_cipher = None

# Platform-aware datas and hiddenimports so this spec can be used cross-OS
datas = []
# Only bundle icons on Windows
if platform.system() == 'Windows':
    datas.extend([
        ('icon.ico', '.'),
        ('icon.png', '.'),
    ])

hiddenimports = [
    'PIL',
    'PIL.Image',
    'PIL._imaging',
    'websockets',
]

# Only include Windows-specific hiddenimports on Windows
if platform.system() == 'Windows':
    hiddenimports += [
        'winsdk',
        'winsdk.windows.media.control',
    ]

# Include dbus hint on Linux (optional)
if platform.system() == 'Linux':
    hiddenimports += ['dbus']

a = Analysis(
    ['blade-song-detector.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Set codesign/entitlements only for macOS (will read identity from env during CI)
codesign_identity = os.environ.get('CODESIGN_IDENTITY') if platform.system() == 'Darwin' else None
entitlements_file = os.path.join(os.getcwd(), 'entitlements.plist') if platform.system() == 'Darwin' else None

# Use Windows ICO for icon on Windows; leave None for other OSes
icon_option = 'icon.ico' if platform.system() == 'Windows' else None

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='blade-song-detector',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=codesign_identity,
    entitlements_file=entitlements_file,
    icon=icon_option,
)
