# 開発Ubuntuを非表示で維持し、既存Portainerだけを起動する。
param([switch]$NoBrowser)

$ErrorActionPreference = 'Stop'
$taskMutex = New-Object System.Threading.Mutex($false, 'Local\PM.Portainer.Dev.Start')
$taskLockHeld = $false
$taskNewKeepAlive = $null
try {
    $taskLockHeld = $taskMutex.WaitOne(0)
    if (-not $taskLockHeld) {
        Write-Host 'Portainer startup is already in progress.'
        exit 0
    }

    # この起動スクリプトの待機プロセスだけを識別し、二重起動しない。
    $taskMarker = 'pm-portainer-dev-keepalive'
    $taskExisting = Get-CimInstance Win32_Process -Filter "Name = 'wsl.exe'" |
        Where-Object { $_.CommandLine -and $_.CommandLine.Contains($taskMarker) } |
        Select-Object -First 1
    if ($taskExisting) {
        $taskKeepAlive = Get-Process -Id $taskExisting.ProcessId
    } else {
        $taskKeepAlive = Start-Process -FilePath 'wsl.exe' -WindowStyle Hidden -PassThru -ArgumentList '-d Ubuntu-24.04 -u daiso -- bash -c "exec -a pm-portainer-dev-keepalive sleep infinity"'
        $taskNewKeepAlive = $taskKeepAlive
    }

    & wsl.exe -d Ubuntu-24.04 -u root -- systemctl start docker
    if ($LASTEXITCODE -ne 0) { throw 'Docker could not be started in Ubuntu-24.04.' }
    & wsl.exe -d Ubuntu-24.04 -u root -- docker start pm-portainer-dev
    if ($LASTEXITCODE -ne 0) { throw 'The existing pm-portainer-dev container could not be started.' }

    # 自己署名証明書の確認省略は、ローカルの状態確認だけに限定する。
    # ブラウザやWindowsの証明書・ファイアウォール設定は変更しない。
    do {
        if ($taskKeepAlive.HasExited) { throw 'The Ubuntu keep-alive process exited.' }
        $taskStatus = & curl.exe --insecure --silent --fail 'https://localhost:9443/api/system/status' 2>$null
        if ($LASTEXITCODE -eq 0) {
            $taskStatusObject = $taskStatus | ConvertFrom-Json
            if (-not $taskStatusObject.Version) { throw 'The local service did not return a Portainer version.' }
            break
        }
        Start-Sleep -Seconds 1
    } while ($true)

    Write-Host 'Portainer is ready: https://localhost:9443/'
    if (-not $NoBrowser) { Start-Process 'https://localhost:9443/' }
} catch {
    # 今回新たに作った待機プロセスだけを停止し、既存Ubuntuや他ジョブは止めない。
    if ($taskNewKeepAlive -and -not $taskNewKeepAlive.HasExited) {
        Stop-Process -Id $taskNewKeepAlive.Id -ErrorAction SilentlyContinue
    }
    Write-Host ('Startup failed: ' + $_.Exception.Message)
    exit 1
} finally {
    if ($taskLockHeld) { $taskMutex.ReleaseMutex() }
    $taskMutex.Dispose()
}
