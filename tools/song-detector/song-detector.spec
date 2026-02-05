# -*- mode: python ; coding: utf-8 -*-
import platform
import os

# macOS-specific data files
datas = []
if platform.system() == 'Darwin':
    # Bundle the MediaRemoteAdapter framework and Perl script
    framework_path = os.path.join(os.getcwd(), 'MediaRemoteAdapter.framework')
    perl_script = os.path.join(os.getcwd(), 'mediaremote-adapter.pl')
    
    if os.path.exists(framework_path):
        datas.append((framework_path, 'MediaRemoteAdapter.framework'))
    if os.path.exists(perl_script):
        datas.append((perl_script, '.'))

a = Analysis(
    ['song-detector.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='song-detector',
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
    codesign_identity=os.environ.get('CODESIGN_IDENTITY'),
    entitlements_file=os.path.join(os.getcwd(), 'entitlements.plist') if platform.system() == 'Darwin' else None,
)
