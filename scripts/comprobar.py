#!/usr/bin/env python3
"""Comprueba que la instalacion de Mantella esta completa.

Se ejecuta en el PC donde esta Skyrim y solo usa la biblioteca estandar:

    python scripts/comprobar.py --skyrim "C:/Program Files (x86)/Steam/steamapps/common/Skyrim Special Edition"

Cada comprobacion se marca [OK], [AVISO] o [FALLO]. El codigo de salida es
1 si hay algun [FALLO].
"""

from __future__ import annotations

import argparse
import configparser
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

OK, AVISO, FALLO = "OK", "AVISO", "FALLO"

_ESTADO = {OK: 0, AVISO: 0, FALLO: 0}


def marca(estado: str, titulo: str, detalle: str = "") -> None:
    _ESTADO[estado] += 1
    linea = f"[{estado:^5}] {titulo}"
    print(linea if not detalle else f"{linea}\n         {detalle}")


def comprobar_python() -> None:
    v = sys.version_info
    if v >= (3, 10):
        marca(OK, f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        marca(FALLO, f"Python {v.major}.{v.minor}", "El gateway necesita Python 3.10 o superior.")


def comprobar_skyrim(carpeta: Path | None) -> Path | None:
    if carpeta is None:
        marca(AVISO, "Carpeta de Skyrim no indicada", "Pasa --skyrim para comprobar el juego y SKSE.")
        return None
    if not carpeta.is_dir():
        marca(FALLO, "Carpeta de Skyrim no encontrada", str(carpeta))
        return None

    ejecutables = [n for n in ("SkyrimSE.exe", "SkyrimVR.exe", "TESV.exe") if (carpeta / n).is_file()]
    if ejecutables:
        marca(OK, f"Skyrim encontrado ({', '.join(ejecutables)})", str(carpeta))
    else:
        marca(FALLO, "En esa carpeta no hay ningun ejecutable de Skyrim", str(carpeta))
        return None

    cargadores = sorted(p.name for p in carpeta.glob("skse*_loader.exe"))
    if cargadores:
        marca(OK, f"SKSE instalado ({', '.join(cargadores)})")
    else:
        marca(FALLO, "No se encuentra skse64_loader.exe / sksevr_loader.exe", "Mantella no arranca sin SKSE.")

    return carpeta


def comprobar_mods(carpeta_mods: Path | None) -> None:
    """Busca los mods que Mantella necesita en la carpeta de Data o de MO2."""
    if carpeta_mods is None:
        marca(AVISO, "Carpeta de mods no indicada", "Pasa --mods para comprobar los requisitos.")
        return
    if not carpeta_mods.is_dir():
        marca(FALLO, "Carpeta de mods no encontrada", str(carpeta_mods))
        return

    nombres = {p.name.lower() for p in carpeta_mods.rglob("*") if p.is_file()}

    requisitos = {
        "Mantella": ("mantella.esp",),
        "PapyrusUtil": ("papyrusutil.dll", "papyrusutil_se_1.dll", "papyrusutil_ae.dll"),
        "Address Library / .NET Script Framework": ("versionlibsse.bin", "nativefunctions.dll"),
        "SkyUI (recomendado)": ("skyui_se.esp", "skyui.esp"),
    }
    for etiqueta, ficheros in requisitos.items():
        encontrado = any(
            any(n == f or n.startswith(f.rsplit(".", 1)[0]) for n in nombres) for f in ficheros
        )
        if encontrado:
            marca(OK, f"{etiqueta} presente")
        elif "recomendado" in etiqueta:
            marca(AVISO, f"{etiqueta} no encontrado")
        else:
            marca(FALLO, f"{etiqueta} no encontrado", f"Se buscaba: {', '.join(ficheros)}")


def comprobar_config_ini(ruta: Path | None, url_gateway: str) -> None:
    if ruta is None:
        marca(AVISO, "config.ini de Mantella no indicado", "Pasa --config para revisarlo.")
        return
    if not ruta.is_file():
        marca(FALLO, "config.ini de Mantella no encontrado", str(ruta))
        return

    parser = configparser.ConfigParser(strict=False, interpolation=None)
    try:
        parser.read(ruta, encoding="utf-8")
    except configparser.Error as exc:
        marca(FALLO, "config.ini ilegible", str(exc))
        return

    valores = {}
    for seccion in parser.sections():
        for clave, valor in parser.items(seccion):
            valores.setdefault(clave.strip().lower(), valor.strip())

    llm_api = valores.get("llm_api", "")
    if not llm_api:
        marca(FALLO, "config.ini no define llm_api", f"Debe apuntar a {url_gateway}/v1")
    elif url_gateway.rstrip("/") in llm_api or "localhost" in llm_api or "127.0.0.1" in llm_api:
        marca(OK, f"llm_api apunta al gateway ({llm_api})")
    else:
        marca(AVISO, f"llm_api apunta a otro sitio ({llm_api})", f"Se esperaba {url_gateway}/v1")

    if valores.get("model"):
        marca(OK, f"model = {valores['model']}")
    else:
        marca(AVISO, "config.ini no define 'model'", "El gateway usara MANTELLA_MODEL.")

    for clave in ("skyrim_folder", "skyrim_mod_folder"):
        valor = valores.get(clave)
        if not valor:
            marca(AVISO, f"config.ini no define {clave}")
        elif Path(valor).is_dir():
            marca(OK, f"{clave} = {valor}")
        else:
            marca(FALLO, f"{clave} apunta a una carpeta inexistente", valor)


def comprobar_gateway(url: str) -> None:
    destino = f"{url.rstrip('/')}/health"
    try:
        with urllib.request.urlopen(destino, timeout=5) as respuesta:
            datos = json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        marca(FALLO, "El gateway no responde", f"{destino} -> {exc.reason}. Arrancalo con scripts/arrancar.")
        return
    except (ValueError, OSError) as exc:
        marca(FALLO, "Respuesta invalida del gateway", f"{destino} -> {exc}")
        return

    marca(OK, f"Gateway activo en {url}", f"proveedor={datos.get('provider')} modelo={datos.get('model')}")
    if datos.get("provider") in {"openrouter", "openai"} and not datos.get("api_key_configurada"):
        marca(FALLO, "El proveedor necesita clave y el gateway no tiene ninguna", "Revisa MANTELLA_API_KEY en .env")


def comprobar_tts(xvasynth: Path | None, xtts: Path | None) -> None:
    if xvasynth is None and xtts is None:
        marca(AVISO, "No se indico motor de voz", "Pasa --xvasynth o --xtts si quieres comprobarlo.")
        return
    for etiqueta, carpeta, marcador in (
        ("xVASynth", xvasynth, "resources"),
        ("XTTS", xtts, ""),
    ):
        if carpeta is None:
            continue
        if carpeta.is_dir() and (not marcador or (carpeta / marcador).exists()):
            marca(OK, f"{etiqueta} encontrado", str(carpeta))
        else:
            marca(FALLO, f"{etiqueta} no encontrado", str(carpeta))


def main() -> int:
    p = argparse.ArgumentParser(description="Diagnostico de la instalacion de Mantella")
    p.add_argument("--skyrim", type=Path, help="Carpeta de instalacion de Skyrim")
    p.add_argument("--mods", type=Path, help="Carpeta Data del juego o de mods de MO2/Vortex")
    p.add_argument("--config", type=Path, help="Ruta al config.ini de Mantella")
    p.add_argument("--gateway", default=os.environ.get("MANTELLA_GATEWAY_URL", "http://localhost:8000"))
    p.add_argument("--xvasynth", type=Path, help="Carpeta de xVASynth")
    p.add_argument("--xtts", type=Path, help="Carpeta del servidor XTTS")
    args = p.parse_args()

    print("Comprobando la instalacion de Mantella\n" + "=" * 44)
    comprobar_python()
    skyrim = comprobar_skyrim(args.skyrim)
    mods = args.mods or (skyrim / "Data" if skyrim else None)
    comprobar_mods(mods)
    comprobar_config_ini(args.config, args.gateway)
    comprobar_tts(args.xvasynth, args.xtts)
    comprobar_gateway(args.gateway)

    print("=" * 44)
    print(f"{_ESTADO[OK]} correctas, {_ESTADO[AVISO]} avisos, {_ESTADO[FALLO]} fallos")
    if _ESTADO[FALLO]:
        print("\nHay fallos que impediran que Mantella funcione. Mira docs/SOLUCION-PROBLEMAS.md")
        return 1
    print("\nTodo listo. Arranca Skyrim con SKSE y usa el hechizo Mantella.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
