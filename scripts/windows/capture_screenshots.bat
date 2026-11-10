@echo off
REM Takes the README / LinkedIn screenshots of the running app.
REM start_project.bat must be running in another window.
cd /d "%~dp0..\.."
set PIP_NO_CACHE_DIR=1
echo === 1/3  Demo customers (so the installer pages are not empty) ===
backend\venv\Scripts\python.exe backend\scripts\demo_data.py
if errorlevel 1 (echo [ERROR] Could not add the demo data - is the database running? & pause & exit /b 1)
echo.
echo === 2/3  Screenshot tool (first time only) ===
backend\venv\Scripts\python.exe -m pip install -q playwright==1.48.0
echo.
echo === 3/3  Taking screenshots (about 2 minutes - the chat ones use the real AI) ===
backend\venv\Scripts\python.exe scripts\capture_screenshots.py > screenshot_log.txt 2>&1
type screenshot_log.txt
start "" "docs\screenshots"
pause
