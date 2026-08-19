# NOTE: This script mirrors scripts/start_mac.sh's docker CLI logic 1:1.
# It has NOT been executed or verified on Windows in this development
# session -- the development machine is macOS. Verify the docker
# inspect/start/run behavior below before relying on it for a live demo.

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$ContainerName = "finally"
$ImageName = "finally"

$BuildRequested = $false
if ($args.Count -gt 0 -and $args[0] -eq "--build") {
    $BuildRequested = $true
}

docker image inspect $ImageName *> $null
$imageExists = ($LASTEXITCODE -eq 0)

if ($BuildRequested -or -not $imageExists) {
    Write-Host "Building the $ImageName image..."
    docker build -t $ImageName $RepoRoot
}

$envPath = Join-Path $RepoRoot ".env"
$envExamplePath = Join-Path $RepoRoot ".env.example"
if (-not (Test-Path $envPath)) {
    Copy-Item $envExamplePath $envPath
    Write-Host "Created .env from .env.example. Add your OpenRouter API key before AI chat will work."
}

$state = docker inspect -f "{{.State.Status}}" $ContainerName 2>$null
if ($LASTEXITCODE -ne 0 -or -not $state) {
    $state = "absent"
}

switch ($state) {
    "running" {
        Write-Host "$ContainerName is already running at http://localhost:8000"
    }
    "exited" {
        docker start $ContainerName | Out-Null
        Write-Host "Started the existing $ContainerName container."
    }
    "created" {
        docker start $ContainerName | Out-Null
        Write-Host "Started the existing $ContainerName container."
    }
    default {
        docker run -d --name $ContainerName `
            -p 127.0.0.1:8000:8000 `
            -v "${RepoRoot}/db:/app/db" `
            --env-file $envPath `
            $ImageName | Out-Null
        Write-Host "Created and started the $ContainerName container."
    }
}

$ready = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 2 | Out-Null
        $ready = $true
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}

if ($ready) {
    Write-Host "finally is ready at http://localhost:8000"
    Start-Process "http://localhost:8000"
    exit 0
} else {
    Write-Error "finally did not become healthy in time. Check container logs with: docker logs $ContainerName"
    exit 1
}
