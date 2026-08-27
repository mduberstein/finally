$root = Split-Path -Path $PSScriptRoot -Parent
Set-Location $root

docker compose down
