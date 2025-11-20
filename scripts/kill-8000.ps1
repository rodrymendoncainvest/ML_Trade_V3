# scripts/kill-8000.ps1
param([int]$Port = 8000)

Write-Host ">> Libertar porta ${Port}"

# 1) Matar listeners em LISTEN
$pids = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
  Select-Object -ExpandProperty OwningProcess -Unique

if (-not $pids) {
  Write-Host "Sem listeners em ${Port}"
} else {
  foreach ($pid in $pids) {
    try {
      $p = Get-Process -Id $pid -ErrorAction Stop
      Write-Host ("Killing PID {0} ({1}) {2}" -f $pid, $p.Name, $p.Path)
      Stop-Process -Id $pid -Force -ErrorAction Stop
    } catch {
      Write-Warning ("Skip PID {0}: {1}" -f $pid, $_.Exception.Message)
    }
  }
}

# 2) Limpar reservas HTTP.sys que às vezes prendem a porta
$acl = (netsh http show urlacl) 2>$null
if ($acl -and ($acl | Select-String -SimpleMatch ":${Port}/")) {
  Write-Host "Encontradas reservas HTTP.sys na ${Port}:"
  $acl | Select-String -SimpleMatch ":${Port}/" | ForEach-Object {
    $line = $_.ToString().Trim()
    if ($line -match "^\s*([Hh][Tt][Tt][Pp]://\+:\d+/\S*)") {
      $url = $Matches[1]
      Write-Host "Removendo URLACL $url"
      netsh http delete urlacl url=$url | Out-Null
    }
  }
}

Write-Host "Estado final:"
Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
