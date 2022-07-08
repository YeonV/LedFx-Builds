cp -f mac-notray.md ./ledfx/__main__.py
pyinstaller mac.spec
mv dist/LedFx_v2 dist/LedFx_core--notray.app