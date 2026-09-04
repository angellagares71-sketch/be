#!/usr/bin/env python3
"""Arranca el gateway y, cuando responde, lanza Skyrim desde SKSE.

Es el "boton de jugar": una sola cosa que ejecutar en vez de tres ventanas en
el orden correcto. Solo usa la biblioteca estandar; el entorno virtual hace
falta para el gateway, no para este script.

    python scripts/jugar.py
    python scripts/jugar.py --skyrim "C:\\...\\Skyrim Special Edition"
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Del mas moderno al mas antiguo; Skyrim VR usa el suyo propio.
_LANZADORES_SKSE = ("skse64_loader.exe", "sksevr_loader.exe", "skse_loader.exe")


def _cargar_comprobar():
    """Reutiliza la localizacion automatica que ya vive en comprobar.py."""
    spec = importlib.util.spec_from_file_location("comprobar", RAIZ / "scripts" / "comprobar.py")
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["comprobar"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def python_del_entorno(raiz: Path | None = None) -> Path | None:
    """El interprete del entorno virtual, que es el que tiene las dependencias."""
    raiz = raiz or RAIZ
    for relativa in ("Scripts/python.exe", "bin/python"):
        candidato = raiz / ".venv" / relativa
        if candidato.is_file():
            return candidato
    return None


def buscar_lanzador_skse(carpeta: Path) -> Path | None:
    """El skse*_loader.exe de una instalacion de Skyrim."""
    for nombre in _LANZADORES_SKSE:
        candidato = carpeta / nombre
        if candidato.is_file():
            return candidato
    return None


def gateway_responde(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(f"{url.rstrip('/')}/health", timeout=timeout) as respuesta:
            return json.loads(respuesta.read().decode("utf-8")).get("status") == "ok"
    except (urllib.error.URLError, ValueError, OSError):
        return False


def esperar_gateway(url: str, segundos: int = 40) -> bool:
    for _ in range(segundos):
        if gateway_responde(url):
            return True
        time.sleep(1)
    return False


def arrancar_gateway(python: Path, url: str) -> bool:
    """Lanza el gateway en su propia ventana y espera a que conteste."""
    if gateway_responde(url):
        print("  El gateway ya estaba arrancado")
        return True

    print("  Arrancando el gateway...")
    opciones: dict = {}
    if os.name == "nt":
        # Ventana aparte, para que se vean los mensajes y se pueda cerrar sola.
        opciones["creationflags"] = subprocess.CREATE_NEW_CONSOLE

    entorno = dict(os.environ, MANTELLA_GATEWAY_ENV=str(RAIZ / ".env"))
    subprocess.Popen([str(python), "-m", "mantella_gateway"], cwd=str(RAIZ / "server"), env=entorno, **opciones)

    if esperar_gateway(url):
        print("  Gateway listo")
        return True
    print("  El gateway no responde. Mira su ventana para ver el error.")
    return False


def main() -> int:
    p = argparse.ArgumentParser(description="Arranca el gateway y Skyrim")
    p.add_argument("--skyrim", type=Path, help="Carpeta de Skyrim, si no se detecta sola")
    p.add_argument("--gateway", default=os.environ.get("MANTELLA_GATEWAY_URL", "http://localhost:8000"))
    p.add_argument("--solo-gateway", action="store_true", help="No lanzar el juego")
    args = p.parse_args()

    print("Preparando la partida\n" + "=" * 44)

    python = python_del_entorno()
    if python is None:
        print("No hay entorno virtual. Ejecuta antes el instalador:")
        print("  Windows:      scripts\\instalar.ps1")
        print("  Linux/macOS:  ./scripts/instalar.sh")
        return 1

    if not arrancar_gateway(python, args.gateway):
        return 1
    if args.solo_gateway:
        return 0

    carpeta = args.skyrim
    if carpeta is None:
        encontradas = _cargar_comprobar().buscar_skyrim()
        if not encontradas:
            print("\nNo encuentro Skyrim. Indicalo con --skyrim, o ejecuta:")
            print("  python scripts/comprobar.py --buscar")
            return 1
        carpeta = encontradas[0]
        print(f"  Skyrim localizado en {carpeta}")

    if not carpeta.is_dir():
        print(f"\nLa carpeta de Skyrim no existe: {carpeta}")
        return 1

    lanzador = buscar_lanzador_skse(carpeta)
    if lanzador is None:
        print(f"\nNo hay ningun {' / '.join(_LANZADORES_SKSE)} en {carpeta}.")
        print("Mantella necesita SKSE: instalalo desde https://skse.silverlock.org/")
        return 1

    print(f"  Arrancando Skyrim con {lanzador.name}")
    try:
        subprocess.Popen([str(lanzador)], cwd=str(carpeta))
    except OSError as exc:
        print(f"\nNo se pudo arrancar el juego: {exc}")
        return 1

    print("=" * 44)
    print("Listo. Acuerdate de arrancar tambien Mantella Software.")
    print("Dentro del juego: hechizo Mantella sobre un PNJ y a hablar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
