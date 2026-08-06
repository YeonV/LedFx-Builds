# -*- mode: python ; coding: utf-8 -*-
import os
from hiddenimports import hiddenimports
from ledfx.consts import PROJECT_VERSION
from PyInstaller.utils.hooks import copy_metadata
# from PyInstaller.utils.hooks import collect_data_files

spec_root = os.path.abspath(SPECPATH)
venv_root = os.path.abspath(os.path.join(SPECPATH, '..'))
block_cipher = None

# Collect lifx-async package metadata (required by lifx/__init__.py for importlib.metadata)
lifx_metadata = copy_metadata('lifx-async')

# Remove the ledfx.env file if it exists
os.remove("ledfx.env") if os.path.exists("ledfx.env") else None

# Get environment variables
github_sha_value = os.getenv('GITHUB_SHA')

# Initialize variables
variables = [f"GITHUB_SHA = {github_sha_value}"]
variables.append('IS_RELEASE = false')

# Write to ledfx.env file
with open('ledfx.env', 'a') as file:
    file.write('\n'.join(variables))

print(venv_root)
print(f'{spec_root}')
yzdata = [(f'{spec_root}/ledfx_frontend', 'ledfx_frontend/'), (f'{spec_root}/ledfx/', 'ledfx/'), (f'{spec_root}/ledfx_assets', 'ledfx_assets/'),(f'{spec_root}/ledfx_assets/tray.png','.'), (f'{spec_root}/ledfx.env','.')]
yzdata += lifx_metadata
# yzdata += collect_data_files('bokeh')
# yzdata += collect_data_files('xyzservices')
# yzdata += copy_metadata('bokeh')
# yzdata += copy_metadata('xyzservices')

# onnxruntime powers real-time stem separation. It is an optional extra, so
# collect it defensively: a build without `--extra stems` simply has no
# onnxruntime, and LedFx reports separation as unavailable at runtime rather
# than failing. Imports are aliased locally so this block can be dropped into
# any spec without touching its import header.
try:
    from PyInstaller.utils.hooks import collect_data_files as _onnx_cdf
    from PyInstaller.utils.hooks import collect_dynamic_libs as _onnx_cdl
    from PyInstaller.utils.hooks import collect_submodules as _onnx_csm

    onnx_binaries = _onnx_cdl('onnxruntime')
    onnx_datas = _onnx_cdf('onnxruntime')
    onnx_hiddenimports = _onnx_csm('onnxruntime')
    print(f'onnxruntime: {len(onnx_binaries)} libs, {len(onnx_datas)} data files')
except Exception as exc:
    print(f'onnxruntime not bundled ({exc}) - stem separation will be unavailable')
    onnx_binaries, onnx_datas, onnx_hiddenimports = [], [], []

a = Analysis([f'{spec_root}/ledfx/__main__.py'],
             pathex=[f'{spec_root}', f'{spec_root}/ledfx'],
             binaries=onnx_binaries,
             datas=yzdata + onnx_datas,
             hiddenimports=hiddenimports + onnx_hiddenimports,
             hookspath=[f'{venv_root}/lib/site-packages/pyupdater/hooks'],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='LedFx_v2',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          # target_arch='universal2',
          # target_arch='arm64',
          # target_arch='x86_64',
          icon=f'{spec_root}/ledfx_assets/logo.icns')
app = BUNDLE(exe,              
          a.binaries,
          a.zipfiles,
          a.datas,
          name='LedFx_v2',
          icon=f'{spec_root}/ledfx_assets/logo.icns',
          bundle_identifier='com.blade.ledfx',
          version=f'{PROJECT_VERSION}',
          info_plist={
              'CFBundleShortVersionString': f'{PROJECT_VERSION}',
              'CFBundleVersion': f'{PROJECT_VERSION}',
              'LSApplicationCategoryType': 'public.app-category.music',
              'NSHumanReadableCopyright': 'Copyright © 2024 YeonV aka Blade',
              'NSPrincipalClass': 'NSApplication',
              'NSAppleScriptEnabled': False,
              'NSMicrophoneUsageDescription': 'LedFx uses audio for sound visualization',
              'com.apple.security.device.audio-input': True,
              'com.apple.security.device.microphone': True,
              },
          entitlements_plist={
              'com.apple.security.device.audio-input': True,
              'com.apple.security.device.microphone': True,
              })
# Cleanup ledfx.env
os.remove("ledfx.env")
