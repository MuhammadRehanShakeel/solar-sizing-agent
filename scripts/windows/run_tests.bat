@echo off
REM Runs all automated tests (no SQL Server or AI keys needed).
cd /d "%~dp0..\..\backend"
venv\Scripts\python.exe -m pytest tests -q -p no:warnings > ..\test_results.txt 2>&1
type ..\test_results.txt
pause
