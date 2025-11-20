param(
  [Parameter(Position=0)][string]$Cmd,
  [string]$Symbol,
  [string]$Exchange,
  [string]$Tf = "1h",
  [int]$Horizon = 24,
  [int]$Top = 5
)

$ErrorActionPreference = "Stop"

function Get-ApiPort {
  $portLine = docker compose port api 8000 | Select-Object -First 1
  if (-not $portLine) {
    Write-Error "API não está a correr. Faz: docker compose up -d"
  }
  return ($portLine -replace '.*:', '')
}

function Use-Api {
  if (-not $env:BASE_URL -or $env:BASE_URL -match ':$') {
    $p = Get-ApiPort
    $env:BASE_URL = "http://127.0.0.1:$p"
  }
  return $env:BASE_URL
}

function Health {
  $base = Use-Api
  try {
    return Invoke-RestMethod "$base/_debug/health" -TimeoutSec 5
  } catch {
    # fallback quando /_debug/health não existe
    return Invoke-RestMethod "$base/" -TimeoutSec 5
  }
}

function Root { $base = Use-Api; Invoke-RestMethod "$base/" -TimeoutSec 5 }

function Resolve([string]$symbol,[string]$exchange,[string]$provider="yahoo") {
  $base = Use-Api
  Invoke-RestMethod ("$base/symbols/resolve?symbol={0}&exchange={1}&provider={2}" -f $symbol,$exchange,$provider)
}

function Dataset([string]$symbol,[string]$tf="1h",[string]$columns="time,close",[int]$limit=3) {
  $base = Use-Api
  Invoke-RestMethod ("$base/dataset/?symbol={0}&tf={1}&columns={2}&limit={3}" -f $symbol,$tf,$columns,$limit)
}

function MLTrain([string]$symbol,[string]$tf="1h",[int]$horizon=24,[int]$threshold_bps=10) {
  $base = Use-Api
  Invoke-RestMethod ("$base/ml/train?symbol={0}&tf={1}&horizon={2}&threshold_bps={3}" -f $symbol,$tf,$horizon,$threshold_bps)
}

function MLPredict([string]$symbol,[string]$tf="1h") {
  $base = Use-Api
  Invoke-RestMethod ("$base/ml/predict?symbol={0}&tf={1}" -f $symbol,$tf)
}

function MLScan([string]$tf="1h",[string]$universe="ASML.AS,MC.PA,STM@XMIL",[int]$top=5) {
  $base = Use-Api
  $uni = [System.Uri]::EscapeDataString($universe)
  Invoke-RestMethod ("$base/ml/scan?tf={0}&universe={1}&top={2}" -f $tf,$uni,$top)
}

switch ($Cmd) {
  "health"    { Health    | Format-Table -AutoSize; break }
  "root"      { Root      | Format-List; break }
  "resolve"   {
    if (-not $Symbol -or -not $Exchange) { Write-Error "uso: ops.ps1 resolve -Symbol ASML -Exchange XAMS"; exit 1 }
    Resolve $Symbol $Exchange | Format-Table -AutoSize; break
  }
  "dataset"   {
    if (-not $Symbol) { Write-Error "uso: ops.ps1 dataset -Symbol ASML.AS [-Tf 1h]"; exit 1 }
    Dataset $Symbol $Tf | Format-List; break
  }
  "ml-train"  {
    if (-not $Symbol) { Write-Error "uso: ops.ps1 ml-train -Symbol ASML.AS [-Tf 1h] [-Horizon 24]"; exit 1 }
    MLTrain $Symbol $Tf $Horizon | Format-List; break
  }
  "ml-predict"{
    if (-not $Symbol) { Write-Error "uso: ops.ps1 ml-predict -Symbol ASML.AS [-Tf 1h]"; exit 1 }
    MLPredict $Symbol $Tf | Format-List; break
  }
  "ml-scan"   { MLScan $Tf | Format-List; break }
  default {
    Write-Host "Comandos:" -ForegroundColor Cyan
    Write-Host "  health                         # /_debug/health (ou / se não existir)"
    Write-Host "  root                           # /"
    Write-Host "  resolve   -Symbol ASML -Exchange XAMS"
    Write-Host "  dataset   -Symbol ASML.AS [-Tf 1h]"
    Write-Host "  ml-train  -Symbol ASML.AS [-Tf 1h] [-Horizon 24]"
    Write-Host "  ml-predict -Symbol ASML.AS [-Tf 1h]"
    Write-Host "  ml-scan    [-Tf 1h]  # universo default: ASML.AS,MC.PA,STM@XMIL"
  }
}
