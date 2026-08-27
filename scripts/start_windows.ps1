$root = Split-Path -Path $PSScriptRoot -Parent
Set-Location $root

if (-Not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Write-Error "Docker not installed. Install Docker Desktop and retry."
  exit 1
}

if (-Not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created .env from .env.example"
}

New-Item -ItemType Directory -Path "db" -Force | Out-Null
docker compose up --build -d
Start-Sleep -Seconds 1
Start-Process "http://localhost:8003"
