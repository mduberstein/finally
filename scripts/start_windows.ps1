# Build (if needed) and run the FinAlly container. Safe to run repeatedly.
# Usage: .\scripts\start_windows.ps1 [--build]

$image = "finally"
$container = "finally"
$volume = "finally-data"
$port = 8000

Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".env")) {
    Write-Host "No .env found. Copy .env.example to .env and add your keys."
    exit 1
}

$build = $args -contains "--build"

docker image inspect $image 2>&1 | Out-Null
$hasImage = ($LASTEXITCODE -eq 0)

if ($build -or -not $hasImage) {
    Write-Host "Building image $image"
    docker build -t $image .
    if ($LASTEXITCODE -ne 0) { exit 1 }
}

$running = docker ps -q -f "name=^$container$"
if (-not $build -and $running) {
    Write-Host "Container $container is already running at http://localhost:$port"
    exit 0
}

docker rm -f $container 2>&1 | Out-Null

docker run -d --name $container -p "${port}:8000" -v "${volume}:/app/db" --env-file .env $image | Out-Null
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "FinAlly is running at http://localhost:$port"
