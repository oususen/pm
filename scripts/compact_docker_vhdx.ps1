param(
    [switch]$WhatIfMode
)

$ErrorActionPreference = "Stop"

$vhdxPath = "$env:LOCALAPPDATA\Docker\wsl\disk\docker_data.vhdx"

function Get-FileSizeGB {
    param([string]$Path)
    $file = Get-Item $Path -ErrorAction SilentlyContinue
    if (-not $file) { return 0 }
    return [math]::Round($file.Length / 1GB, 2)
}

function Get-FreeSpaceGB {
    param([string]$Drive)
    $disk = Get-PSDrive $Drive -ErrorAction SilentlyContinue
    if (-not $disk) { return 0 }
    return [math]::Round($disk.Free / 1GB, 2)
}

# 管理者権限チェック
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "エラー: 管理者権限で実行してください（PowerShellを右クリック → 管理者として実行）" -ForegroundColor Red
    exit 1
}

Write-Host "=== Docker VHDX 圧縮スクリプト ===" -ForegroundColor Green
Write-Host "対象: $vhdxPath"
if ($WhatIfMode) {
    Write-Host "モード: WhatIf（削除・停止は実行しません）`n" -ForegroundColor Yellow
} else {
    Write-Host "モード: 実行`n"
}

# VHDXファイル存在確認
if (-not (Test-Path $vhdxPath)) {
    Write-Host "エラー: VHDXファイルが見つかりません: $vhdxPath" -ForegroundColor Red
    exit 1
}

# 圧縮前サイズ確認
$sizeBefore = Get-FileSizeGB -Path $vhdxPath
$freeBefore = Get-FreeSpaceGB -Drive "C"
Write-Host "[1/4] 圧縮前サイズ確認" -ForegroundColor Cyan
Write-Host "  VHDX:    $sizeBefore GB"
Write-Host "  C: 空き: $freeBefore GB"

# Docker Desktop 停止
Write-Host "`n[2/4] Docker Desktop を停止" -ForegroundColor Cyan
$dockerProc = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
if ($dockerProc) {
    if ($WhatIfMode) {
        Write-Host "  [WhatIf] Stop-Process Docker Desktop"
    } else {
        Stop-Process -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue
        Write-Host "  停止しました。10秒待機..."
        Start-Sleep -Seconds 10
    }
} else {
    Write-Host "  すでに停止しています"
}

# WSL2 シャットダウン
Write-Host "`n[3/4] WSL2 シャットダウン" -ForegroundColor Cyan
if ($WhatIfMode) {
    Write-Host "  [WhatIf] wsl --shutdown"
} else {
    wsl --shutdown
    Write-Host "  WSL2 停止完了"
    Start-Sleep -Seconds 3
}

# VHDX 圧縮
Write-Host "`n[4/4] VHDX 圧縮（数分〜20分かかる場合があります）" -ForegroundColor Cyan
$diskpartCommands = @"
select vdisk file="$vhdxPath"
attach vdisk readonly
compact vdisk
detach vdisk
exit
"@

if ($WhatIfMode) {
    Write-Host "  [WhatIf] diskpart コマンド:"
    Write-Host $diskpartCommands -ForegroundColor DarkGray
} else {
    $tempFile = [System.IO.Path]::GetTempFileName() -replace "\.tmp$", ".txt"
    $diskpartCommands | Out-File -FilePath $tempFile -Encoding ascii
    diskpart /s $tempFile
    Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
}

# 圧縮後サイズ確認
$sizeAfter = Get-FileSizeGB -Path $vhdxPath
$freeAfter = Get-FreeSpaceGB -Drive "C"
$savedGB = [math]::Round($sizeBefore - $sizeAfter, 2)

Write-Host "`n=== 結果 ===" -ForegroundColor Green
Write-Host "  VHDX:    $sizeBefore GB → $sizeAfter GB（$savedGB GB 削減）"
Write-Host "  C: 空き: $freeBefore GB → $freeAfter GB"

Write-Host "`n次のステップ：" -ForegroundColor Yellow
Write-Host "  1. Docker Desktop を起動"
Write-Host "  2. コンテナ再起動: docker-compose up -d"
