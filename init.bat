@echo off
cls
if "%~1"=="" (
    SET project=ledfx
) else (
    SET project=%1
)

if exist .\%project%\ (
  echo A folder named '%project%' is already existing!
  pause
  goto end 
)
FOR /F "tokens=2" %%F IN ('"python --version"') DO SET v=%%F
SET pyversion=%v:~0,4%
if %pyversion%==3.10 (
  echo Initializing LedFx-Dev for Python %pyversion% into '%project%':
) else if %pyversion%==3.9. (
  echo Initializing LedFx-Dev for Python %pyversion% into '%project%':
) else (
  echo Unsupport python version %pyversion%
  pause
  goto end 
)
git clone --quiet https://github.com/YeonV/LedFx-Builds %project% && cd %project%
echo Getting Backend...
git clone --quiet https://github.com/LedFx/LedFx backend 
echo Getting Frontend...
git clone --quiet https://github.com/YeonV/LedFx-Frontend-v2 frontend 
echo Creating Python Venv...
python -m venv venv
cd venv

call .\Scripts\activate.bat
echo Installing dependencies ...
pip install pipwin
pipwin refresh
pipwin install pywin32
python .\Scripts\pywin32_postinstall.py -install
pip install numpy
pip install pillow
pip install "chardet<4.0"
pip install --upgrade git+https://github.com/Digital-Sapphire/PyUpdater.git@main
if %pyversion%==3.10 (
  copy ..\tools\win\aubio-0.5.0a0-cp310-cp310-win_amd64.whl .
  pip install -q aubio-0.5.0a0-cp310-cp310-win_amd64.whl
) else if %pyversion%==3.9. (
  copy ..\tools\win\aubio-0.5.0a0-cp39-cp39-win_amd64.whl .
  pip install -q aubio-0.5.0a0-cp39-cp39-win_amd64.whl
)
cd ..
cd backend
python setup.py develop

if %pyversion%==3.10 (
  copy ..\tools\win\libportaudio64bit.dll ..\venv\Lib\site-packages\sounddevice-0.4.4-py3.10-win-amd64.egg\_sounddevice_data\portaudio-binaries >nul 2>&1
) else if %pyversion%==3.9. (
  copy ..\tools\win\libportaudio64bit.dll ..\venv\Lib\site-packages\sounddevice-0.4.4-py3.9-win-amd64.egg\_sounddevice_data\portaudio-binaries >nul 2>&1
) else (
  echo Unsupport python version %pyversion%
  pause
  goto end 
)
cd ..
cd frontend
echo Installing Frontend...
where yarn.exe >nul 2>&1 && echo yarn already installed || call ..\tools\win\install-yarn.bat
echo Grab a coffee!
call ..\install.bat
cls
cd %~dp0
@REM del init.bat
cd %project%
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
