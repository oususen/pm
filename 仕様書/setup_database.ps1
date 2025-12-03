# setup_database.ps1
# pm_db データベースのセットアップスクリプト (PowerShell)

Write-Host "====================================" -ForegroundColor Cyan
Write-Host "pm_db データベースセットアップ" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "MySQLのrootパスワードを入力してください" -ForegroundColor Yellow
Write-Host ""

# スクリプトのディレクトリに移動
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# MySQLコマンド実行
$mysqlPath = "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"

if (Test-Path $mysqlPath) {
    & $mysqlPath -u root -p --default-character-set=utf8mb4 < setup_database.sql
} else {
    # PATHから探す
    mysql -u root -p --default-character-set=utf8mb4 < setup_database.sql
}

Write-Host ""
if ($LASTEXITCODE -eq 0) {
    Write-Host "セットアップが完了しました！" -ForegroundColor Green
} else {
    Write-Host "エラーが発生しました。" -ForegroundColor Red
}

Write-Host ""
Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
