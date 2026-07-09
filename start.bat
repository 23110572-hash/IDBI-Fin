@echo off
REM ===========================================================================
REM  MSME Financial Health Card - single entry point.
REM  First run installs dependencies; every run launches the app and opens Chrome.
REM  The trained model is bundled in backend\model_artifacts (never retrained).
REM  Requires Python 3.11+ and Node 18+ on PATH.
REM ===========================================================================
setlocal
cd /d "%~dp0"
set "KMP_DUPLICATE_LIB_OK=TRUE"
set "PY=%~dp0ml\.venv\Scripts\python.exe"

REM --- first-run: create venv + install backend/ML runtime deps ---
if not exist "%PY%" (
    echo [first run] Creating Python environment and installing backend dependencies...
    python -m venv ml\.venv || goto :err
    "%PY%" -m pip install --upgrade pip
    "%PY%" -m pip install -e ml || goto :err
    "%PY%" -m pip install -r backend\requirements.txt || goto :err
)

REM --- first-run: install frontend deps ---
if not exist "frontend\node_modules" (
    echo [first run] Installing frontend dependencies...
    pushd frontend
    call npm install || (popd & goto :err)
    popd
)

echo Starting backend on http://localhost:8000 ...
start "MSME Backend" /D "%~dp0backend" cmd /k "%PY%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo Starting frontend on http://localhost:5173 ...
start "MSME Frontend" /D "%~dp0frontend" cmd /k npm run dev

echo Waiting for services to come up ...
timeout /t 12 /nobreak >nul

echo Opening the dashboard in Chrome ...
start chrome "http://localhost:5173" 2>nul || start "" "http://localhost:5173"

echo(
echo  Backend : http://localhost:8000  (API docs: /docs)
echo  Frontend: http://localhost:5173  (sign in as  rm / rm123!)
echo  Close the two spawned windows to stop.
goto :eof

:err
echo(
echo [ERROR] Install failed. Check that Python 3.11+ and Node 18+ are on PATH.
pause
exit /b 1
