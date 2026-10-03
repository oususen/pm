# 開発専用Memuraiを起動する。サービス登録・ファイアウォール変更は行わない。
param(
    [string]$MemuraiPath = 'C:\Program Files\Memurai\memurai.exe'
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $MemuraiPath -PathType Leaf)) {
    throw 'Memurai Developer is not installed. See the development setup in the AI specification.'
}

$taskConfigPath = Join-Path $PSScriptRoot 'analysis-redis-dev.conf'
# この端末で稼働する。停止はCtrl+C。ほかのプロセスを停止しない。
& $MemuraiPath $taskConfigPath
if ($LASTEXITCODE -ne 0) {
    throw "Memurai exited with code $LASTEXITCODE."
}
