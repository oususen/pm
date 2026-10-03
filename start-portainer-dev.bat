@echo off
rem 開発用Portainerを起動する。Windowsへの自動起動登録は行わない。
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-portainer-dev.ps1" %*
if errorlevel 1 pause
