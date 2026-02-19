param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$DumpFile,
    [string]$DbName = "pm_db",
    [string]$DbUser = "root",
    [string]$DbPassword = "daisoseisanka1470-3#",
    [string]$MysqlPath = "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
)

$ErrorActionPreference = "Stop"

function Resolve-MysqlPath {
    param([string]$PathHint)

    if (Test-Path $PathHint) {
        return $PathHint
    }

    $cmd = Get-Command mysql -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    throw "mysql.exe was not found. Please set -MysqlPath."
}

function Invoke-Mysql {
    param(
        [string]$MysqlExe,
        [string]$User,
        [string]$Password,
        [string]$Sql,
        [string]$TargetDb = ""
    )

    $passwordArg = "-p$Password"

    if ([string]::IsNullOrWhiteSpace($TargetDb)) {
        & $MysqlExe -u $User $passwordArg --default-character-set=utf8mb4 -e $Sql
    } else {
        & $MysqlExe -u $User $passwordArg --default-character-set=utf8mb4 $TargetDb -e $Sql
    }

    if ($LASTEXITCODE -ne 0) {
        throw "MySQL command failed. SQL: $Sql"
    }
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$dumpPath = Join-Path $projectRoot $DumpFile

if (-not (Test-Path $dumpPath)) {
    throw "Dump file not found: $dumpPath"
}

$mysqlExe = Resolve-MysqlPath -PathHint $MysqlPath

Write-Host "Start restore from: $dumpPath" -ForegroundColor Cyan
Write-Host "Target DB: $DbName" -ForegroundColor Cyan

Invoke-Mysql -MysqlExe $mysqlExe -User $DbUser -Password $DbPassword -Sql "DROP DATABASE IF EXISTS $DbName; CREATE DATABASE $DbName CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

$sourceSql = "source " + ($dumpPath -replace "\\", "/")
Invoke-Mysql -MysqlExe $mysqlExe -User $DbUser -Password $DbPassword -TargetDb $DbName -Sql $sourceSql

$passwordArg = "-p$DbPassword"
$tableCount = & $mysqlExe -u $DbUser $passwordArg -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$DbName' AND table_type='BASE TABLE';"
$migrationCount = & $mysqlExe -u $DbUser $passwordArg -N -e "SELECT COUNT(*) FROM $DbName.django_migrations;"

Write-Host "Restore completed." -ForegroundColor Green
Write-Host "Table count: $tableCount"
Write-Host "django_migrations count: $migrationCount"
