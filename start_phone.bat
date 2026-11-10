@echo off
REM ===================================================================
REM  Open SolarSaathi on your PHONE (same Wi-Fi as this laptop).
REM  HTTPS is needed because phone browsers only allow the microphone on https pages.
REM ===================================================================
cd /d "%~dp0"
cd frontend
if not exist node_modules\@vitejs\plugin-basic-ssl call npm install --no-audit --no-fund
cd ..
start "SolarSaathi Backend" cmd /k "cd /d "%~dp0backend" && venv\Scripts\python.exe main.py"
start "SolarSaathi Frontend (phone mode)" cmd /k "cd /d "%~dp0frontend" && set PHONE=1&& npm run dev"
echo.
echo ===================================================================
echo  On your PHONE (Chrome) open:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do for /f "tokens=*" %%b in ("%%a") do echo     https://%%b:5175
echo.
echo  Chrome says "Your connection is not private": tap Advanced, then Proceed (it is your own laptop).
echo  Then tap the mic and allow the microphone. Chrome menu - "Add to Home screen" installs it like an app.
echo  If Windows asks to allow Node.js on the network, tick PRIVATE networks and Allow.
echo ===================================================================
pause
