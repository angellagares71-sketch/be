#!/usr/bin/env python3
"""Genera Diagnostico.bat: el diagnostico entero en un solo fichero.

Descomprimir un ZIP es el paso donde mas gente se queda. Este .bat lleva
comprobar.py dentro: se descarga uno y se hace doble clic, sin extraer nada.
El .bat se ejecuta como tal hasta su `exit /b`; el resto del fichero es el
script de Python, que PowerShell recorta y guarda en %TEMP% para lanzarlo.

    python scripts/generar-diagnostico-unico.py
"""

from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "Diagnostico.bat"
FUENTE = RAIZ / "scripts" / "comprobar.py"

# En el .bat la marca va partida ('#___'+'PYTHON___') para que aparezca una
# sola vez de forma literal y IndexOf no encuentre la del propio comando.
MARCA = "#___PYTHON___"

CABECERA = r'''@echo off
chcp 65001 >nul
title Diagnostico Skyrim IA
setlocal

echo ============================================================
echo   Diagnostico de la instalacion de Skyrim con IA
echo ============================================================
echo.

set "PY="
py -3 --version >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if defined PY goto :tengo_python
python --version >nul 2>&1
if not errorlevel 1 set "PY=python"
if defined PY goto :tengo_python
goto :sin_python

:tengo_python
set "SCRIPT=%TEMP%\mantella_diagnostico.py"
set "SALIDA=%~dp0resultado-diagnostico.txt"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$m='#___'+'PYTHON___'; $c=[IO.File]::ReadAllText('%~f0'); $i=$c.IndexOf($m); if($i -lt 0){exit 1}; [IO.File]::WriteAllText($env:TEMP+'\mantella_diagnostico.py', $c.Substring($i+$m.Length))"
if errorlevel 1 goto :fallo_extraccion
if not exist "%SCRIPT%" goto :fallo_extraccion

echo Buscando Skyrim y Mantella en el equipo...
echo Puede tardar un minuto. No cierres esta ventana.
echo.

%PY% "%SCRIPT%" > "%SALIDA%" 2>&1
type "%SALIDA%"

echo.
echo ------------------------------------------------------------
echo Este resultado se ha guardado tambien en:
echo   %SALIDA%
echo ------------------------------------------------------------
echo.
pause
exit /b

:fallo_extraccion
echo No se ha podido preparar el diagnostico.
echo Vuelve a descargar el fichero, puede haberse cortado la descarga.
echo.
pause
exit /b 1

:sin_python
echo No se encuentra Python en este equipo.
echo.
echo Instalalo desde https://www.python.org/downloads/
echo IMPORTANTE: al instalarlo, marca la casilla "Add python.exe to PATH".
echo Despues vuelve a hacer doble clic en este fichero.
echo.
pause
exit /b 1

'''


def construir(fuente: Path | None = None) -> bytes:
    script = (fuente or FUENTE).read_text(encoding="utf-8")
    if MARCA in script:
        raise SystemExit("La marca choca con el contenido de comprobar.py")
    return (CABECERA + MARCA + "\n" + script).replace("\n", "\r\n").encode("utf-8")


def main() -> int:
    contenido = construir()
    DESTINO.write_bytes(contenido)
    print(f"Generado {DESTINO.name} ({len(contenido)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
