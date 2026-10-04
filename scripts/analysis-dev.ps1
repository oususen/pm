# 開発PC専用: 分析AIの実行基盤(Memurai・launcher・専用ワーカー)を、起動・停止・確認する。
# 本番では使わない。launcherと専用ワーカーは、PCの再起動やWSLの停止で止まる(自動起動はしない)。
param(
    [ValidateSet('start', 'stop', 'status')][string]$Action = 'status',
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root 'venv\Scripts\python.exe'
$backend = Join-Path $root 'pm_backend'
$envFile = Join-Path $backend '.env'
$healthUrl = 'http://127.0.0.1:8091/v1/health'
$wslRoot = '/mnt/' + $root.Substring(0, 1).ToLower() + ($root.Substring(2) -replace '\\', '/')

function Get-Health {
    # 一時的な遅れで「停止」と誤表示しないよう、2回まで試す(各8秒)。
    foreach ($attempt in 1..2) {
        try { return Invoke-RestMethod -Uri $healthUrl -TimeoutSec 8 } catch { }
    }
    return $null
}

function Get-State {
    # ワーカーの生存と、実行枠(Redis)を返す。確認に失敗したら $null。
    $script = Join-Path $env:TEMP 'pm-analysis-dev-state.py'
    @'
import json, sys
import redis
from dotenv import dotenv_values
sys.path.insert(0, sys.argv[2] + '/apps')
from ai.services.analysis_worker_identity import current_code_version, worker_version_matches
r = redis.Redis.from_url(dotenv_values(sys.argv[1]).get('AI_ANALYSIS_REDIS_URL'), decode_responses=True)
k = 'pm:ai:analysis:execution:'
worker = r.get(k + 'worker')
print(json.dumps({'worker': bool(worker), 'worker_stale': bool(worker) and not worker_version_matches(worker, current_code_version()), 'active': r.get(k + 'active')}))
'@ | Set-Content -Path $script -Encoding UTF8
    try {
        $lines = & $python $script $envFile $backend 2>$null
        $json = ($lines | Where-Object { $_ -like '{*' } | Select-Object -Last 1)
        if ($json) { return $json | ConvertFrom-Json }
    } catch { }
    return $null
}

function Test-Redis {
    # Memuraiは、Windowsサービスではなく、開発用の設定で単体起動している。6379番ポートの待受けで判定する。
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $task = $client.ConnectAsync('127.0.0.1', 6379)
        $ok = $task.Wait(2000) -and $client.Connected
        $client.Close()
        return $ok
    } catch { return $false }
}

function Get-ContainerCount {
    try {
        # WSLやDockerの確認に失敗した場合は、エラー文を件数として数えず「確認できません」($null)にする。
        $out = & wsl.exe -d Ubuntu-24.04 -u root -- docker ps -aq --filter label=pm.analysis.job=1 2>&1
        if ($LASTEXITCODE -ne 0) { return $null }
        return @($out | Where-Object { $_ -is [string] -and $_ -match '^[0-9a-f]{12,}$' }).Count
    } catch { return $null }
}

function Get-WorkerProcesses {
    Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -and $_.CommandLine -match 'analysis_worker' -and $_.ProcessId -ne $PID
    }
}

function Wait-For($label, [scriptblock]$condition, [int]$seconds = 45) {
    $until = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $until) {
        if (& $condition) { return $true }
        Start-Sleep -Seconds 2
    }
    Write-Host "  × $label を確認できませんでした($seconds 秒)。" -ForegroundColor Red
    return $false
}

function Show-Status {
    Write-Host '=== 分析AI実行基盤の状態 ===' -ForegroundColor Cyan
    Write-Host '  起動できない場合は、PCの時刻帯が日本標準時か確認してください' -ForegroundColor Yellow
    if (Test-Redis) { Write-Host '  Redis(Memurai) : 動作中' -ForegroundColor Green }
    else { Write-Host '  Redis(Memurai) : 停止中(起動してください)' -ForegroundColor Red }

    $health = Get-Health
    if ($health -and $health.status -eq 'ready') {
        $busy = if ($health.busy) { '(実行中、または後始末が残っています)' } else { '(待機中)' }
        Write-Host "  launcher       : 動作中 $busy" -ForegroundColor Green
    } else { Write-Host '  launcher       : 停止中(起動してください)' -ForegroundColor Red }

    $count = Get-ContainerCount
    if ($null -eq $count) { Write-Host '  ジョブ用コンテナ: 確認できません' -ForegroundColor Yellow }
    elseif ($count -eq 0) { Write-Host '  ジョブ用コンテナ: 0件(正常)' -ForegroundColor Green }
    else { Write-Host "  ジョブ用コンテナ: $count 件が残っています(後始末の失敗の可能性)" -ForegroundColor Yellow }

    $state = Get-State
    if ($null -eq $state) {
        Write-Host '  専用ワーカー   : 確認できません(Redisに接続できません)' -ForegroundColor Yellow
    } else {
        if ($state.worker_stale) { Write-Host '  専用ワーカー   : 版が古いか確認できません。専用ワーカーを再起動してください。' -ForegroundColor Yellow }
        elseif ($state.worker) { Write-Host '  専用ワーカー   : 動作中' -ForegroundColor Green }
        else { Write-Host '  専用ワーカー   : 停止中(起動してください)' -ForegroundColor Red }
        if ($state.active) { Write-Host "  実行枠         : 使用中 (ジョブID $($state.active))" -ForegroundColor Yellow }
        elseif ($state.worker -and -not $state.worker_stale) { Write-Host '  実行枠         : 空き(ワーカーの版は一致しています)' -ForegroundColor Green }
        else { Write-Host '  実行枠         : 空き(専用ワーカーの起動・再起動が必要です)' -ForegroundColor Yellow }
    }
    return @{ Health = $health; State = $state }
}

function Start-Dev {
    Write-Host '=== 分析AI実行基盤を起動します ===' -ForegroundColor Cyan
    Write-Host '  起動できない場合は、PCの時刻帯が日本標準時か確認してください' -ForegroundColor Yellow
    # 1. Redis(Memurai)。既存の開発用起動スクリプトを、新しい窓で実行する
    if (Test-Redis) {
        Write-Host '  Redis(Memurai): すでに動いています。' -ForegroundColor Green
    } else {
        Write-Host '  Redis(Memurai): 新しい窓で起動します(この窓は閉じないでください)。'
        $redisScript = Join-Path $PSScriptRoot 'start-analysis-redis-dev.ps1'
        $command = "`$Host.UI.RawUI.WindowTitle = '分析AI Redis(Memurai)(閉じると止まります)'; Set-Location '$root'; & '$redisScript'"
        Start-Process powershell.exe -ArgumentList @('-NoExit', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $command) | Out-Null
        if (-not (Wait-For 'Redis(Memurai)' { Test-Redis } 30)) { Write-Host '  Redisの窓にエラーが出ていないか、確認してください。' -ForegroundColor Red; return }
        Write-Host '  Redis(Memurai): 起動しました。' -ForegroundColor Green
    }

    # 2. launcher
    $health = Get-Health
    if ($health -and $health.status -eq 'ready') {
        Write-Host '  launcher: すでに動いています。' -ForegroundColor Green
    } else {
        Write-Host '  launcher: 新しい窓で起動します(この窓は閉じないでください)。'
        $command = "`$Host.UI.RawUI.WindowTitle = '分析AI launcher(閉じると止まります)'; wsl.exe -d Ubuntu-24.04 -u root -- python3 $wslRoot/analysis-sandbox/launcher/launcher.py"
        Start-Process powershell.exe -ArgumentList @('-NoExit', '-NoProfile', '-Command', $command) | Out-Null
        $ok = Wait-For 'launcher' { $h = Get-Health; $h -and $h.status -eq 'ready' }
        if (-not $ok) { Write-Host '  launcherの窓にエラーが出ていないか、確認してください。' -ForegroundColor Red; return }
        Write-Host '  launcher: 起動しました。' -ForegroundColor Green
    }

    # 3. 専用ワーカー
    $state = Get-State
    if ($state -and $state.worker) {
        if ($state.worker_stale) {
            Write-Host '  専用ワーカーの版が古いか確認できません。実行・後始末の状態を確認して、専用ワーカーを再起動してください。' -ForegroundColor Yellow
            return
        }
        Write-Host '  専用ワーカー: すでに動いています。' -ForegroundColor Green
    } else {
        if (Get-WorkerProcesses) {
            Write-Host '  専用ワーカーのプロセスが残っています。生存確認が戻るまで待ちます。'
        } else {
            Write-Host '  専用ワーカー: 新しい窓で起動します(この窓は閉じないでください)。'
            $command = "`$Host.UI.RawUI.WindowTitle = '分析AI 専用ワーカー(閉じると止まります)'; Set-Location '$backend'; & '$python' manage.py analysis_worker"
            Start-Process powershell.exe -ArgumentList @('-NoExit', '-NoProfile', '-Command', $command) | Out-Null
        }
        $ok = Wait-For '専用ワーカー' { $s = Get-State; $s -and $s.worker }
        if (-not $ok) {
            Write-Host '  ワーカーの窓にエラーが出ていないか、確認してください。' -ForegroundColor Red
            Write-Host '  起動できない場合は、PCの時刻帯が日本標準時か確認してください' -ForegroundColor Yellow
            return
        }
        Write-Host '  専用ワーカー: 起動しました。' -ForegroundColor Green
    }
    Write-Host ''
    Show-Status | Out-Null
    Write-Host ''
    Write-Host '準備ができました。画面の「実行基盤の状態を確認」を押してください。' -ForegroundColor Cyan
}

function Stop-Dev {
    Write-Host '=== 分析AI実行基盤を停止します ===' -ForegroundColor Cyan
    $state = Get-State
    if ($state -and $state.active) {
        Write-Host "  実行枠が使用中です(ジョブID $($state.active))。実行中に止めると、枠が塞がり、手動復旧が必要になります。" -ForegroundColor Yellow
        if ($DryRun) { Write-Host '  [確認のみ] 実際に止める場合は、ここで確認を求めます。' }
        else {
            $answer = Read-Host '  それでも止めますか? (y/N)'
            if ($answer -notin @('y', 'Y')) { Write-Host '  中止しました。何も止めていません。'; return }
        }
    }
    $workers = @(Get-WorkerProcesses)
    Write-Host "  専用ワーカー: $($workers.Count) 個のプロセスを停止します。"
    if (-not $DryRun) { foreach ($p in $workers) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue } }
    Write-Host '  launcher: 停止します。'
    if (-not $DryRun) {
        & wsl.exe -d Ubuntu-24.04 -u root -- bash "$wslRoot/analysis-sandbox/tools/stop-launcher.sh"
    }
    if ($DryRun) { Write-Host '  [確認のみ] 実際には何も止めていません。' -ForegroundColor Yellow; return }
    Start-Sleep -Seconds 3
    Show-Status | Out-Null
    Write-Host '  ※ launcher・ワーカーの窓は、手動で閉じてください。'
}

switch ($Action) {
    'start' { Start-Dev }
    'stop' { Stop-Dev }
    'status' { Show-Status | Out-Null }
}
