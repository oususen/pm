# AppData\Local キャッシュ整理手順

対象: `C:\Users\user\AppData\Local`

## 1. 上位容量フォルダを確認

```powershell
$base = $env:LOCALAPPDATA
Get-ChildItem $base -Directory -Force | ForEach-Object {
  $size = (Get-ChildItem $_.FullName -Recurse -Force -File -ErrorAction SilentlyContinue |
    Measure-Object -Property Length -Sum).Sum
  [PSCustomObject]@{
    Folder = $_.FullName
    SizeGB = [math]::Round(($size/1GB),2)
  }
} | Sort-Object SizeGB -Descending | Select-Object -First 20 | Format-Table -AutoSize
```

## 2. 安全なキャッシュを削除

```powershell
$targets = @(
  "$env:LOCALAPPDATA\Temp\*",
  "$env:LOCALAPPDATA\CrashDumps\*",
  "$env:LOCALAPPDATA\npm-cache\*",
  "$env:LOCALAPPDATA\pypa\Cache\*",
  "$env:LOCALAPPDATA\obsidian-updater\*",
  "$env:LOCALAPPDATA\ms-playwright-go\*"
)
foreach ($t in $targets) {
  Remove-Item $t -Recurse -Force -ErrorAction SilentlyContinue
}
```

## 3. Microsoft 配下の内訳を確認

```powershell
Get-ChildItem "$env:LOCALAPPDATA\Microsoft" -Directory -Force | ForEach-Object {
  $size = (Get-ChildItem $_.FullName -Recurse -Force -File -ErrorAction SilentlyContinue |
    Measure-Object -Property Length -Sum).Sum
  [PSCustomObject]@{
    Folder = $_.Name
    SizeGB = [math]::Round(($size/1GB),2)
  }
} | Sort-Object SizeGB -Descending | Select-Object -First 20 | Format-Table -AutoSize
```

## 4. Edge / Office / Outlook のキャッシュ削除

実行前に `Edge` `Outlook` `Office` を終了する。

```powershell
$paths = @(
  "$env:LOCALAPPDATA\Microsoft\Edge\User Data\*\Cache\*",
  "$env:LOCALAPPDATA\Microsoft\Edge\User Data\*\Code Cache\*",
  "$env:LOCALAPPDATA\Microsoft\Edge\User Data\*\GPUCache\*",
  "$env:LOCALAPPDATA\Microsoft\Edge\User Data\*\Service Worker\CacheStorage\*",
  "$env:LOCALAPPDATA\Microsoft\Office\16.0\OfficeFileCache\*",
  "$env:LOCALAPPDATA\Microsoft\Office\SolutionPackages\*",
  "$env:LOCALAPPDATA\Microsoft\Outlook\RoamCache\*",
  "$env:LOCALAPPDATA\Microsoft\Windows\INetCache\Content.Outlook\*"
)
foreach ($p in $paths) {
  Remove-Item $p -Recurse -Force -ErrorAction SilentlyContinue
}
```

## 5. 削除後に再計測

```powershell
Get-ChildItem "$env:LOCALAPPDATA\Microsoft" -Directory -Force | ForEach-Object {
  $size = (Get-ChildItem $_.FullName -Recurse -Force -File -ErrorAction SilentlyContinue |
    Measure-Object -Property Length -Sum).Sum
  [PSCustomObject]@{
    Folder = $_.Name
    SizeGB = [math]::Round(($size/1GB),2)
  }
} | Sort-Object SizeGB -Descending | Select-Object -First 10 | Format-Table -AutoSize
```

## 注意点

- `Programs` と `Packages` は原則削除しない（アプリ本体）。
- `Outlook` の `*.ost` は削除可能だが、再同期に時間と通信量がかかるため最終手段。
