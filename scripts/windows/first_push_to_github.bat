@echo off
REM ===================================================================
REM  FIRST upload of SolarSaathi to GitHub (run once).
REM  Before running: on github.com create an EMPTY repository named
REM  solar-sizing-agent  (no README, no .gitignore, no license).
REM ===================================================================
cd /d "%~dp0..\.."
if exist scripts\github_ci.yml (
    if not exist .github\workflows mkdir .github\workflows
    move /y scripts\github_ci.yml .github\workflows\ci.yml >nul
)
if exist frontend\src\components\PublicHeader.jsx del frontend\src\components\PublicHeader.jsx
git config --global user.name "Muhammad Rehan Shakeel"
git config --global user.email "MuhammadRehanShakeel11@gmail.com"
if not exist .git git init -b main
git add .
echo.
echo Files that will be uploaded (check: NO .env, NO DEMO_ACCOUNT.txt):
git status --short
echo.
pause
git commit -m "SolarSaathi: AI solar sizing agent (LangGraph + Groq/Gemini, bill reading, voice, PDF quotes)"
git remote remove origin 2>nul
git remote add origin https://github.com/MuhammadRehanShakeel/solar-sizing-agent.git
git push -u origin main
echo.
echo If it asks you to sign in, sign in to GitHub in the window that opens.
pause
