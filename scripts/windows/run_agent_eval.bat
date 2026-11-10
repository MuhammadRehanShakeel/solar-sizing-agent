@echo off
REM Tests the REAL AI agent on 10 scripted customers (uses your free Groq / Gemini quota, ~2 minutes).
cd /d "%~dp0..\.."
backend\venv\Scripts\python.exe evaluation\eval_agent.py > eval_log.txt 2>&1
type eval_log.txt
pause
