@echo off
REM setup_database.bat
REM pm_db database setup helper

REM Use UTF-8 console so Japanese/MySQL output is readable.
chcp 65001 > nul
setlocal
cd /d "%~dp0"

echo ====================================
echo Setting up database: pm_db
echo ====================================
echo.
echo Enter the MySQL root password when prompted.
echo.

mysql -u root -p --default-character-set=utf8mb4 < setup_database.sql
set "err=%errorlevel%"

echo.
if not "%err%"=="0" (
    echo Database setup failed. Exit code: %err%
) else (
    echo Database setup completed successfully.
)
echo.
pause
exit /b %err%
