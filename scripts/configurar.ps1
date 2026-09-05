<#
.SYNOPSIS
    Pregunta por el proveedor y la clave de API y escribe el fichero .env.

.DESCRIPTION
    Evita tener que editar el .env a mano. Comprueba la conexion con el
    proveedor antes de guardar, para que un error de clave salga aqui y no
    a mitad de partida.

.PARAMETER Forzar
    Reescribe el .env aunque ya exista, sin preguntar.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\configurar.ps1
#>
[CmdletBinding()]
param([switch]$Forzar)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$env_destino = Join-Path $raiz ".env"

if ((Test-Path $env_destino) -and -not $Forzar) {
    Write-Host "Ya existe un fichero .env." -ForegroundColor Yellow
    $r = Read-Host "Quieres reescribirlo? (s/N)"
    if ($r -notmatch '^[sSyY]') {
        Write-Host "Se conserva el .env actual." -ForegroundColor Green
        exit 0
    }
}

Write-Host ""
Write-Host "=== Configuracion de Skyrim IA ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "De donde quieres que salgan las respuestas de los PNJ?"
Write-Host ""
Write-Host "  1) OpenRouter  - en la nube, muchos modelos, necesita clave (lo mas facil)"
Write-Host "  2) Ollama      - en tu PC, gratis y sin conexion, requiere instalar Ollama"
Write-Host "  3) OpenAI      - en la nube, necesita clave"
Write-Host "  4) LM Studio   - en tu PC, requiere LM Studio abierto"
Write-Host ""

$opcion = ""
while ($opcion -notin @("1", "2", "3", "4")) {
    $opcion = (Read-Host "Elige [1-4]").Trim()
}

$proveedor = @{ "1" = "openrouter"; "2" = "ollama"; "3" = "openai"; "4" = "lmstudio" }[$opcion]
$modelo_sugerido = @{
    "1" = "mistralai/mistral-nemo"
    "2" = "llama3.1:8b"
    "3" = "gpt-4o-mini"
    "4" = "local-model"
}[$opcion]
$necesita_clave = $proveedor -in @("openrouter", "openai")

$clave = ""
if ($necesita_clave) {
    $donde = if ($proveedor -eq "openrouter") { "https://openrouter.ai/keys" } else { "https://platform.openai.com/api-keys" }
    Write-Host ""
    Write-Host "Necesitas una clave de API. Sacala en: $donde" -ForegroundColor Yellow
    Write-Host "(no se muestra al escribirla, y se guarda solo en tu .env local)"
    # La entrada oculta solo funciona con una consola de verdad: con la
    # entrada redirigida, Read-Host -AsSecureString termina el proceso sin
    # lanzar ningun error, asi que no basta con un try/catch. Se comprueba
    # antes de llamarlo.
    $consola_real = $false
    try { $consola_real = -not [Console]::IsInputRedirected } catch { $consola_real = $false }

    # Numero acotado de intentos: al llegar al final de la entrada Read-Host
    # devuelve vacio indefinidamente y un bucle sin limite no terminaria.
    for ($intento = 1; $intento -le 3 -and -not $clave; $intento++) {
        if ($consola_real) {
            $segura = Read-Host "Pega aqui tu clave" -AsSecureString
            if ($segura -and $segura.Length -gt 0) {
                $clave = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
                    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($segura)).Trim()
            }
        } else {
            $clave = (Read-Host "Pega aqui tu clave").Trim()
        }
        if (-not $clave -and $intento -lt 3) {
            Write-Host "  La clave no puede estar vacia." -ForegroundColor Red
        }
    }
    if (-not $clave) {
        Write-Host ""
        Write-Host "No se ha podido leer la clave." -ForegroundColor Red
        Write-Host "Escribela a mano en el fichero .env, en la linea MANTELLA_API_KEY="
        exit 1
    }
}

Write-Host ""
$modelo = (Read-Host "Modelo [$modelo_sugerido]").Trim()
if (-not $modelo) { $modelo = $modelo_sugerido }

Write-Host ""
$idioma = (Read-Host "Que los PNJ respondan en espanol? (S/n)").Trim()
$prefijo = ""
if ($idioma -notmatch '^[nN]') {
    $prefijo = "Responde siempre en espanol, en una o dos frases cortas, sin describir acciones."
}

# --- Escribir el .env ------------------------------------------------------
$lineas = @(
    "# Generado por scripts\configurar.ps1",
    "MANTELLA_PROVIDER=$proveedor",
    "MANTELLA_MODEL=$modelo",
    "MANTELLA_API_KEY=$clave",
    "MANTELLA_HOST=127.0.0.1",
    "MANTELLA_PORT=8000",
    "MANTELLA_TEMPERATURE=0.8",
    "MANTELLA_MAX_TOKENS=250",
    "MANTELLA_SANITIZE=true",
    "MANTELLA_STRIP_ACTIONS=true",
    "MANTELLA_MAX_SENTENCES=2",
    "MANTELLA_TIMEOUT=60",
    "MANTELLA_MAX_RETRIES=2",
    "MANTELLA_LOG_LEVEL=INFO"
)
if ($prefijo) { $lineas += "MANTELLA_SYSTEM_PREFIX=$prefijo" }

Set-Content -Path $env_destino -Value $lineas -Encoding UTF8

# Comprobacion explicita: si algo corto el script antes de tiempo, mas vale
# fallar aqui que anunciar una instalacion correcta que no lo es.
# -Force es necesario: .env es un fichero oculto y Get-Item lo ignora sin el.
$escrito = Get-Item $env_destino -Force -ErrorAction SilentlyContinue
if (-not $escrito -or $escrito.Length -eq 0) {
    Write-Host "No se pudo escribir $env_destino" -ForegroundColor Red
    exit 1
}
Write-Host ""
Write-Host "Guardado en $env_destino" -ForegroundColor Green

# --- Comprobar que el proveedor responde -----------------------------------
Write-Host ""
Write-Host "Comprobando la conexion con $proveedor..." -ForegroundColor Cyan

$python = Join-Path $raiz ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = Join-Path $raiz ".venv/bin/python" }

if (Test-Path $python) {
    $prueba = Join-Path $PSScriptRoot "probar-proveedor.py"
    & $python $prueba
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "El .env se ha guardado, pero el proveedor no ha respondido." -ForegroundColor Yellow
        Write-Host "Corrigelo cuando quieras con:"
        Write-Host "  powershell -ExecutionPolicy Bypass -File scripts\configurar.ps1 -Forzar"
        # Codigo 3: configuracion escrita pero sin verificar. Quien llama puede
        # seguir adelante (el acceso directo sigue teniendo sentido); solo el 1
        # significa que no hay nada utilizable.
        exit 3
    }
} else {
    Write-Host "  (sin entorno virtual todavia; se omite la prueba)" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Configuracion terminada." -ForegroundColor Green
