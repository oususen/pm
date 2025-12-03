@echo off
REM Setup pm_db database
echo ====================================
echo PM Database Setup
echo ====================================
echo.
echo Please enter MySQL root password when prompted
echo.

cd /d %~dp0
mysql -u root -p < setup_database.sql

echo.
echo Setup completed!
pause
