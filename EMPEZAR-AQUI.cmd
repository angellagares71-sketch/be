@echo off
rem ===========================================================================
rem  Skyrim IA - el unico fichero que hace falta bajarse.
rem
rem  Se descarga el proyecto entero, lo deja en una carpeta "Skyrim IA" en el
rem  Escritorio y lanza la instalacion. No hay que descomprimir nada a mano.
rem
rem  Basta con hacer doble clic en este fichero.
rem ===========================================================================
setlocal
title Skyrim IA
cd /d "%~dp0"

set "PS=%WINDIR%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS%" set "PS=powershell.exe"

echo.
echo   ============================================
echo      Skyrim IA
echo   ============================================
echo.
echo   Descargando el proyecto. Tarda unos segundos...
echo.

"%PS%" -ExecutionPolicy Bypass -NoProfile -Command ^
  "$ErrorActionPreference='Stop';" ^
  "try {" ^
  "  [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;" ^
  "  $zip=Join-Path $env:TEMP 'skyrim-ia.zip';" ^
  "  $url='https://github.com/angellagares71-sketch/be/archive/refs/heads/claude/optimistic-keller-mui31r.zip';" ^
  "  Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing;" ^
  "  $esc=[Environment]::GetFolderPath('Desktop');" ^
  "  if(-not $esc){ $esc=Join-Path $env:USERPROFILE 'Desktop' }" ^
  "  $tmp=Join-Path $env:TEMP 'skyrim-ia-tmp';" ^
  "  if(Test-Path $tmp){ Remove-Item $tmp -Recurse -Force }" ^
  "  Expand-Archive -Path $zip -DestinationPath $tmp -Force;" ^
  "  $origen=Get-ChildItem $tmp -Directory | Select-Object -First 1;" ^
  "  if(-not $origen){ throw 'El fichero descargado no trae ninguna carpeta dentro.' }" ^
  "  $destino=Join-Path $esc 'Skyrim IA';" ^
  "  if(Test-Path $destino){ Remove-Item $destino -Recurse -Force }" ^
  "  Move-Item $origen.FullName $destino;" ^
  "  Remove-Item $zip,$tmp -Recurse -Force -ErrorAction SilentlyContinue;" ^
  "  Write-Host ('  Listo: ' + $destino) -ForegroundColor Green;" ^
  "  Set-Content -Path (Join-Path $env:TEMP 'skyrim-ia-destino.txt') -Value $destino -Encoding ASCII;" ^
  "} catch {" ^
  "  Write-Host '';" ^
  "  Write-Host ('  [!] No se ha podido descargar: ' + $_.Exception.Message) -ForegroundColor Red;" ^
  "  exit 1;" ^
  "}"
if errorlevel 1 goto :error

rem PowerShell deja aqui la ruta final: el Escritorio no siempre esta donde
rem uno cree, sobre todo con OneDrive de por medio.
set "DESTINO="
for /f "usebackq delims=" %%d in ("%TEMP%\skyrim-ia-destino.txt") do set "DESTINO=%%d"
del "%TEMP%\skyrim-ia-destino.txt" >nul 2>&1
if not defined DESTINO goto :error
if not exist "%DESTINO%\INSTALAR-IA-EN-MI-PC.cmd" goto :error

echo.
echo   Tienes una carpeta "Skyrim IA" en el Escritorio.
echo   Arrancando la instalacion...
echo.
timeout /t 3 >nul

cd /d "%DESTINO%"
call "INSTALAR-IA-EN-MI-PC.cmd"
exit /b 0

:error
echo.
echo   ============================================
echo      No se ha podido preparar la instalacion.
echo.
echo      Comprueba que tienes internet y vuelve a
echo      hacer doble clic aqui.
echo.
echo      Si sigue fallando, bajate el proyecto a
echo      mano desde GitHub (boton Code, Download
echo      ZIP), extraelo, y haz doble clic dentro
echo      en INSTALAR-IA-EN-MI-PC.cmd
echo   ============================================
echo.
pause
exit /b 1
