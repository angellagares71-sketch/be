<#
.SYNOPSIS
    Instala Ollama, descarga el modelo y deja el gateway configurado.

.DESCRIPTION
    Es la via sin cuenta ni clave: la IA corre en el propio PC. El script
    hace de una vez lo que si no habria que hacer a mano:

      1. Instala Ollama con winget, si no esta ya.
      2. Arranca su servicio y espera a que responda.
      3. Descarga el modelo (unos 5 GB la primera vez).
      4. Escribe el .env del gateway apuntando a Ollama.

    Si ya esta hecho algun paso, se lo salta. Se puede repetir sin miedo.

.PARAMETER Modelo
    Modelo a descargar. Por defecto llama3.1:8b. Para PCs justos de memoria,
    llama3.2:3b va mucho mas ligero.

.PARAMETER SinModelo
    Instala Ollama y configura el .env, pero no descarga el modelo.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\instalar-ollama.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\instalar-ollama.ps1 -Modelo llama3.2:3b
#>
[CmdletBinding()]
param(
    [string]$Modelo = "llama3.1:8b",
    [switch]$SinModelo
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot

function Paso {
    param([string]$Texto)
    Write-Host ""
    Write-Host "  $Texto" -ForegroundColor Cyan
}

function Refrescar-Path {
    # Tras instalar, el PATH del proceso actual sigue siendo el de antes:
    # hay que releerlo para poder llamar a ollama sin reiniciar la consola.
    $partes = @()
    foreach ($ambito in @("Machine", "User")) {
        $valor = $null
        try { $valor = [Environment]::GetEnvironmentVariable("Path", $ambito) } catch { $valor = $null }
        if ($valor) { $partes += $valor }
    }
    # Si no se pudo leer ninguno, mas vale dejar el PATH como estaba que
    # vaciarlo y quedarnos sin poder llamar a nada.
    if ($partes.Count -gt 0) { $env:Path = $partes -join ";" }

    # winget lo deja aqui aunque el PATH tarde en propagarse.
    if ($env:LOCALAPPDATA) {
        $habitual = Join-Path $env:LOCALAPPDATA "Programs\Ollama"
        if ((Test-Path $habitual) -and ($env:Path -notlike "*$habitual*")) {
            $env:Path = "$env:Path;$habitual"
        }
    }
}

function Hay-Ollama {
    return [bool](Get-Command ollama -ErrorAction SilentlyContinue)
}

function Ollama-Responde {
    try {
        Invoke-WebRequest -Uri "http://localhost:11434/api/version" -UseBasicParsing -TimeoutSec 3 | Out-Null
        return $true
    } catch {
        return $false
    }
}

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "     Skyrim IA - instalar la IA en tu PC" -ForegroundColor Cyan
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Sin cuenta, sin clave y sin pagar nada." -ForegroundColor DarkGray
Write-Host "  La primera vez tarda: son unos 5 GB de descarga." -ForegroundColor DarkGray

# --- 1. Ollama -------------------------------------------------------------
Paso "[1/4] Ollama"

Refrescar-Path
if (Hay-Ollama) {
    Write-Host "  Ya esta instalado. Nos lo saltamos." -ForegroundColor Green
} else {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Host ""
        Write-Host "  [!] Este Windows no trae winget, asi que no puedo instalarlo solo." -ForegroundColor Red
        Write-Host ""
        Write-Host "      Instala Ollama a mano desde https://ollama.com/download" -ForegroundColor Yellow
        Write-Host "      (descargar, abrir, Siguiente hasta el final) y vuelve a" -ForegroundColor Yellow
        Write-Host "      ejecutar este mismo fichero: el resto lo hace solo." -ForegroundColor Yellow
        Write-Host ""
        exit 2
    }

    Write-Host "  Descargando e instalando Ollama. Esto tarda unos minutos..."
    winget install --id Ollama.Ollama --exact --silent `
        --accept-package-agreements --accept-source-agreements
    $codigo = $LASTEXITCODE

    Refrescar-Path
    if (-not (Hay-Ollama)) {
        Write-Host ""
        Write-Host "  [!] La instalacion de Ollama no ha salido bien (codigo $codigo)." -ForegroundColor Red
        Write-Host "      Instalalo a mano desde https://ollama.com/download y repite." -ForegroundColor Yellow
        exit 2
    }
    Write-Host "  Ollama instalado." -ForegroundColor Green
}

# --- 2. Servicio -----------------------------------------------------------
Paso "[2/4] Arrancando Ollama"

if (Ollama-Responde) {
    Write-Host "  Ya estaba en marcha." -ForegroundColor Green
} else {
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    $arrancado = $false
    foreach ($intento in 1..20) {
        Start-Sleep -Seconds 1
        if (Ollama-Responde) { $arrancado = $true; break }
    }
    if ($arrancado) {
        Write-Host "  En marcha." -ForegroundColor Green
    } else {
        Write-Host "  [!] Ollama no responde en el puerto 11434." -ForegroundColor Red
        Write-Host "      Abrelo desde el menu Inicio y vuelve a ejecutar este fichero." -ForegroundColor Yellow
        exit 3
    }
}

# --- 3. Modelo -------------------------------------------------------------
Paso "[3/4] Modelo $Modelo"

if ($SinModelo) {
    Write-Host "  Saltado (-SinModelo)." -ForegroundColor Yellow
} else {
    $ya = ""
    try { $ya = (& ollama list 2>&1 | Out-String) } catch { $ya = "" }
    if ($ya -match [regex]::Escape($Modelo)) {
        Write-Host "  Ya esta descargado. Nos lo saltamos." -ForegroundColor Green
    } else {
        Write-Host "  Descargando. Son unos 5 GB: dejalo hasta que acabe." -ForegroundColor DarkGray
        Write-Host ""
        & ollama pull $Modelo
        if ($LASTEXITCODE -ne 0) {
            Write-Host ""
            Write-Host "  [!] La descarga del modelo ha fallado." -ForegroundColor Red
            Write-Host "      Suele ser la conexion. Vuelve a ejecutar este fichero:" -ForegroundColor Yellow
            Write-Host "      continua por donde iba, no empieza de cero." -ForegroundColor Yellow
            exit 4
        }
        Write-Host ""
        Write-Host "  Modelo listo." -ForegroundColor Green
    }
}

# --- 4. .env del gateway ---------------------------------------------------
Paso "[4/4] Configurando el gateway"

$destino = Join-Path $raiz ".env"
$lineas = @(
    "# Generado por scripts\instalar-ollama.ps1",
    "MANTELLA_PROVIDER=ollama",
    "MANTELLA_MODEL=$Modelo",
    "MANTELLA_API_KEY=",
    "MANTELLA_HOST=127.0.0.1",
    "MANTELLA_PORT=8000",
    "MANTELLA_TEMPERATURE=0.8",
    "MANTELLA_MAX_TOKENS=250",
    "MANTELLA_SANITIZE=true",
    "MANTELLA_STRIP_ACTIONS=true",
    "MANTELLA_MAX_SENTENCES=2",
    "MANTELLA_TIMEOUT=60",
    "MANTELLA_MAX_RETRIES=2",
    "MANTELLA_LOG_LEVEL=INFO",
    "MANTELLA_SYSTEM_PREFIX=Responde siempre en espanol, en una o dos frases cortas, sin describir acciones."
)
Set-Content -Path $destino -Value $lineas -Encoding UTF8

# .env es un fichero oculto: sin -Force, Get-Item no lo ve.
$escrito = Get-Item $destino -Force -ErrorAction SilentlyContinue
if (-not $escrito -or $escrito.Length -eq 0) {
    Write-Host "  [!] No se ha podido escribir $destino" -ForegroundColor Red
    exit 5
}
Write-Host "  Guardado en $destino" -ForegroundColor Green

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Green
Write-Host "     Listo. La IA ya corre en tu PC." -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Solo queda una linea en el config.ini de Mantella:" -ForegroundColor DarkGray
Write-Host "     llm_api = http://localhost:8000/v1"
Write-Host "     model   = mantella"
Write-Host ""
exit 0
