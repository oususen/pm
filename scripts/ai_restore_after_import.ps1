# 開発PC専用: 本番ダンプを開発DBへインポートした「後」に実行する。
# 1. migrate(消えたAI用ビュー・マイグレーション記録 ai 0034〜 を戻す)
# 2. setup_ai_views --apply(ビューの定義者・列権限を戻す。--reader-host は付けない)
# 3. import_ai_analysis_data(書き出したテンプレート・実行履歴を元のIDで戻す)
# 4. setup_ai_views --check(ビュー・権限の確認)
# どれかが失敗したら、その場で止まる。手順は 仕様書\AI分析_開発DB再取り込み手順.md。
param(
    [string]$InputDir,
    [switch]$DryRun
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

function Invoke-Step($label, [string[]]$arguments) {
    Write-Host ''
    Write-Host "=== $label ===" -ForegroundColor Cyan
    & $python @arguments
    if ($LASTEXITCODE -ne 0) {
        Write-Host "× 失敗しました: $label (終了コード $LASTEXITCODE)。ここで止めます。" -ForegroundColor Red
        exit 1
    }
    Write-Host "○ 完了: $label" -ForegroundColor Green
}

Push-Location $backend
try {
    Invoke-Step '1/4 migrate' @('manage.py', 'migrate')
    Invoke-Step '2/4 setup_ai_views --apply' @('manage.py', 'setup_ai_views', '--apply')

    if ($DryRun) {
        # 確認だけ: 書き込まずに、復元できる件数・スキップする件数を表示して止まる。
        $dryArguments = @('manage.py', 'import_ai_analysis_data', '--dry-run')
        if ($InputDir) { $dryArguments += @('--input-dir', $InputDir) }
        Invoke-Step '3/4 import_ai_analysis_data --dry-run(書き込まない。復元できる件数・スキップの件数の確認)' $dryArguments
        Write-Host ''
        Write-Host '○ 確認だけが完了しました(復元はしていません)。件数とスキップの理由を確認してください。' -ForegroundColor Green
        exit 0
    }

    $importArguments = @('manage.py', 'import_ai_analysis_data', '--i-am-on-dev')
    if ($InputDir) { $importArguments += @('--input-dir', $InputDir) }
    Invoke-Step '3/4 import_ai_analysis_data(テンプレート・実行履歴の復元)' $importArguments

    Invoke-Step '4/4 setup_ai_views --check' @('manage.py', 'setup_ai_views', '--check')
} finally {
    Pop-Location
}

Write-Host ''
Write-Host '○ すべての手順が完了しました。3/4 のスキップ件数(ユーザーが見つからない行)を確認してください。' -ForegroundColor Green
