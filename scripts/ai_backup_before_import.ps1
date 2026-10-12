# 開発PC専用: 本番ダンプを開発DBへインポートする「前」に実行する。
# AI分析のテンプレートと実行履歴を、output\ai_backup\<日時>\ へ書き出し、件数を表示する(DBは読み取りのみ)。
# インポート後は ai_restore_after_import.ps1 を実行する。手順は 仕様書\AI分析_開発DB再取り込み手順.md。
param(
    [string]$OutputDir
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root 'venv\Scripts\python.exe'
$backend = Join-Path $root 'pm_backend'

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = '1'

if (-not (Test-Path $python)) {
    Write-Host "× 仮想環境のPythonが見つかりません: $python" -ForegroundColor Red
    exit 1
}

Write-Host '=== AI分析のテンプレート・実行履歴を書き出します(DBは読み取りのみ) ===' -ForegroundColor Cyan
Push-Location $backend
try {
    $arguments = @('manage.py', 'export_ai_analysis_data')
    if ($OutputDir) { $arguments += @('--output-dir', $OutputDir) }
    & $python @arguments
    if ($LASTEXITCODE -ne 0) {
        Write-Host '× 書き出しに失敗しました。ダンプのインポートは行わないでください。' -ForegroundColor Red
        exit 1
    }
} finally {
    Pop-Location
}

Write-Host '○ 書き出しが完了しました。上に表示された件数と書き出し先を確認してから、ダンプをインポートしてください。' -ForegroundColor Green
Write-Host '  (このフォルダはGitにコミットされません。ユーザー名・分析目的を含みます。)' -ForegroundColor Yellow
