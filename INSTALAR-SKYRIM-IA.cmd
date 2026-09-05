@echo off
rem ===========================================================================
rem  Skyrim IA - instalacion completa de un solo doble clic.
rem
rem  Hace todo lo necesario: comprueba Python, instala las dependencias,
rem  pregunta por tu proveedor y tu clave, prueba la conexion, crea el acceso
rem  directo del Escritorio y arranca el gateway.
rem
rem  Basta con hacer doble clic en este fichero.
rem ===========================================================================
setlocal
title Instalar Skyrim IA
cd /d "%~dp0"

echo.
echo   ============================================
echo      Skyrim IA - instalacion
echo   ============================================
echo.

rem --- 1. Buscar PowerShell -------------------------------------------------
set "PS=%WINDIR%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" set "PS=powershell.exe"

rem --- 2. Comprobar que hay Python ------------------------------------------
where python >nul 2>&1
if errorlevel 1 (
    echo   [!] No se encuentra Python.
    echo.
    echo   Instalalo desde https://www.python.org/downloads/
    echo   IMPORTANTE: marca la casilla "Add python.exe to PATH".
    echo.
    echo   Cuando lo tengas, vuelve a hacer doble clic aqui.
    echo.
    pause
    exit /b 1
)

rem --- 3. Instalar dependencias ---------------------------------------------
echo   [1/4] Instalando dependencias...
echo.
"%PS%" -ExecutionPolicy Bypass -File "scripts\instalar.ps1"
if errorlevel 1 goto :error

rem --- 4. Configurar proveedor y clave --------------------------------------
echo.
echo   [2/4] Configuracion...
"%PS%" -ExecutionPolicy Bypass -File "scripts\configurar.ps1"
rem Codigo 3 = el .env se guardo pero el proveedor no respondio. No es fatal:
rem se avisa al final y la instalacion continua.
set "AVISO="
if errorlevel 4 goto :error
if errorlevel 3 set "AVISO=1"
if not defined AVISO if errorlevel 1 goto :error

rem --- 5. Acceso directo en el Escritorio -----------------------------------
echo.
echo   [3/4] Creando el acceso directo del Escritorio...
"%PS%" -ExecutionPolicy Bypass -File "scripts\crear-acceso-directo.ps1" -Forzar
if errorlevel 1 goto :error

rem --- 6. Recordar lo que falta y arrancar ----------------------------------
echo.
echo   [4/4] Todo listo.
echo.
echo   ============================================
echo      Falta un paso dentro de Mantella:
echo.
echo      Abre el config.ini de Mantella y pon
echo         llm_api = http://localhost:8000/v1
echo         model   = mantella
echo   ============================================
echo.
echo   A partir de ahora, para jugar solo tienes que abrir
echo   el acceso directo "Skyrim IA" del Escritorio.
echo.
if defined AVISO (
    echo   [!] Aviso: el proveedor no respondio a la prueba de conexion.
    echo       Revisa la clave, o arranca Ollama/LM Studio, y repite con:
    echo         powershell -ExecutionPolicy Bypass -File scripts\configurar.ps1 -Forzar
    echo.
)

choice /c SN /n /m "   Arrancar el gateway ahora? (S/N): "
if errorlevel 2 goto :fin

echo.
"%PS%" -ExecutionPolicy Bypass -NoExit -File "scripts\arrancar.ps1"
goto :fin

:error
echo.
echo   ============================================
echo      La instalacion se ha detenido por un error.
echo      El mensaje de arriba dice cual.
echo   ============================================
echo.
pause
exit /b 1

:fin
echo.
pause
