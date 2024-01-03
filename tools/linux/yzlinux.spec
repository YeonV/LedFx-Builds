# -*- mode: python ; coding: utf-8 -*-
import os
import importlib.util
 
# specify the module that needs to be 
# imported relative to the path of the 
# module
spec_imports = importlib.util.spec_from_file_location("hiddenimports","/home/runner/work/LedFx-Builds/LedFx-Builds/src/hiddenimports.py")
 
# creates a new module based on spec
imp = importlib.util.module_from_spec(spec_imports)
 
# executes the module in its own namespace
# when a module is imported or reloaded.
spec_imports.loader.exec_module(imp)

spec_root = os.path.abspath(SPECPATH)

venv_root = os.path.abspath(os.path.join(SPECPATH, '..'))
block_cipher = None
print(venv_root)

a = Analysis([f'{spec_root}/ledfx/__main__.py'],
             pathex=[f'{spec_root}', f'{spec_root}/ledfx'],
             binaries=[],
             datas=[(f'{spec_root}/ledfx_frontend', 'ledfx_frontend/'), (f'{spec_root}/ledfx/', 'ledfx/'), (f'{spec_root}/icons', 'icons/'),(f'{spec_root}/icons/tray.png','.')],
             hiddenimports=imp.hiddenimports,
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
          a.binaries,
          a.zipfiles,
          a.datas,
          name='LedFx',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          icon=f'{spec_root}/icons/discord.ico')
