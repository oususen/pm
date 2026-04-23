$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

git config core.hooksPath .githooks

Write-Host "Configured core.hooksPath to .githooks"
Write-Host "Current value: $(git config --get core.hooksPath)"
