# Stop and remove the FinAlly container. The finally-data volume is kept.

$container = "finally"

$existing = docker ps -aq -f "name=^$container$"
if (-not $existing) {
    Write-Host "Container $container does not exist. Nothing to stop."
    exit 0
}

docker rm -f $container | Out-Null
Write-Host "Stopped and removed container $container. Volume finally-data kept."
