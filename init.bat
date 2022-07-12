@echo off
cls
if exist %~dp0\ledfx\ (
  echo A folder named 'ledfx' is already existing!
  pause
  goto end 
)
FOR /F "tokens=2" %%F IN ('"python --version"') DO SET v=%%F
SET pyversion=%v:~0,4%
if %pyversion%==3.10 (
) else if %pyversion%==3.9. (
) else (
  echo unsupported Python version: %pyversion%
  pause
  goto end
)
echo Initializing LedFx-Dev:
git clone --quiet https://github.com/YeonV/LedFx-Builds ledfx && cd ledfx
echo Getting Backend...
git clone --quiet https://github.com/LedFx/LedFx backend 
echo Getting Frontend...
git clone --quiet https://github.com/YeonV/LedFx-Frontend-v2 frontend 
echo Creating Python Venv...
python -m venv venv
cd venv\Scripts
call activate.bat
cd ..
cd ..
cd backend
echo Installing dependencies ...
python -m pip install -q --upgrade pip
python -m pip install -q --upgrade wheel
if %pyversion%==3.10 (
  pip install -q ..\tools\win\aubio-0.5.0a0-cp310-cp310-win_amd64.whl
) else if %pyversion%==3.9. (
  pip install -q ..\tools\win\aubio-0.5.0a0-cp39-cp39-win_amd64.whl
)
pip install -q aiohttp~=3.7.4
pip install -q aiohttp_cors>=0.7.0
pip install -q -r requirements-dev.txt
python -m pip install -q pywin32
python ..\venv\Scripts\pywin32_postinstall.py -install -silent >nul 2>&1
pip install -q pystray
pip install -q typing-extensions
echo Installing Backend...
python setup.py develop >nul 2>&1
cd ..
if %pyversion%==3.10 (
  copy tools\win\libportaudio64bit.dll venv\Lib\site-packages\sounddevice-0.4.4-py3.10-win-amd64.egg\_sounddevice_data\portaudio-binaries
) else if %pyversion%==3.9. (
  copy tools\win\libportaudio64bit.dll venv\Lib\site-packages\sounddevice-0.4.4-py3.9-win-amd64.egg\_sounddevice_data\portaudio-binaries
)

cd frontend
echo Installing Frontend...
where yarn.exe >nul 2>&1 && echo yarn already installed || call %~dp0\ledfx\tools\win\install-yarn.bat
call %~dp0\ledfx\install.bat >nul 2>&1
cls
cd %~dp0
@REM del init.bat
cd ledfx
echo DONE! 
echo =====
echo Commands to start:
echo dev backend
echo dev frontend
echo dev
echo =====
echo You want to start now?
pause
del init.bat
del install.bat
del .gitignore
del LICENSE
del README.md
rmdir .github /s /q
call dev.bat

:end
