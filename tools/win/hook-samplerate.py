
"""
samplerate:
https://github.com/tuxu/python-samplerate/
"""

import os

from PyInstaller.compat import is_darwin, is_win
from PyInstaller.utils.hooks import get_package_paths

sfp = get_package_paths("samplerate")

path = None
if is_win:
    path = os.path.join(sfp[0], "samplerate", "_samplerate_data")
elif is_darwin:
    path = os.path.join(
        sfp[0], "samplerate", "_samplerate_data", "libsamplerate.dylib"
    )

if path is not None and os.path.exists(path):
    binaries = [(path,
                 os.path.join("samplerate", "_samplerate_data"))]