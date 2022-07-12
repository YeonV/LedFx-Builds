@echo off
git clone https://github.com/YeonV/LedFx-Builds ledfx && cd ledfx
git clone https://github.com/YeonV/LedFx-Frontend-v2 frontend
git clone https://github.com/LedFx/LedFx backend

python -m venv venv
cd venv\Scripts
call activate.bat
cd ..
cd ..
cd backend
pip install ..\tools\win\aubio-0.5.0a0-cp310-cp310-win_amd64.whl
pip install aiohttp~=3.7.4
pip install aiohttp_cors>=0.7.0
pip install -r requirements-dev.txt
python -m pip install --upgrade pip
python -m pip install --upgrade wheel
python -m pip install pywin32
python ..\venv\Scripts\pywin32_postinstall.py -install
pip install pystray
pip install typing-extensions
python setup.py develop
cd ..
cp tools\win\libportaudio64bit.dll venv\Lib\site-packages\sounddevice-0.4.4-py3.10-win-amd64.egg\_sounddevice_data\portaudio-binaries
cd frontend
where node.exe >nul 2>&1 && echo yarn installed || call %~dp0\install-yarn.bat
call yarn
cls
call dev.bat