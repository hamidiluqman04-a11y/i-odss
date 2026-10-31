@echo off
rem Start I-ODSS (backend + frontend) and open the browser.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
echo.
pause
