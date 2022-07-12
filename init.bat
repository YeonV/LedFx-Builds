@echo off
echo Initializing LedFx:
git clone --quiet https://github.com/YeonV/LedFx-Builds ledfx && cd ledfx
echo Getting Frontend...
git clone --quiet https://github.com/YeonV/LedFx-Frontend-v2 frontend 
echo Getting Backend...
git clone --quiet https://github.com/LedFx/LedFx backend 
echo Creating Python Venv...
python -m venv venv
cd venv\Scripts
call activate.bat
cd ..
cd ..
cd backend

pip install -q ..\tools\win\aubio-0.5.0a0-cp310-cp310-win_amd64.whl
pip install -q aiohttp~=3.7.4
pip install -q aiohttp_cors>=0.7.0
pip install -q -r requirements-dev.txt
python -m pip install -q --upgrade pip
python -m pip install -q --upgrade wheel
python -m pip install -q  pywin32
python ..\venv\Scripts\pywin32_postinstall.py -install
pip install -q pystray
pip install -q typing-extensions
python setup.py develop
cd ..
cp tools\win\libportaudio64bit.dll venv\Lib\site-packages\sounddevice-0.4.4-py3.10-win-amd64.egg\_sounddevice_data\portaudio-binaries
cd frontend
where node.exe >nul 2>&1 && echo yarn already installed || call %~dp0\ledfx\install-yarn.bat
call yarn
cls
call %~dp0\ledfx\dev.bat