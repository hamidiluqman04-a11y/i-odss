@echo off
rem One-time I-ODSS setup. Safe to run again.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
echo.
pause
