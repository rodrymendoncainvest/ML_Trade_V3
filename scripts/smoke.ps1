# scripts/smoke.ps1
# Smoke test da ML API: health -> openapi -> train -> models -> predict
param(
  [string]$BaseUrl = "http://localhost:8000",
  [string]$Symbol = "AAPL",
  [string]$Tf     = "1d",
  [int]$TrainLimit = 1200,
  [int]$PredLimit  = 300
)

$ErrorActionPreference = "Stop"

function Assert($cond, $msg) {
  if (-not $cond) { throw $msg }
}

Write-Host "==> 1) HEALTH" -ForegroundColor Cyan
$health = Invoke-RestMethod "$BaseUrl/health"
Assert ($health.status -eq "ok") "Health check falhou."
Write-Host "OK /health`n" -ForegroundColor Green

Write-Host "==> 2) OPENAPI" -ForegroundColor Cyan
$openapi = Invoke-RestMethod "$BaseUrl/openapi.json"
$paths = $openapi.paths.PSObject.Properties | Select-Object -ExpandProperty Name
Assert ($paths -contains "/ml/train")   "Falta /ml/train"
Assert ($paths -contains "/ml/predict") "Falta /ml/predict"
Assert ($paths -contains "/ml/models")  "Falta /ml/models"
Write-Host "OK rotas: $($paths -join ', ' )`n" -ForegroundColor Green

Write-Host "==> 3) TRAIN ($Symbol $Tf, limit=$TrainLimit)" -ForegroundColor Cyan
$trainBody = @{ symbol = $Symbol; tf = $Tf; limit = $TrainLimit } | ConvertTo-Json
$train = Invoke-RestMethod -Method POST -Uri "$BaseUrl/ml/train" -ContentType application/json -Body $trainBody
Assert ($train.ok -eq $true) "Treino não devolveu ok=true."
Write-Host "OK train: key=$($train.key) rows=$($train.meta.rows) rows_features=$($train.meta.rows_features) as_of=$($train.meta.as_of)`n" -ForegroundColor Green

Write-Host "==> 4) MODELS" -ForegroundColor Cyan
$models = Invoke-RestMethod "$BaseUrl/ml/models"
Assert ($models.ok -eq $true) "/ml/models não devolveu ok=true."
$modelKey = "$($Symbol)_$($Tf)"
$model = $models.models | Where-Object { $_.key -eq $modelKey }
Assert ($null -ne $model) "Modelo $modelKey não encontrado."
Write-Host "OK models: encontrado $modelKey em $($model.path)`n" -ForegroundColor Green

Write-Host "==> 5) PREDICT ($Symbol $Tf, limit=$PredLimit)" -ForegroundColor Cyan
$predBody = @{ symbol = $Symbol; tf = $Tf; limit = $PredLimit } | ConvertTo-Json
$pred = Invoke-RestMethod -Method POST -Uri "$BaseUrl/ml/predict" -ContentType application/json -Body $predBody
Assert ($pred.ok -eq $true) "Predict não devolveu ok=true."
Write-Host "OK predict: key=$($pred.key) signal=$($pred.prediction.signal) proba_up=$([math]::Round([double]$pred.prediction.proba_up,4)) last_close=$($pred.prediction.last_close)`n" -ForegroundColor Green

Write-Host "==== RESUMO ====" -ForegroundColor Yellow
[pscustomobject]@{
  health      = $health.status
  train_ok    = $train.ok
  model_key   = $modelKey
  model_path  = $model.path
  predict_ok  = $pred.ok
  signal      = $pred.prediction.signal
  proba_up    = [math]::Round([double]$pred.prediction.proba_up, 6)
  last_close  = $pred.prediction.last_close
} | Format-List
