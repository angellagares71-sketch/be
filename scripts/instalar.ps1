<#
.SYNOPSIS
    Instala el gateway de Mantella en Windows: entorno virtual, dependencias
    y fichero .env a partir del ejemplo.
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\instalar.ps1
#>
[CmdletBinding()]
param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$venv = Join-Path $raiz ".venv"

Write-Host "Instalando el gateway de Mantella en $raiz" -ForegroundColor Cyan

# 1. Comprobar Python 3.10 o superior.
try {
    $version = & $Python -c "import sys; print('%d.%d' % sys.version_info[:2])"
} catch {
    throw "No se encuentra '$Python'. Instala Python 3.10+ desde https://www.python.org/downloads/ y marca 'Add python.exe to PATH'."
}
$partes = $version.Split(".")
if ([int]$partes[0] -lt 3 -or ([int]$partes[0] -eq 3 -and [int]$partes[1] -lt 10)) {
    throw "Se necesita Python 3.10 o superior; se encontro $version."
}
Write-Host "  Python $version encontrado" -ForegroundColor Green

# 2. Entorno virtual.
if (-not (Test-Path $venv)) {
    Write-Host "  Creando el entorno virtual..." -ForegroundColor Cyan
    & $Python -m venv $venv
}
$pip = Join-Path $venv "Scripts\pip.exe"
if (-not (Test-Path $pip)) { throw "No se creo el entorno virtual en $venv" }

# 3. Dependencias.
Write-Host "  Instalando dependencias..." -ForegroundColor Cyan
& $pip install --quiet --upgrade pip
& $pip install --quiet -r (Join-Path $raiz "server\requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Fallo la instalacion de dependencias." }
Write-Host "  Dependencias instaladas" -ForegroundColor Green

# 4. Fichero .env.
$env_destino = Join-Path $raiz ".env"
$env_ejemplo = Join-Path $raiz "config\gateway.env.ejemplo"
if (Test-Path $env_destino) {
    Write-Host "  Ya existe .env, no se toca" -ForegroundColor Yellow
} else {
    Copy-Item $env_ejemplo $env_destino
    Write-Host "  Creado .env a partir del ejemplo" -ForegroundColor Green
}

Write-Host ""
Write-Host "Instalacion terminada." -ForegroundColor Green
Write-Host "Siguiente paso: edita .env y pon tu clave de API en MANTELLA_API_KEY."
Write-Host "Despues arranca el gateway con:  powershell -ExecutionPolicy Bypass -File scripts\arrancar.ps1"
Write-Host ""
Write-Host "Para tenerlo a mano, crea un acceso directo en el Escritorio con:"
Write-Host "  powershell -ExecutionPolicy Bypass -File scripts\crear-acceso-directo.ps1"
