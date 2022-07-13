cd frontend
if "%~1"=="" goto both
if "%~1"=="frontend" (goto frontend) else goto backend

:frontend
yarn start
goto done

:backend
cd..
venv\Scripts\activate.bat & ledfx -vv --offline
goto done

:both
cd ..
call wt -d "./backend" cmd /k "title LedFx-Backend & code . & cd .. && venv\Scripts\activate.bat & ledfx -vv --offline"; ^
split-pane -H -d "./frontend" cmd /k "title LedFx-Frontend & code . & yarn start"; ^
split-pane -V -d "./" cmd /k "title LedFx & echo =============================== & echo     LedFx Dev Environment & echo ------------------------------- & echo Commands to start: & echo dev & echo dev frontend & echo dev backend & echo =============================== & echo Backend:  http://localhost:8888 & echo Frontend: http://localhost:3000 & echo ===============================

:done
cls

