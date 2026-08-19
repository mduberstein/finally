# NOTE: This script mirrors scripts/stop_mac.sh's docker CLI logic 1:1.
# It has NOT been executed or verified on Windows in this development
# session -- the development machine is macOS. Verify the docker
# inspect/stop behavior below before relying on it for a live demo.

$ErrorActionPreference = "Stop"

$ContainerName = "finally"

$running = docker inspect -f "{{.State.Running}}" $ContainerName 2>$null
if ($LASTEXITCODE -ne 0 -or -not $running) {
    $running = "false"
}

if ($running -eq "true") {
    docker stop $ContainerName | Out-Null
    Write-Host "Stopped $ContainerName. Data under db/ is preserved."
} else {
    Write-Host "$ContainerName is not running."
}
