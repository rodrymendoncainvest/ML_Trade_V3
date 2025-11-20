Param(
  [string]$ComposeFile = "docker-compose.yml",
  [string]$StableTag   = "ml_trade-api:stable"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Garante que a imagem está local
docker image inspect $StableTag | Out-Null

# Sobe o serviço usando a imagem estável (sem rebuild)
docker compose -f $ComposeFile down -v
docker compose -f $ComposeFile up -d

Write-Host "Rollback efetuado com $StableTag" -ForegroundColor Yellow
