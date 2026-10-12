@echo off
chcp 65001 >nul
rem 開発PC専用: 本番ダンプを開発DBへインポートする「前」に、ダブルクリックで実行する。
rem AI分析のテンプレート・実行履歴を、output\ai_backup\<日時>\ に書き出す(DBは読み取りのみ)。
rem 次の手順: 1) 上に表示された件数と書き出し先を確認 2) 本番のダンプをインポート 3) ai_restore_after_import.bat を実行
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0ai_backup_before_import.ps1"
set RESULT=%ERRORLEVEL%
echo.
if not "%RESULT%"=="0" (
    echo [失敗] 書き出しに失敗しました。ダンプのインポートは行わないでください。
) else (
    echo [完了] 書き出しが完了しました。次は、本番のダンプをインポートし、その後 ai_restore_after_import.bat を実行します。
)
pause
exit /b %RESULT%
