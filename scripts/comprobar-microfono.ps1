<#
.SYNOPSIS
    Revisa por que Mantella no te oye por el microfono.

.DESCRIPTION
    Comprueba, en el PC donde juegas:
      1. Que Windows ve algun microfono y cual es.
      2. Que el permiso de microfono esta dado, incluido el de las
         aplicaciones de escritorio, que es el que necesita Mantella.
      3. Que ajustes de microfono tiene el config.ini de Mantella.

    Cada punto se marca [OK], [AVISO] o [FALLO]. No cambia nada del sistema:
    solo mira y te dice que arreglar.

.PARAMETER Config
    Ruta al config.ini de Mantella. Si no se indica, se busca en los sitios
    habituales.

.PARAMETER AbrirAjustes
    Abre ademas las paginas de Configuracion de Windows que hagan falta.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\comprobar-microfono.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\comprobar-microfono.ps1 -Config "C:\MantellaSoftware\config.ini"
#>
[CmdletBinding()]
param(
    [string]$Config,
    [switch]$AbrirAjustes
)

$ErrorActionPreference = "Continue"

$script:Fallos = 0
$script:Avisos = 0
$script:AbrirPrivacidad = $false
$script:AbrirSonido = $false

function Marca {
    param(
        [ValidateSet("OK", "AVISO", "FALLO")] [string]$Estado,
        [string]$Titulo,
        [string]$Detalle = ""
    )
    $color = switch ($Estado) {
        "OK"    { "Green" }
        "AVISO" { "Yellow" }
        "FALLO" { "Red" }
    }
    if ($Estado -eq "FALLO") { $script:Fallos++ }
    if ($Estado -eq "AVISO") { $script:Avisos++ }
    Write-Host ("[{0,-5}] " -f $Estado) -ForegroundColor $color -NoNewline
    Write-Host $Titulo
    if ($Detalle) { Write-Host "         $Detalle" -ForegroundColor DarkGray }
}

function Comprobar-Dispositivos {
    Write-Host ""
    Write-Host "-- Microfonos que ve Windows --" -ForegroundColor Cyan

    $micros = $null
    try {
        $micros = Get-PnpDevice -Class AudioEndpoint -ErrorAction Stop |
            Where-Object { $_.FriendlyName -match "Micr|Mic|Input|Entrada" }
    } catch {
        Marca AVISO "No se ha podido consultar la lista de dispositivos" $_.Exception.Message
        return
    }

    if (-not $micros) {
        Marca FALLO "Windows no ve ningun microfono" "Conectalo y, si es USB o jack, prueba otro puerto."
        $script:AbrirSonido = $true
        return
    }

    $activos = @($micros | Where-Object { $_.Status -eq "OK" })
    foreach ($m in $micros) {
        if ($m.Status -eq "OK") {
            Marca OK $m.FriendlyName
        } else {
            Marca AVISO "$($m.FriendlyName) (desactivado)" "Estado: $($m.Status)"
        }
    }

    if (-not $activos) {
        Marca FALLO "Ningun microfono esta activo" "Activalo en Configuracion > Sistema > Sonido."
        $script:AbrirSonido = $true
    } elseif ($activos.Count -gt 1) {
        Marca AVISO "Hay $($activos.Count) microfonos activos" "Mantella usa el que Windows tenga por defecto. Si te oye mal, deja solo el que quieres usar."
        $script:AbrirSonido = $true
    }
}

function Leer-Consentimiento {
    param([string]$Ruta)
    try {
        $v = Get-ItemProperty -Path $Ruta -Name "Value" -ErrorAction Stop
        return $v.Value
    } catch {
        return $null
    }
}

function Comprobar-Permisos {
    Write-Host ""
    Write-Host "-- Permiso de microfono en Windows --" -ForegroundColor Cyan

    $base = "HKCU:\Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"

    $general = Leer-Consentimiento $base
    if ($general -eq "Allow") {
        Marca OK "El microfono esta permitido para este usuario"
    } elseif ($general -eq "Deny") {
        Marca FALLO "El microfono esta BLOQUEADO para este usuario" "Configuracion > Privacidad > Microfono: ponlo en Activado."
        $script:AbrirPrivacidad = $true
    } else {
        Marca AVISO "No se ha podido leer el permiso general" "Revisalo a mano en Configuracion > Privacidad > Microfono."
        $script:AbrirPrivacidad = $true
    }

    # Mantella y Python no son apps de la Store: dependen de este permiso.
    $escritorio = Leer-Consentimiento "$base\NonPackaged"
    if ($escritorio -eq "Allow") {
        Marca OK "Las aplicaciones de escritorio pueden usar el microfono"
    } elseif ($escritorio -eq "Deny") {
        Marca FALLO "Las aplicaciones de escritorio NO pueden usar el microfono" "Este es el permiso que necesita Mantella. Activa 'Permitir que las aplicaciones de escritorio accedan al microfono'."
        $script:AbrirPrivacidad = $true
    } else {
        Marca AVISO "No se ha podido leer el permiso de las aplicaciones de escritorio" "Es el que necesita Mantella. Revisalo a mano."
        $script:AbrirPrivacidad = $true
    }
}

function Buscar-Config {
    if ($Config) {
        if (Test-Path $Config) { return $Config }
        Marca FALLO "No existe el config.ini indicado" $Config
        return $null
    }

    $candidatos = @(
        "C:\MantellaSoftware\config.ini",
        "D:\MantellaSoftware\config.ini"
    )
    # Join-Path falla si la variable no existe, asi que se comprueba antes.
    if ($env:USERPROFILE) {
        $candidatos += (Join-Path $env:USERPROFILE "Documents\My Games\Mantella\config.ini")
        $candidatos += (Join-Path $env:USERPROFILE "Desktop\MantellaSoftware\config.ini")
    }
    foreach ($c in $candidatos) {
        if ($c -and (Test-Path $c)) { return $c }
    }
    return $null
}

function Comprobar-Mantella {
    Write-Host ""
    Write-Host "-- Ajustes de microfono de Mantella --" -ForegroundColor Cyan

    $ruta = Buscar-Config
    if (-not $ruta) {
        # Si el usuario indico una ruta, Buscar-Config ya ha dicho que falla:
        # no hace falta repetirselo.
        if (-not $Config) {
            Marca AVISO "No se ha encontrado el config.ini de Mantella" "Vuelve a lanzarlo indicandolo: -Config `"C:\ruta\a\config.ini`""
        }
        return
    }
    Marca OK "config.ini encontrado" $ruta

    $lineas = Get-Content -Path $ruta -Encoding UTF8 -ErrorAction SilentlyContinue
    if (-not $lineas) {
        Marca AVISO "El config.ini esta vacio o no se ha podido leer" $ruta
        return
    }

    # Mantella ha cambiado los nombres de estas claves entre versiones, asi que
    # se muestra lo que haya en vez de dar por supuesta una clave concreta.
    $interesantes = $lineas | Where-Object {
        $_ -notmatch "^\s*[#;]" -and
        $_ -match "=" -and
        $_ -match "(micro|mic_|stt|whisper|audio_threshold|listen)"
    }

    if ($interesantes) {
        foreach ($l in $interesantes) {
            Write-Host "         $($l.Trim())" -ForegroundColor DarkGray
        }
        $apagado = $interesantes | Where-Object { $_ -match "(micro\w*)\s*=\s*(0|false|no)\s*$" }
        if ($apagado) {
            Marca FALLO "El microfono parece desactivado en el config.ini" "Pon esa clave a 1 (o True) y reinicia Mantella."
        } else {
            Marca OK "El microfono no aparece desactivado en el config.ini"
        }
    } else {
        Marca AVISO "En el config.ini no hay ninguna clave de microfono" "Tu version de Mantella puede llevar el microfono en su propia interfaz."
    }
}

function Prueba-Manual {
    Write-Host ""
    Write-Host "-- Prueba de voz (hazla tu, tarda 10 segundos) --" -ForegroundColor Cyan
    Write-Host "  Windows trae un medidor en vivo: si la barra se mueve al hablar," -ForegroundColor DarkGray
    Write-Host "  el microfono funciona y el problema esta en Mantella, no en el micro." -ForegroundColor DarkGray
    Write-Host "  Configuracion > Sistema > Sonido > Entrada > Probar el microfono." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "     Skyrim IA - diagnostico del microfono" -ForegroundColor Cyan
Write-Host "  ============================================" -ForegroundColor Cyan

Comprobar-Dispositivos
Comprobar-Permisos
Comprobar-Mantella
Prueba-Manual

Write-Host ""
Write-Host "-- Resumen --" -ForegroundColor Cyan
if ($script:Fallos -gt 0) {
    Write-Host "  $($script:Fallos) fallo(s) y $($script:Avisos) aviso(s). Empieza por los [FALLO]." -ForegroundColor Red
} elseif ($script:Avisos -gt 0) {
    Write-Host "  Sin fallos, $($script:Avisos) aviso(s). Mira los [AVISO] de arriba." -ForegroundColor Yellow
} else {
    Write-Host "  Todo correcto por este lado." -ForegroundColor Green
    Write-Host "  Si aun asi Mantella no te oye, el fallo esta dentro de Mantella:" -ForegroundColor DarkGray
    Write-Host "  mira su ventana mientras hablas, a ver que mensaje saca." -ForegroundColor DarkGray
}

if ($AbrirAjustes) {
    if ($script:AbrirPrivacidad) {
        Write-Host ""
        Write-Host "  Abriendo la privacidad del microfono..." -ForegroundColor Cyan
        Start-Process "ms-settings:privacy-microphone"
    }
    if ($script:AbrirSonido) {
        Write-Host ""
        Write-Host "  Abriendo los ajustes de sonido..." -ForegroundColor Cyan
        Start-Process "ms-settings:sound"
    }
}

if ($script:Fallos -gt 0) { exit 1 }
exit 0
