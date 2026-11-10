@echo off
REM Run after copying a new version: upgrades the database (keeps your data) and installs new packages.
REM Close the backend and frontend windows first.
cd /d "%~dp0..\.."
echo === 1/3  Python packages ===
cd backend
venv\Scripts\python.exe -m pip install -q -r requirements.txt
echo === 2/3  Database upgrade (new tables / columns only, your data stays) ===
venv\Scripts\python.exe scripts\init_db.py
if errorlevel 1 (echo [ERROR] Database upgrade failed - see above & pause & exit /b 1)
cd ..\frontend
echo === 3/3  Website packages ===
call npm install --no-audit --no-fund
if errorlevel 1 (echo [ERROR] npm install failed & pause & exit /b 1)
cd ..
echo.
echo [DONE] Now double-click start_project.bat
pause
