@echo off
rem Development PC only. Starts/stops/checks the analysis AI execution stack (Memurai, launcher, worker).
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\analysis-dev.ps1" -Action status %*
pause
