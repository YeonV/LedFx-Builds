@echo off
cls
if exist %~dp0\ledfx\ (
  echo A folder named 'ledfx' is already existing!
  pause
  goto end 
)
FOR /F "tokens=2" %%F IN ('"python --version"') DO SET v=%%F
SET pyversion=%v:~0,4%
echo Initializing LedFx-Dev for Python %pyversion%:
git clone --quiet https://github.com/YeonV/LedFx-Builds ledfx && cd ledfx
echo Getting Backend...
git clone --quiet https://github.com/LedFx/LedFx backend 
echo Getting Frontend...
git clone --quiet https://github.com/YeonV/LedFx-Frontend-v2 frontend 
echo Creating Python Venv...
python -m venv venv
call %~dp0\ledfx\venv\Scripts\activate.bat
cd  %~dp0\ledfx\
cd backend
echo Installing dependencies ...

@REM python -m pip install -q --upgrade wheel


@REM pip install -q pystray
@REM pip install -q typing-extensions
python -m pip install -q --upgrade pip
pip install pipwin
pipwin refresh
pipwin install pywin32
python %~dp0\ledfx\venv\Scripts\pywin32_postinstall.py -install
pip install numpy
pip install pillow
pip install psutil
if %pyversion%==3.10 (
  pip install -q ..\tools\win\aubio-0.5.0a0-cp310-cp310-win_amd64.whl
) else if %pyversion%==3.9. (
  pip install -q ..\tools\win\aubio-0.5.0a0-cp39-cp39-win_amd64.whl
)
pip install "chardet<4.0"
pip install --upgrade git+https://github.com/Digital-Sapphire/PyUpdater.git@main
python setup.py develop
if %pyversion%==3.10 (
  copy %~dp0\ledfx\tools\win\libportaudio64bit.dll %~dp0\ledfx\venv\Lib\site-packages\sounddevice-0.4.4-py3.10-win-amd64.egg\_sounddevice_data\portaudio-binaries >nul 2>&1
) else if %pyversion%==3.9. (
  copy %~dp0\ledfx\tools\win\libportaudio64bit.dll %~dp0\ledfx\venv\Lib\site-packages\sounddevice-0.4.4-py3.9-win-amd64.egg\_sounddevice_data\portaudio-binaries >nul 2>&1
) else (
  echo Unsupport python version %pyversion%
  pause
  goto end 
)
cd %~dp0\ledfx\frontend
echo Installing Frontend...
where yarn.exe >nul 2>&1 && echo yarn already installed || call %~dp0\ledfx\tools\win\install-yarn.bat
echo Grab a coffee!
call %~dp0\ledfx\install.bat
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
