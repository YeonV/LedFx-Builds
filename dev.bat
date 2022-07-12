@echo off
if "%~1"=="" goto both
if "%~1"=="frontend" (goto frontend) else goto backend

:frontend
yarn start
:backend
%~dp0\venv\Scripts\activate.bat & ledfx -vv --offline

:both
call wt -d "./backend" cmd /k "title LedFx-Backend & code . & %~dp0\venv\Scripts\activate.bat & ledfx -vv --offline"; ^
split-pane -H -d "./frontend" cmd /k "title LedFx-Frontend & code . & call yarn start"

:done
cls
echo LedFx-Dev-Environment startet!