@echo off
chcp 65001 >nul
rem 開発PC専用: 本番ダンプを開発DBへインポートした「後」に、ダブルクリックで実行する。
rem 手順: 1) migrate と setup_ai_views --apply を実行し、--dry-run で、復元できる件数・スキップの件数を確認する
rem       2) 内容を確認してから、Y を入力すると、実際に復元する(migrate・setup_ai_views --apply は、もう一度実行される。何度実行しても同じ結果)
cd /d "%~dp0"
echo ===== 1/2 確認(復元はまだしません) =====
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0ai_restore_after_import.ps1" -DryRun
if not "%ERRORLEVEL%"=="0" (
    echo.
    echo [失敗] 確認の途中で止まりました。上のメッセージを確認してください。復元はしていません。
    pause
    exit /b 1
)
echo.
echo 上の「復元できる件数・スキップの件数」を確認してください。
choice /c YN /n /m "この内容で、実際に復元しますか? (Y=復元する / N=やめる): "
if errorlevel 2 (
    echo 復元をやめました。何も書き込んでいません。
    pause
    exit /b 0
)
echo.
echo ===== 2/2 復元(実行) =====
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0ai_restore_after_import.ps1"
set RESULT=%ERRORLEVEL%
echo.
if not "%RESULT%"=="0" (
    echo [失敗] 復元の途中で止まりました。上のメッセージを確認してください。
) else (
    echo [完了] すべての手順が完了しました。スキップの件数(ユーザーが見つからない行)を確認してください。
)
pause
exit /b %RESULT%
