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
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Iterable, Sequence
from pathlib import Path

OK, AVISO, FALLO = "OK", "AVISO", "FALLO"

_ESTADO = {OK: 0, AVISO: 0, FALLO: 0}


def marca(estado: str, titulo: str, detalle: str = "") -> None:
    _ESTADO[estado] += 1
    linea = f"[{estado:^5}] {titulo}"
    print(linea if not detalle else f"{linea}\n         {detalle}")


# --------------------------------------------------------------------------
# Localizacion automatica
#
# Mantella ha cambiado de sitio entre versiones: unas guardan el config.ini
# junto al ejecutable (C:\Mantella\MantellaSoftware) y otras en
# Documentos\My Games\Mantella. Ademas OneDrive suele redirigir "Documentos".
# En vez de obligar a escribir la ruta a mano, la buscamos.
# --------------------------------------------------------------------------

# Carpetas que no vale la pena recorrer: ni contienen mods ni juegos.
_SALTAR = {
    "windows", "$recycle.bin", "system volume information", "appdata",
    "node_modules", "recovery", "perflogs", "msocache", "temp", "tmp",
}

_EJECUTABLES_SKYRIM = ("SkyrimSE.exe", "SkyrimVR.exe", "TESV.exe")
_CARPETAS_STEAM = ("Skyrim Special Edition", "Skyrim VR", "Skyrim", "Skyrim Anniversary Edition")


def _unico(rutas: Iterable[Path]) -> list[Path]:
    """Quita duplicados conservando el orden."""
    vistas: dict[str, Path] = {}
    for ruta in rutas:
        try:
            clave = str(ruta.resolve()).lower()
        except OSError:
            clave = str(ruta).lower()
        vistas.setdefault(clave, ruta)
    return list(vistas.values())


def carpetas_documentos(home: Path | None = None) -> list[Path]:
    """Documentos del usuario, incluidas las versiones redirigidas a OneDrive."""
    home = home or Path.home()
    posibles = [home / "Documents", home / "Documentos"]
    try:
        posibles += [
            sub / nombre
            for sub in sorted(home.glob("OneDrive*"))
            for nombre in ("Documents", "Documentos")
        ]
    except OSError:
        pass
    return [p for p in _unico(posibles) if p.is_dir()]


def raices_busqueda() -> list[Path]:
    """Unidades donde buscar: las letras de Windows, o el home fuera de Windows."""
    if os.name == "nt":
        return [Path(f"{letra}:\\") for letra in "CDEFGHIJKLMNOPQRSTUVWXYZ" if Path(f"{letra}:\\").is_dir()]
    return [Path.home()]


def _carpetas_que_contienen(raiz: Path, fragmento: str, profundidad: int = 4) -> list[Path]:
    """Carpetas cuyo nombre contiene `fragmento`, sin bajar mas de `profundidad`.

    El limite de profundidad es lo que mantiene la busqueda en segundos en vez
    de minutos: nadie instala un juego a diez niveles de la raiz.
    """
    encontradas: list[Path] = []

    def andar(carpeta: Path, nivel: int) -> None:
        if nivel > profundidad:
            return
        try:
            entradas = list(os.scandir(carpeta))
        except OSError:
            return
        for entrada in entradas:
            try:
                if not entrada.is_dir(follow_symlinks=False):
                    continue
            except OSError:
                continue
            nombre = entrada.name.lower()
            if nombre in _SALTAR or nombre.startswith("."):
                continue
            if fragmento in nombre:
                encontradas.append(Path(entrada.path))
            andar(Path(entrada.path), nivel + 1)

    andar(raiz, 0)
    return encontradas


def buscar_config_mantella(
    raices: Sequence[Path] | None = None,
    documentos: Sequence[Path] | None = None,
) -> list[Path]:
    """Devuelve los config.ini de Mantella que encuentre, del mas probable al menos."""
    candidatos: list[Path] = []

    # 1. Documentos\My Games\Mantella: donde lo dejan las versiones recientes.
    docs = carpetas_documentos() if documentos is None else list(documentos)
    for carpeta in docs:
        candidatos.append(carpeta / "My Games" / "Mantella" / "config.ini")

    # 2. Cualquier carpeta con "mantella" en el nombre, y un nivel por debajo.
    for raiz in (raices_busqueda() if raices is None else list(raices)):
        for carpeta in _carpetas_que_contienen(raiz, "mantella"):
            candidatos.append(carpeta / "config.ini")
            try:
                candidatos += sorted(carpeta.glob("*/config.ini"))
            except OSError:
                pass

    return [c for c in _unico(candidatos) if c.is_file()]


def _bibliotecas_steam(raices: Sequence[Path]) -> list[Path]:
    """Carpetas de biblioteca de Steam, leidas de libraryfolders.vdf."""
    bibliotecas: list[Path] = []
    for raiz in raices:
        for sub in ("Program Files (x86)/Steam", "Program Files/Steam", "Steam", "SteamLibrary"):
            vdf = raiz / sub / "steamapps" / "libraryfolders.vdf"
            if not vdf.is_file():
                continue
            bibliotecas.append(vdf.parent.parent)
            try:
                texto = vdf.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            # El vdf lista cada biblioteca como:  "path"  "D:\\SteamLibrary"
            for encontrado in re.finditer(r'"path"\s*"([^"]+)"', texto):
                bibliotecas.append(Path(encontrado.group(1).replace("\\\\", "\\")))
    return _unico(bibliotecas)


def buscar_skyrim(raices: Sequence[Path] | None = None) -> list[Path]:
    """Devuelve las instalaciones de Skyrim que encuentre."""
    raices = raices_busqueda() if raices is None else list(raices)
    candidatos: list[Path] = []

    # 1. Por Steam, que es como lo tiene casi todo el mundo.
    for biblioteca in _bibliotecas_steam(raices):
        for nombre in _CARPETAS_STEAM:
            candidatos.append(biblioteca / "steamapps" / "common" / nombre)

    # 2. A mano, por si esta fuera de Steam o en una copia.
    for raiz in raices:
        candidatos += _carpetas_que_contienen(raiz, "skyrim")

    return [
        c for c in _unico(candidatos)
        if c.is_dir() and any((c / exe).is_file() for exe in _EJECUTABLES_SKYRIM)
    ]


def comprobar_python() -> None:
    v = sys.version_info
    if v >= (3, 10):
        marca(OK, f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        marca(FALLO, f"Python {v.major}.{v.minor}", "El gateway necesita Python 3.10 o superior.")


def comprobar_skyrim(carpeta: Path | None) -> Path | None:
    if carpeta is None:
        marca(AVISO, "Skyrim no localizado", "No esta en las rutas habituales. Indicalo con --skyrim.")
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
        marca(
            AVISO,
            "config.ini de Mantella no localizado",
            "No esta en las rutas habituales. Indicalo con --config, o ejecuta: comprobar.py --buscar",
        )
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


def nota(texto: str) -> None:
    """Linea informativa, sin contar como comprobacion."""
    print(f"         {texto}")


def modo_buscar() -> int:
    """Solo busca Skyrim y el config.ini, y enseña lo que encuentre."""
    print("Buscando Skyrim y Mantella en este equipo (puede tardar un poco)\n" + "=" * 44)

    juegos = buscar_skyrim()
    if juegos:
        print("Skyrim encontrado en:")
        for ruta in juegos:
            print(f"  {ruta}")
    else:
        print("No se ha encontrado ninguna instalacion de Skyrim.")

    print()
    configs = buscar_config_mantella()
    if configs:
        print("config.ini de Mantella encontrado en:")
        for ruta in configs:
            print(f"  {ruta}")
    else:
        print("No se ha encontrado ningun config.ini de Mantella.")
        print("Suele significar que falta el paquete 'Mantella Software' de Nexus,")
        print("o que aun no se ha arrancado una vez para que lo genere.")

    print("=" * 44)
    if juegos and configs:
        print("Ya puedes lanzar el diagnostico completo:\n")
        print(f'  python scripts/comprobar.py --skyrim "{juegos[0]}" --config "{configs[0]}"')
        return 0
    return 1


def main() -> int:
    p = argparse.ArgumentParser(description="Diagnostico de la instalacion de Mantella")
    p.add_argument("--skyrim", type=Path, help="Carpeta de instalacion de Skyrim")
    p.add_argument("--mods", type=Path, help="Carpeta Data del juego o de mods de MO2/Vortex")
    p.add_argument("--config", type=Path, help="Ruta al config.ini de Mantella")
    p.add_argument("--gateway", default=os.environ.get("MANTELLA_GATEWAY_URL", "http://localhost:8000"))
    p.add_argument("--xvasynth", type=Path, help="Carpeta de xVASynth")
    p.add_argument("--xtts", type=Path, help="Carpeta del servidor XTTS")
    p.add_argument(
        "--buscar",
        action="store_true",
        help="Solo busca Skyrim y el config.ini de Mantella, y enseña las rutas",
    )
    args = p.parse_args()

    if args.buscar:
        return modo_buscar()

    print("Comprobando la instalacion de Mantella\n" + "=" * 44)
    comprobar_python()

    ruta_skyrim = args.skyrim
    if ruta_skyrim is None:
        encontrados = buscar_skyrim()
        if encontrados:
            ruta_skyrim = encontrados[0]
            nota(f"(Skyrim localizado solo: {ruta_skyrim})")
    skyrim = comprobar_skyrim(ruta_skyrim)

    mods = args.mods or (skyrim / "Data" if skyrim else None)
    comprobar_mods(mods)

    ruta_config = args.config
    if ruta_config is None:
        encontrados = buscar_config_mantella()
        if encontrados:
            ruta_config = encontrados[0]
            nota(f"(config.ini localizado solo: {ruta_config})")
            if len(encontrados) > 1:
                nota(f"(hay {len(encontrados)} config.ini; usa --buscar para verlos todos)")
    comprobar_config_ini(ruta_config, args.gateway)
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
