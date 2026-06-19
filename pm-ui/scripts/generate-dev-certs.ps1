param(
  [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"

if (-not $ProjectRoot) {
  $ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
}

$certDir = Join-Path $ProjectRoot "certs"
$envLocal = Join-Path $ProjectRoot ".env.local"

if (-not (Get-Command openssl -ErrorAction SilentlyContinue)) {
  throw "openssl not found. Install OpenSSL or add it to PATH."
}

New-Item -ItemType Directory -Force -Path $certDir | Out-Null

try {
  $ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
    Where-Object {
      $_.IPAddress -and
      $_.IPAddress -notlike "169.254*" -and
      $_.IPAddress -ne "127.0.0.1" -and
      $_.IPAddress -ne "0.0.0.0"
    } |
    Select-Object -ExpandProperty IPAddress -Unique
} catch {
  $ips = @(
    ipconfig |
      Select-String "IPv4 Address" |
      ForEach-Object {
        if ($_.Line -match ":\s*(\d+\.\d+\.\d+\.\d+)\s*$") {
          $matches[1]
        }
      }
  ) | Select-Object -Unique
}

$sanParts = @("DNS:localhost", "IP:127.0.0.1")
if ($ips) {
  $sanParts += ($ips | ForEach-Object { "IP:$($_)" })
}

$san = $sanParts -join ","
Set-Content -Path (Join-Path $certDir "pm-ui.ext") -Value ("subjectAltName=" + $san) -Encoding ascii

$caKey = Join-Path $certDir "pm-ui-ca.key"
$caCrt = Join-Path $certDir "pm-ui-ca.crt"

if (-not (Test-Path $caKey) -or -not (Test-Path $caCrt)) {
  & openssl genrsa -out $caKey 2048 | Out-Null
  & openssl req -x509 -new -nodes -key $caKey -sha256 -days 3650 -subj "/CN=pm-ui-dev-ca" -out $caCrt | Out-Null
}

$srvKey = Join-Path $certDir "pm-ui.key"
$srvCsr = Join-Path $certDir "pm-ui.csr"
$srvCrt = Join-Path $certDir "pm-ui.crt"

& openssl genrsa -out $srvKey 2048 | Out-Null
& openssl req -new -key $srvKey -subj "/CN=pm-ui" -out $srvCsr | Out-Null
& openssl x509 -req -in $srvCsr -CA $caCrt -CAkey $caKey -CAcreateserial -out $srvCrt -days 825 -sha256 -extfile (Join-Path $certDir "pm-ui.ext") | Out-Null

Set-Content -Path $envLocal -Value "VITE_HTTPS=true`nVITE_HTTPS_KEY=certs/pm-ui.key`nVITE_HTTPS_CERT=certs/pm-ui.crt`n" -Encoding ascii

Write-Host "Done. SANs: $san"
Write-Host "CA cert: $caCrt"
Write-Host "Server cert: $srvCrt"
