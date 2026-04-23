$ErrorActionPreference = "Stop"

$repoRoot = (git rev-parse --show-toplevel).Trim()
Set-Location $repoRoot

$emptyTree = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
$changed = New-Object System.Collections.Generic.HashSet[string]

while ($true) {
    $line = [Console]::In.ReadLine()
    if ($null -eq $line) { break }
    if ([string]::IsNullOrWhiteSpace($line)) { continue }

    $parts = $line -split "\s+"
    if ($parts.Length -lt 4) { continue }

    $localSha = $parts[1]
    $remoteSha = $parts[3]

    if ($localSha -match '^0+$') { continue }

    if ($remoteSha -match '^0+$') {
        $files = git diff --name-only $emptyTree $localSha
    } else {
        $files = git diff --name-only $remoteSha $localSha
    }

    foreach ($f in $files) {
        if (-not [string]::IsNullOrWhiteSpace($f)) {
            [void]$changed.Add($f)
        }
    }
}

if ($changed.Count -eq 0) {
    exit 0
}

$dbRelatedChanged = $false
$masterDocChanged = $false
$erDocChanged = $false

foreach ($path in $changed) {
    $normalized = $path.Replace('\', '/').ToLowerInvariant()

    if ($normalized -match '^pm_backend/apps/.+/models[^/]*\.py$' -or $normalized -match '^pm_backend/apps/.+/migrations/.+\.py$') {
        $dbRelatedChanged = $true
    }

    if ($normalized -eq "仕様書/master_tables_definition.md".ToLowerInvariant()) {
        $masterDocChanged = $true
    }

    if ($normalized -eq "仕様書/er_diagram_v3.md".ToLowerInvariant()) {
        $erDocChanged = $true
    }
}

if ($dbRelatedChanged -and (-not $masterDocChanged -or -not $erDocChanged)) {
    Write-Host "ERROR: DB関連変更（models/migrations）を検出しました。"
    Write-Host "以下2ファイルを同じpushに含めてください。"
    Write-Host "  - 仕様書/MASTER_TABLES_DEFINITION.MD"
    Write-Host "  - 仕様書/ER_diagram_v3.md"
    Write-Host ""
    Write-Host "緊急回避が必要な場合のみ: git push --no-verify"
    exit 1
}

exit 0
