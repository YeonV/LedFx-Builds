git clone https://github.com/YeonV/LedFx-Build ledfx
cd ledfx
git clone https://github.com/YeonV/LedFx-Frontend-v2 frontend
git clone https://github.com/LedFx/LedFx backend

python -m venv venv
cd venv\Scripts
call activate.bat
cd ..
cd ..
cd backend
pip install ..\tools\aubio-0.5.0a0-cp310-cp310-win_amd64.whl
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
cd frontend
where node.exe >nul 2>&1 && yarn || set /p install_yarn="Install Yarn? (y/n)"
IF /I "%install_yarn%" NEQ "y" GOTO STEP2
npm -g install yarn
yarn
GOTO STEP3

:STEP2
npm install --force

:STEP3
cls

