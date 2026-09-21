@echo off
rem ===========================================================================
rem  Skyrim IA - crea el acceso directo del Escritorio, de un solo doble clic.
rem
rem  Util si ya instalaste Skyrim IA pero el acceso directo no esta en el
rem  Escritorio, o si lo borraste sin querer. No reinstala nada.
rem
rem  Basta con hacer doble clic en este fichero.
rem ===========================================================================
setlocal
title Crear el acceso directo de Skyrim IA
cd /d "%~dp0"

echo.
echo   ============================================
echo      Skyrim IA - acceso directo del Escritorio
echo   ============================================
echo.

rem --- 1. Buscar PowerShell -------------------------------------------------
set "PS=%WINDIR%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" set "PS=powershell.exe"

rem --- 2. Crear el acceso directo -------------------------------------------
rem -Forzar sobrescribe el que hubiera: apunta al mismo lanzador, asi que
rem volver a crearlo no rompe nada.
"%PS%" -ExecutionPolicy Bypass -File "scripts\crear-acceso-directo.ps1" -Forzar
if errorlevel 1 goto :error

rem --- 3. Avisar si todavia no se ha instalado nada --------------------------
if not exist ".venv" (
    echo.
    echo   [!] Aviso: aun no hay dependencias instaladas.
    echo       El acceso directo ya esta en el Escritorio, pero antes de
    echo       jugar haz doble clic en INSTALAR-SKYRIM-IA.cmd.
)

echo.
echo   Ya puedes arrancar Skyrim IA desde el Escritorio.
echo.
pause
exit /b 0

:error
echo.
echo   ============================================
echo      No se ha podido crear el acceso directo.
echo      El mensaje de arriba dice por que.
echo   ============================================
echo.
pause
exit /b 1
