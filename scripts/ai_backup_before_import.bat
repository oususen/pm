@echo off
rem Dev PC only. Run BEFORE importing the production dump. (messages are shown by the PowerShell script)
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0ai_backup_before_import.ps1"
set RESULT=%ERRORLEVEL%
echo.
echo exit code: %RESULT%
pause
exit /b %RESULT%
