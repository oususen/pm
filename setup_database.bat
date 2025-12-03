@echo off
REM setup_database.bat
REM pm_db データベースのセットアップバッチファイル

echo ====================================
echo pm_db データベースセットアップ
echo ====================================
echo.
echo MySQLのrootパスワードを入力してください
echo.

cd /d %~dp0
mysql -u root -p < setup_database.sql

echo.
echo セットアップが完了しました
pause
