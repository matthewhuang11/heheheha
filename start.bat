@echo off
rem Scoutbot for Windows: double-click me. The first time, I set everything up (a few minutes); after that I start at once.
setlocal
cd /d "%~dp0"

set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY goto nopython

%PY% scripts\setup.py --if-needed
if errorlevel 1 goto setupfailed

".venv\Scripts\python.exe" -m scoutbot.start %*
echo.
pause
exit /b 0

:nopython
echo Scoutbot needs Python 3.10 or newer, and this computer does not have it yet.
echo Install Python 3.10+ from https://www.python.org/downloads/ and tick "Add python.exe to PATH",
echo then double-click start.bat again.
pause
exit /b 1

:setupfailed
echo.
echo Setup did not finish. Scroll up to see why, fix it, then double-click start.bat again.
echo (If Python is missing: install Python 3.10+ from python.org and tick "Add python.exe to PATH".)
pause
exit /b 1
