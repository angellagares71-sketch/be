<#
.SYNOPSIS
    Crea un acceso directo "Skyrim IA" en el Escritorio.

.DESCRIPTION
    Por defecto el acceso directo arranca la partida entera (Jugar.bat: levanta
    el gateway, espera a que responda y lanza Skyrim con SKSE). Con
    -Que Gateway crea el de antes, que solo levanta el gateway.

    Genera un .lnk con el icono de assets\skyrim-ia.ico.

    Si la creacion del .lnk falla (COM no disponible, politicas restrictivas),
    cae a un .cmd equivalente, que Windows trata igual de bien como lanzador.

.PARAMETER Que
    Que arranca: "Juego" (por defecto) lanza el gateway y Skyrim; "Gateway"
    lanza solo el gateway.

.PARAMETER Nombre
    Nombre del acceso directo. Por defecto "Skyrim IA".

.PARAMETER Destino
    Carpeta donde crearlo. Por defecto el Escritorio del usuario actual.

.PARAMETER Forzar
    Sobrescribe un acceso directo que ya exista con ese nombre.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\crear-acceso-directo.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\crear-acceso-directo.ps1 -Forzar
#>
[CmdletBinding()]
param(
    [ValidateSet("Juego", "Gateway")]
    [string]$Que = "Juego",
    [string]$Nombre = "Skyrim IA",
    [string]$Destino,
    [switch]$Forzar
)

$ErrorActionPreference = "Stop"

$raiz = Split-Path -Parent $PSScriptRoot
$icono = Join-Path $raiz "assets\skyrim-ia.ico"

if ($Que -eq "Juego") {
    $lanzar = Join-Path $raiz "Jugar.bat"
    $descripcion = "Arranca el gateway y Skyrim con IA"
} else {
    $lanzar = Join-Path $raiz "scripts\arrancar.ps1"
    $descripcion = "Arranca el gateway de Mantella para hablar con los PNJ de Skyrim"
}

if (-not (Test-Path $lanzar)) {
    throw "No se encuentra $lanzar. Ejecuta este script desde el repositorio."
}

# El Escritorio real, que con OneDrive no siempre es %USERPROFILE%\Desktop.
if (-not $Destino) {
    $Destino = [Environment]::GetFolderPath("Desktop")
}
if (-not $Destino -or -not (Test-Path $Destino)) {
    throw "No se encuentra la carpeta del Escritorio. Indica una con -Destino."
}

Write-Host "Creando el acceso directo '$Nombre'" -ForegroundColor Cyan
Write-Host "  repositorio: $raiz"
Write-Host "  escritorio : $Destino"

$lnk = Join-Path $Destino "$Nombre.lnk"
$cmd = Join-Path $Destino "$Nombre.cmd"

foreach ($existente in @($lnk, $cmd)) {
    if ((Test-Path $existente) -and -not $Forzar) {
        throw "Ya existe '$existente'. Usa -Forzar para sobrescribirlo."
    }
}

# PowerShell 5 (windows) sigue siendo el interprete mas seguro para el .lnk:
# esta en todas las instalaciones de Windows.
$interprete = "powershell.exe"
if ($env:WINDIR) {
    $candidato = Join-Path $env:WINDIR "System32\WindowsPowerShell\v1.0\powershell.exe"
    if (Test-Path $candidato) { $interprete = $candidato }
}

if ($Que -eq "Juego") {
    # Un .bat se abre solo; no hace falta envolverlo en PowerShell.
    $objetivo = $lanzar
    $argumentos = ""
} else {
    $objetivo = $interprete
    $argumentos = "-ExecutionPolicy Bypass -NoExit -File `"$lanzar`""
}

$creado = $null
try {
    $shell = New-Object -ComObject WScript.Shell
    $atajo = $shell.CreateShortcut($lnk)
    $atajo.TargetPath = $objetivo
    $atajo.Arguments = $argumentos
    $atajo.WorkingDirectory = $raiz
    $atajo.Description = $descripcion
    if (Test-Path $icono) {
        $atajo.IconLocation = "$icono,0"
    }
    $atajo.Save()
    $creado = $lnk
    if (Test-Path $cmd) { Remove-Item $cmd -Force }
} catch {
    Write-Warning "No se pudo crear el .lnk ($($_.Exception.Message)). Se creara un .cmd."
    $contenido = @"
@echo off
rem Lanzador de Skyrim IA. Generado por scripts\crear-acceso-directo.ps1
title Skyrim IA
cd /d "$raiz"
"$objetivo" $argumentos
"@
    Set-Content -Path $cmd -Value $contenido -Encoding ASCII
    $creado = $cmd
}

if (-not (Test-Path $creado)) {
    throw "El acceso directo no llego a crearse en $Destino."
}

Write-Host ""
Write-Host "Listo: $creado" -ForegroundColor Green
if ($Que -eq "Juego") {
    Write-Host "Haz doble clic para jugar: arranca el gateway y despues Skyrim."
} else {
    Write-Host "Haz doble clic para arrancar el gateway. Deja la ventana abierta mientras juegas."
}
if (-not (Test-Path (Join-Path $raiz ".env"))) {
    Write-Warning "Aun no hay fichero .env. Ejecuta antes scripts\instalar.ps1 y pon tu clave de API."
}
