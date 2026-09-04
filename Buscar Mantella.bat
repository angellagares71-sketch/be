@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Buscar Mantella

if exist "scripts\comprobar.py" goto :sitio_correcto
echo.
echo No encuentro los ficheros del programa en esta carpeta.
echo.
echo Casi siempre es por abrir el .bat dentro del ZIP, sin descomprimirlo.
echo Windows deja abrirlo, pero luego no funciona.
echo.
echo Solucion: cierra esta ventana, busca el ZIP que descargaste, haz clic
echo derecho encima, elige "Extraer todo", y abre el .bat desde la carpeta
echo nueva que aparezca.
echo.
pause
exit /b 1

:sitio_correcto

set "PY="
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if defined PY goto :tengo_python
py -3 --version >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if defined PY goto :tengo_python
python --version >nul 2>&1
if not errorlevel 1 set "PY=python"
if defined PY goto :tengo_python
goto :sin_python

:tengo_python
echo Buscando Skyrim y Mantella en este equipo...
echo Puede tardar un minuto. No cierres esta ventana.
echo.
%PY% scripts\comprobar.py --buscar > "resultado-busqueda.txt" 2>&1
type "resultado-busqueda.txt"

echo.
echo ------------------------------------------------------------
echo Resultado guardado en:
echo   %CD%\resultado-busqueda.txt
echo Abre ese fichero y copia lo que ponga si necesitas ensenarlo.
echo ------------------------------------------------------------
echo.
pause
exit /b

:sin_python
echo.
echo No se encuentra Python en este equipo.
echo.
echo Instalalo desde https://www.python.org/downloads/
echo IMPORTANTE: al instalarlo, marca la casilla "Add python.exe to PATH".
echo Despues vuelve a hacer doble clic en este fichero.
echo.
pause
exit /b 1
