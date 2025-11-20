Param(
  [string]$Symbol = "AAPL",
  [string]$Tf = "1d",
  [int]$Limit = 300,
  [double]$Threshold = 0.55,
  [int]$FeesBps = 10,
  [int]$SlippageBps = 5,
  # muda para caminho absoluto se quiseres (ex.: "D:\02_RO_\RO_TRADE\ML_Trade\exports")
  [string]$ExportRoot = (Join-Path (Resolve-Path .) "exports"),
  [switch]$PostJson,          # se passado, faz também as versões POST
  [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

# 0) health check rápido
$health = Invoke-RestMethod "$BaseUrl/health"
if ($health.status -ne "ok") { throw "API não está OK: $($health | ConvertTo-Json -Compress)" }

# 1) garantir pasta do dia
$day    = Get-Date -Format 'yyyyMMdd'
$stamp  = Get-Date -Format 'yyyyMMdd_HHmmss'
$prefix = "${Symbol}_${Tf}"
$outDir = Join-Path $ExportRoot $day
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

Write-Host "Export dir: $outDir"

# 2) nomes de ficheiro
$equityCsvGet = Join-Path $outDir "equity_${prefix}_${stamp}.csv"
$tradesCsvGet = Join-Path $outDir "trades_${prefix}_${stamp}.csv"
$sweepCsv     = Join-Path $outDir "sweep_${prefix}_${stamp}.csv"

$equityCsvPost = Join-Path $outDir "equity_${prefix}_post_${stamp}.csv"
$tradesCsvPost = Join-Path $outDir "trades_${prefix}_post_${stamp}.csv"

# 3) GET — equity/trades/sweep
$qs = "symbol=$Symbol&tf=$Tf&limit=$Limit&threshold=$Threshold&fees_bps=$FeesBps&slippage_bps=$SlippageBps"

Invoke-RestMethod "$BaseUrl/ml/backtest/equity.csv?$qs" -OutFile $equityCsvGet
Invoke-RestMethod "$BaseUrl/ml/backtest/trades.csv?$qs" -OutFile $tradesCsvGet

# sweep típico; ajusta o range se quiseres
$thresholds = "0.50:0.65:0.01"
Invoke-RestMethod "$BaseUrl/ml/backtest/sweep.csv?symbol=$Symbol&tf=$Tf&limit=$Limit&thresholds=$thresholds&metric=expectancy&fees_bps=$FeesBps&slippage_bps=$SlippageBps" `
  -OutFile $sweepCsv

# 4) POST — versões equivalentes (opcional com -PostJson)
if ($PostJson) {
  $body = @{
    symbol       = $Symbol
    tf           = $Tf
    limit        = $Limit
    threshold    = $Threshold
    fees_bps     = $FeesBps
    slippage_bps = $SlippageBps
  } | ConvertTo-Json

  Invoke-RestMethod -Method POST -Uri "$BaseUrl/ml/backtest/equity.csv" -ContentType application/json -Body $body -OutFile $equityCsvPost
  Invoke-RestMethod -Method POST -Uri "$BaseUrl/ml/backtest/trades.csv" -ContentType application/json -Body $body -OutFile $tradesCsvPost
}

# 5) resumo
Write-Host ""
Write-Host "==> Ficheiros gerados:"
Write-Host " - $equityCsvGet"
Write-Host " - $tradesCsvGet"
Write-Host " - $sweepCsv"
if ($PostJson) {
  Write-Host " - $equityCsvPost"
  Write-Host " - $tradesCsvPost"
}
