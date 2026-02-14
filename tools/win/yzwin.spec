# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from hiddenimports import hiddenimports
from PyInstaller.utils.hooks import copy_metadata
from PyInstaller.utils.hooks import collect_data_files

spec_root = os.path.abspath(SPECPATH)

# Read version from ledfx/consts.py
sys.path.insert(0, spec_root)
from ledfx.consts import PROJECT_VERSION, PROJECT_NAME, PROJECT_AUTHOR

# Parse version string (e.g., "2.1.5" or "2.1.5-b6")
base_version = PROJECT_VERSION.split('-')[0]
version_parts = base_version.split('.')
# Pad to 3 components (major, minor, patch)
while len(version_parts) < 3:
    version_parts.append('0')
version_list = [int(x) for x in version_parts[:3]]

# Extract beta number if present (e.g., "2.1.5-b6" -> 6)
beta_number = 0
if '-b' in PROJECT_VERSION:
    try:
        beta_number = int(PROJECT_VERSION.split('-b')[1])
    except (IndexError, ValueError):
        beta_number = 0

# Create 4-component version tuple: (major, minor, patch, beta)
version_tuple = tuple(version_list + [beta_number])

venv_root = os.path.abspath(os.path.join(SPECPATH, '..'))
block_cipher = None
print(venv_root)

# Collect lifx-async package metadata (required by lifx/__init__.py for importlib.metadata)
lifx_metadata = copy_metadata('lifx-async')

yzdata = [(f'{spec_root}/ledfx_frontend', 'ledfx_frontend/'), (f'{spec_root}/ledfx/', 'ledfx/'), (f'{spec_root}/ledfx_assets', 'ledfx_assets/'),(f'{spec_root}/ledfx_assets/tray.png','.')]
yzdata += lifx_metadata
# yzdata += collect_data_files('bokeh')
# yzdata += collect_data_files('xyzservices')
# yzdata += copy_metadata('bokeh')
# yzdata += copy_metadata('xyzservices')

a = Analysis([f'{spec_root}\\ledfx\\__main__.py'],
             pathex=[f'{spec_root}', f'{spec_root}\\ledfx'],
             binaries=[],
             datas=yzdata,
             hiddenimports=hiddenimports,
             hookspath=[f'{venv_root}\\lib\\site-packages\\pyupdater\\hooks'],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

# Create version info for Windows exe metadata
from PyInstaller.utils.win32.versioninfo import (
    VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable,
    StringStruct, VarFileInfo, VarStruct
)

version_info = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=version_tuple,
        prodvers=version_tuple,
        mask=0x3f,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0)
    ),
    kids=[
        StringFileInfo([
            StringTable(
                '040904B0',
                [
                    StringStruct('CompanyName', 'YeonV aka Blade'),
                    StringStruct('FileDescription', 'LedFx v2 - BladeMOD'),
                    StringStruct('FileVersion', PROJECT_VERSION),
                    StringStruct('InternalName', 'LedFx'),
                    StringStruct('LegalCopyright', 'Copyright © 2026 YeonV aka Blade'),
                    StringStruct('OriginalFilename', 'LedFx.exe'),
                    StringStruct('ProductName', PROJECT_NAME),
                    StringStruct('ProductVersion', PROJECT_VERSION)
                ]
            )
        ]),
        VarFileInfo([VarStruct('Translation', [1033, 1200])])
    ]
)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='LedFx',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          icon=f'{spec_root}\\ledfx_assets\\discord.ico',
          version=version_info)
