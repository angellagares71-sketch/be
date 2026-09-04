"""Pruebas de la localizacion automatica de Skyrim y del config.ini.

`comprobar.py` vive en scripts/ y solo usa la biblioteca estandar, asi que se
carga por ruta en vez de importarse como paquete.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]


def _cargar():
    spec = importlib.util.spec_from_file_location("comprobar", RAIZ / "scripts" / "comprobar.py")
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["comprobar"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


comprobar = _cargar()


@pytest.fixture
def disco(tmp_path: Path) -> Path:
    """Una unidad simulada, vacia."""
    raiz = tmp_path / "C"
    raiz.mkdir()
    return raiz


def _crear(ruta: Path, contenido: str = "") -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


# --- config.ini -----------------------------------------------------------


def test_encuentra_config_en_my_games(tmp_path: Path):
    docs = tmp_path / "Documents"
    esperado = _crear(docs / "My Games" / "Mantella" / "config.ini", "[Language]\n")

    encontrados = comprobar.buscar_config_mantella(raices=[], documentos=[docs])

    assert encontrados == [esperado]


def test_encuentra_config_junto_al_ejecutable(disco: Path):
    esperado = _crear(disco / "Mantella" / "MantellaSoftware" / "config.ini", "[Language]\n")

    encontrados = comprobar.buscar_config_mantella(raices=[disco], documentos=[])

    assert esperado in encontrados


def test_encuentra_config_aunque_la_carpeta_se_llame_distinto(disco: Path):
    esperado = _crear(disco / "Juegos" / "Mantella-v0.13" / "config.ini")

    encontrados = comprobar.buscar_config_mantella(raices=[disco], documentos=[])

    assert esperado in encontrados


def test_my_games_tiene_prioridad_sobre_el_resto(tmp_path: Path, disco: Path):
    docs = tmp_path / "Documents"
    en_documentos = _crear(docs / "My Games" / "Mantella" / "config.ini")
    _crear(disco / "Mantella" / "config.ini")

    encontrados = comprobar.buscar_config_mantella(raices=[disco], documentos=[docs])

    assert encontrados[0] == en_documentos
    assert len(encontrados) == 2


def test_sin_mantella_no_devuelve_nada(disco: Path):
    _crear(disco / "Skyrim" / "config.ini")

    assert comprobar.buscar_config_mantella(raices=[disco], documentos=[]) == []


def test_no_devuelve_carpetas_sin_config(disco: Path):
    (disco / "Mantella").mkdir()

    assert comprobar.buscar_config_mantella(raices=[disco], documentos=[]) == []


def test_documentos_incluye_onedrive(tmp_path: Path):
    home = tmp_path / "home"
    (home / "Documents").mkdir(parents=True)
    (home / "OneDrive" / "Documents").mkdir(parents=True)

    carpetas = comprobar.carpetas_documentos(home=home)

    assert home / "Documents" in carpetas
    assert home / "OneDrive" / "Documents" in carpetas


# --- Skyrim ---------------------------------------------------------------


def test_encuentra_skyrim_por_steam(disco: Path):
    biblioteca = disco / "Program Files (x86)" / "Steam"
    _crear(
        biblioteca / "steamapps" / "libraryfolders.vdf",
        '"libraryfolders"\n{\n\t"0"\n\t{\n\t\t"path"\t\t"%s"\n\t}\n}\n' % str(disco / "Program Files (x86)" / "Steam").replace("\\", "\\\\"),
    )
    juego = biblioteca / "steamapps" / "common" / "Skyrim Special Edition"
    _crear(juego / "SkyrimSE.exe")

    assert juego in comprobar.buscar_skyrim(raices=[disco])


def test_encuentra_skyrim_en_una_segunda_biblioteca(tmp_path: Path, disco: Path):
    otra = tmp_path / "D" / "SteamLibrary"
    _crear(
        disco / "Program Files (x86)" / "Steam" / "steamapps" / "libraryfolders.vdf",
        '"libraryfolders"\n{\n\t"1"\n\t{\n\t\t"path"\t\t"%s"\n\t}\n}\n' % str(otra).replace("\\", "\\\\"),
    )
    juego = otra / "steamapps" / "common" / "Skyrim Special Edition"
    _crear(juego / "SkyrimSE.exe")

    assert juego in comprobar.buscar_skyrim(raices=[disco])


def test_encuentra_skyrim_fuera_de_steam(disco: Path):
    juego = disco / "Juegos" / "Skyrim VR"
    _crear(juego / "SkyrimVR.exe")

    assert juego in comprobar.buscar_skyrim(raices=[disco])


def test_ignora_carpetas_de_skyrim_sin_ejecutable(disco: Path):
    (disco / "Mods de Skyrim").mkdir()

    assert comprobar.buscar_skyrim(raices=[disco]) == []


def test_no_baja_mas_alla_del_limite_de_profundidad(disco: Path):
    hondo = disco / "a" / "b" / "c" / "d" / "e" / "f" / "Mantella"
    _crear(hondo / "config.ini")

    assert comprobar.buscar_config_mantella(raices=[disco], documentos=[]) == []
