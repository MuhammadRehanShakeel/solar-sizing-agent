@echo off
REM Starts the backend (port 5002) and the website (port 5175) in two windows.
cd /d "%~dp0"
start "SolarSaathi Backend" /min cmd /k "cd /d "%~dp0backend" && venv\Scripts\python.exe main.py"
start "SolarSaathi Frontend" /min cmd /k "cd /d "%~dp0frontend" && npm run dev"
echo The two black windows start MINIMISED (on the taskbar). Do not click inside them: a click freezes the app until you press Esc.
echo Backend API docs: http://localhost:5002/docs
echo Customer chat:    http://localhost:5175
echo Staff pages:      http://localhost:5175/staff
timeout /t 6 >nul
start http://localhost:5175
