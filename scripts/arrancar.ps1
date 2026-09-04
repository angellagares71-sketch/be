<#
.SYNOPSIS
    Arranca el gateway de Mantella. Deja esta ventana abierta mientras juegas.
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\arrancar.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$python = Join-Path $raiz ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "No hay entorno virtual. Ejecuta antes: powershell -ExecutionPolicy Bypass -File scripts\instalar.ps1"
}
if (-not (Test-Path (Join-Path $raiz ".env"))) {
    Write-Warning "No hay fichero .env; se usaran los valores por defecto."
}

Write-Host "Arrancando el gateway. Deja esta ventana abierta mientras juegas." -ForegroundColor Cyan
Write-Host "Para pararlo: Ctrl+C" -ForegroundColor DarkGray
Write-Host ""

Push-Location (Join-Path $raiz "server")
try {
    $env:MANTELLA_GATEWAY_ENV = Join-Path $raiz ".env"
    & $python -m mantella_gateway
} finally {
    Pop-Location
}
