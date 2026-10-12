@echo off
rem Dev PC only. Run AFTER importing the production dump. (messages and the Y/N prompt are in the PowerShell script)
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0ai_restore_after_import.ps1" -Interactive
set RESULT=%ERRORLEVEL%
echo.
echo exit code: %RESULT%
pause
exit /b %RESULT%
