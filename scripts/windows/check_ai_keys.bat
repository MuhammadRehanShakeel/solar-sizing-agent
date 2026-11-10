@echo off
REM Checks your GROQ / GEMINI keys in backend\.env and lists the models they can use.
cd /d "%~dp0..\..\backend"
venv\Scripts\python.exe scripts\check_ai.py
pause
