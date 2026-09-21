@echo off
rem ===========================================================================
rem  Skyrim IA - deja la IA funcionando en tu PC, de un solo doble clic.
rem
rem  Sin cuenta, sin clave y sin pagar. Instala Ollama, se descarga el
rem  modelo y configura el gateway. Tu no tienes que escribir nada.
rem
rem  La primera vez tarda: son unos 5 GB de descarga.
rem ===========================================================================
setlocal
title Instalar la IA en mi PC
cd /d "%~dp0"

set "PS=%WINDIR%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" set "PS=powershell.exe"

rem --- 1. Dependencias del gateway ------------------------------------------
echo.
echo   Preparando el gateway...
echo.
"%PS%" -ExecutionPolicy Bypass -File "scripts\instalar.ps1"
if errorlevel 1 goto :error

rem --- 2. Ollama, modelo y .env ---------------------------------------------
"%PS%" -ExecutionPolicy Bypass -File "scripts\instalar-ollama.ps1"
if errorlevel 1 goto :error

rem --- 3. Acceso directo del Escritorio -------------------------------------
echo.
echo   Creando el acceso directo del Escritorio...
"%PS%" -ExecutionPolicy Bypass -File "scripts\crear-acceso-directo.ps1" -Forzar
if errorlevel 1 goto :error

echo.
echo   ============================================
echo      Todo listo.
echo.
echo      Para jugar, abre el acceso directo
echo      "Skyrim IA" del Escritorio.
echo   ============================================
echo.
pause
exit /b 0

:error
echo.
echo   ============================================
echo      Se ha detenido por un error.
echo      El mensaje de arriba dice cual, y que hacer.
echo   ============================================
echo.
pause
exit /b 1
