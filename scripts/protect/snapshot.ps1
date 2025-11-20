Param(
  [string]$Tag = $(Get-Date -Format "yyyyMMdd-HHmm"),
  [string]$BaseUrl = $env:BASE_URL ? $env:BASE_URL : "http://localhost:8000"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# 1) Pasta do snapshot
$root = Get-Location
$dir  = Join-Path $root ("snapshots\" + $Tag)
New-Item -ItemType Directory -Force -Path $dir | Out-Null

# 2) Verifica saúde e guarda OpenAPI
$health = Invoke-RestMethod "$BaseUrl/_debug/health"
if (-not $health.ok) { throw "Health não OK" }
Invoke-RestMethod "$BaseUrl/openapi.json" | ConvertTo-Json -Depth 12 | Out-File (Join-Path $dir "openapi.json") -Encoding UTF8

# 3) Git: commit e tag leve (se repo existir)
if (Test-Path .git) {
  git add -A
  git commit -m "snapshot: $Tag" | Out-Null
  git tag "snap-$Tag"
  git rev-parse HEAD | Out-File (Join-Path $dir "git_HEAD.txt")
}

# 4) Docker: tag estável + tar
#   assume imagem local ml_trade-api:latest
$img = "ml_trade-api:latest"
$stableTag = "ml_trade-api:stable"
$tsTag     = "ml_trade-api:stable-$Tag"

docker image tag $img $stableTag
docker image tag $img $tsTag

# 5) Inspeção da imagem
docker image inspect $img | Out-File (Join-Path $dir "image_inspect.json")
docker image inspect $tsTag | Out-File (Join-Path $dir "image_stable_inspect.json")

# 6) Export da imagem estável com timestamp
$tar = Join-Path $dir ("ml_trade-api-" + $Tag + ".tar")
docker image save -o $tar $tsTag

# 7) Guardar env efetivo (DEBUG/LOG_LEVEL e .env se existir)
$envOut = @{
  DEBUG     = $env:DEBUG
  LOG_LEVEL = $env:LOG_LEVEL
}
$envOut | ConvertTo-Json | Out-File (Join-Path $dir "env_runtime.json")
if (Test-Path ".env") { Copy-Item ".env" (Join-Path $dir ".env.snapshot") -Force }

Write-Host "Snapshot criado em: $dir" -ForegroundColor Green
Write-Host "Imagem estável: $stableTag  |  Timestamp: $tsTag" -ForegroundColor Green
