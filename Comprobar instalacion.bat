@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Comprobar la instalacion

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
echo Comprobando la instalacion...
echo Arranca antes el gateway, o la ultima comprobacion saldra en FALLO.
echo.
%PY% scripts\comprobar.py > "resultado-diagnostico.txt" 2>&1
type "resultado-diagnostico.txt"

echo.
echo ------------------------------------------------------------
echo Resultado guardado en:
echo   %CD%\resultado-diagnostico.txt
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
