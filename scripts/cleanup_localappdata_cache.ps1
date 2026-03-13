param(
    [switch]$WhatIfMode
)

$ErrorActionPreference = "Stop"

function Get-FolderSizeGB {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $sum = (Get-ChildItem $Path -Recurse -Force -File -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum).Sum

    if (-not $sum) {
        $sum = 0
    }

    return [math]::Round(($sum / 1GB), 2)
}

function Show-TopLocalFolders {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BasePath,
        [int]$Top = 20
    )

    Write-Host "`n[1/4] AppData\Local 上位フォルダ容量（Top $Top）" -ForegroundColor Cyan
    Get-ChildItem $BasePath -Directory -Force | ForEach-Object {
        [PSCustomObject]@{
            Folder = $_.FullName
            SizeGB = Get-FolderSizeGB -Path $_.FullName
        }
    } | Sort-Object SizeGB -Descending | Select-Object -First $Top | Format-Table -AutoSize
}

function Remove-CacheItems {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Targets,
        [switch]$WhatIfMode
    )

    Write-Host "`n[2/4] 安全なキャッシュ削除を実行" -ForegroundColor Cyan
    foreach ($target in $Targets) {
        if ($WhatIfMode) {
            Write-Host "[WhatIf] Remove-Item $target" -ForegroundColor Yellow
            continue
        }

        Remove-Item $target -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "削除対象を処理: $target"
    }
}

function Show-MicrosoftBreakdown {
    param(
        [Parameter(Mandatory = $true)]
        [string]$MicrosoftPath,
        [int]$Top = 20
    )

    Write-Host "`n[3/4] Microsoft 配下の容量内訳（Top $Top）" -ForegroundColor Cyan
    Get-ChildItem $MicrosoftPath -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object {
        [PSCustomObject]@{
            Folder = $_.Name
            SizeGB = Get-FolderSizeGB -Path $_.FullName
        }
    } | Sort-Object SizeGB -Descending | Select-Object -First $Top | Format-Table -AutoSize
}

function Show-MicrosoftTop10 {
    param(
        [Parameter(Mandatory = $true)]
        [string]$MicrosoftPath
    )

    Write-Host "`n[4/4] 削除後の Microsoft 上位10件" -ForegroundColor Cyan
    Get-ChildItem $MicrosoftPath -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object {
        [PSCustomObject]@{
            Folder = $_.Name
            SizeGB = Get-FolderSizeGB -Path $_.FullName
        }
    } | Sort-Object SizeGB -Descending | Select-Object -First 10 | Format-Table -AutoSize
}

$base = $env:LOCALAPPDATA
$microsoftPath = Join-Path $base "Microsoft"

$cacheTargets = @(
    "$env:LOCALAPPDATA\Temp\*",
    "$env:LOCALAPPDATA\CrashDumps\*",
    "$env:LOCALAPPDATA\npm-cache\*",
    "$env:LOCALAPPDATA\pypa\Cache\*",
    "$env:LOCALAPPDATA\obsidian-updater\*",
    "$env:LOCALAPPDATA\ms-playwright-go\*",
    "$env:LOCALAPPDATA\Microsoft\Edge\User Data\*\Cache\*",
    "$env:LOCALAPPDATA\Microsoft\Edge\User Data\*\Code Cache\*",
    "$env:LOCALAPPDATA\Microsoft\Edge\User Data\*\GPUCache\*",
    "$env:LOCALAPPDATA\Microsoft\Edge\User Data\*\Service Worker\CacheStorage\*",
    "$env:LOCALAPPDATA\Microsoft\Office\16.0\OfficeFileCache\*",
    "$env:LOCALAPPDATA\Microsoft\Office\SolutionPackages\*",
    "$env:LOCALAPPDATA\Microsoft\Outlook\RoamCache\*",
    "$env:LOCALAPPDATA\Microsoft\Windows\INetCache\Content.Outlook\*"
)

Write-Host "=== AppData\Local キャッシュ整理スクリプト ===" -ForegroundColor Green
Write-Host "対象: $base"
if ($WhatIfMode) {
    Write-Host "モード: WhatIf（削除は実行しません）`n" -ForegroundColor Yellow
} else {
    Write-Host "モード: 実行（削除を実施します）`n" -ForegroundColor Yellow
}

Show-TopLocalFolders -BasePath $base -Top 20
Show-MicrosoftBreakdown -MicrosoftPath $microsoftPath -Top 20
Remove-CacheItems -Targets $cacheTargets -WhatIfMode:$WhatIfMode
Show-MicrosoftTop10 -MicrosoftPath $microsoftPath

Write-Host "`n完了。必要なら Outlook の .ost は別途手動確認してください。" -ForegroundColor Green
