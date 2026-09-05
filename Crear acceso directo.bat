@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Crear acceso directo

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

echo Creando el acceso directo "Skyrim IA" en el Escritorio...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\crear-acceso-directo.ps1" -Forzar
if errorlevel 1 goto :fallo
echo.
echo ------------------------------------------------------------
echo Listo. Ya tienes el icono "Skyrim IA" en el Escritorio.
echo ------------------------------------------------------------
echo.
pause
exit /b

:fallo
echo.
echo ------------------------------------------------------------
echo No se ha podido crear el acceso directo. El motivo esta arriba.
echo ------------------------------------------------------------
echo.
pause
exit /b 1
