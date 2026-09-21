@echo off
rem ===========================================================================
rem  Skyrim IA - revisa por que el microfono no funciona, de un solo doble clic.
rem
rem  No cambia nada del sistema: mira el microfono, los permisos de Windows y
rem  el config.ini de Mantella, y te dice que arreglar.
rem
rem  Basta con hacer doble clic en este fichero.
rem ===========================================================================
setlocal
title Comprobar el microfono de Skyrim IA
cd /d "%~dp0"

set "PS=%WINDIR%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" set "PS=powershell.exe"

rem -AbrirAjustes abre las paginas de Configuracion que hagan falta.
"%PS%" -ExecutionPolicy Bypass -File "scripts\comprobar-microfono.ps1" -AbrirAjustes

echo.
pause
