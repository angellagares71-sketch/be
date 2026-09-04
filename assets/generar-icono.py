#!/usr/bin/env python3
"""Genera assets/skyrim-ia.ico sin dependencias externas.

El icono es un cuadrado redondeado oscuro con un bocadillo de dialogo en
azul hielo: el mod va de hablar con los PNJ. Se dibuja con supersampling 4x
para que tenga antialiasing y se guarda como ICO con entradas BMP de 32 bits,
que Windows admite en todas las versiones.

    python3 assets/generar-icono.py
"""

from __future__ import annotations

import struct
from pathlib import Path

TAMANOS = (16, 24, 32, 48, 64, 128, 256)
SUPER = 4  # factor de supersampling

FONDO_ARRIBA = (46, 56, 68)
FONDO_ABAJO = (22, 28, 36)
BORDE = (86, 104, 122)
BOCADILLO = (127, 196, 232)
PUNTO = (18, 24, 31)


def _mezcla(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def _dentro_rect_redondo(x, y, x0, y0, x1, y1, r):
    if x < x0 or x > x1 or y < y0 or y > y1:
        return False
    for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r), (x0 + r, y1 - r), (x1 - r, y1 - r)):
        dentro_x = (x < x0 + r) if cx == x0 + r else (x > x1 - r)
        dentro_y = (y < y0 + r) if cy == y0 + r else (y > y1 - r)
        if dentro_x and dentro_y:
            return (x - cx) ** 2 + (y - cy) ** 2 <= r * r
    return True


def _dentro_triangulo(px, py, a, b, c):
    def signo(p1, p2, p3):
        return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

    d1, d2, d3 = signo((px, py), a, b), signo((px, py), b, c), signo((px, py), c, a)
    neg = d1 < 0 or d2 < 0 or d3 < 0
    pos = d1 > 0 or d2 > 0 or d3 > 0
    return not (neg and pos)


def render(size: int) -> bytes:
    """Devuelve `size*size` pixeles BGRA, de arriba a abajo."""
    n = size * SUPER
    u = n / 256.0  # unidad relativa a un lienzo de 256

    # Geometria en coordenadas del lienzo grande.
    marco = (6 * u, 6 * u, n - 6 * u, n - 6 * u)
    radio_marco = 44 * u
    burbuja = (46 * u, 58 * u, n - 46 * u, n - 92 * u)
    radio_burbuja = 26 * u
    cola = ((92 * u, n - 94 * u), (150 * u, n - 94 * u), (104 * u, n - 44 * u))
    puntos_y = (burbuja[1] + burbuja[3]) / 2
    puntos_x = [n / 2 - 44 * u, n / 2, n / 2 + 44 * u]
    radio_punto = 15 * u

    # Acumuladores por pixel de destino (media de los SUPER*SUPER subpixeles).
    acumulado = [[0.0, 0.0, 0.0, 0.0] for _ in range(size * size)]

    for sy in range(n):
        fila_t = sy / max(n - 1, 1)
        fondo = _mezcla(FONDO_ARRIBA, FONDO_ABAJO, fila_t)
        destino_y = sy // SUPER
        for sx in range(n):
            r = g = b = a = 0.0

            if _dentro_rect_redondo(sx, sy, *marco, radio_marco):
                r, g, b = fondo
                a = 255.0

                # Borde: un anillo interior mas claro.
                if not _dentro_rect_redondo(
                    sx, sy, marco[0] + 3 * u, marco[1] + 3 * u,
                    marco[2] - 3 * u, marco[3] - 3 * u, radio_marco - 3 * u
                ):
                    r, g, b = BORDE

                en_burbuja = _dentro_rect_redondo(sx, sy, *burbuja, radio_burbuja)
                en_cola = _dentro_triangulo(sx, sy, *cola)
                if en_burbuja or en_cola:
                    r, g, b = BOCADILLO
                    if en_burbuja:
                        for px in puntos_x:
                            if (sx - px) ** 2 + (sy - puntos_y) ** 2 <= radio_punto**2:
                                r, g, b = PUNTO
                                break

            celda = acumulado[destino_y * size + (sx // SUPER)]
            celda[0] += b
            celda[1] += g
            celda[2] += r
            celda[3] += a

    total = SUPER * SUPER
    return bytes(
        max(0, min(255, round(canal / total)))
        for celda in acumulado
        for canal in celda
    )


def _entrada_bmp(size: int, bgra_arriba_abajo: bytes) -> bytes:
    """Empaqueta un DIB de 32 bits como lo espera un ICO."""
    cabecera = struct.pack(
        "<IiiHHIIiiII",
        40, size, size * 2, 1, 32, 0, size * size * 4, 0, 0, 0, 0,
    )
    # El DIB va de abajo a arriba.
    filas = [
        bgra_arriba_abajo[y * size * 4 : (y + 1) * size * 4]
        for y in reversed(range(size))
    ]
    # Mascara AND: todo opaco, filas alineadas a 4 bytes.
    bytes_fila = ((size + 31) // 32) * 4
    mascara = b"\x00" * (bytes_fila * size)
    return cabecera + b"".join(filas) + mascara


def main() -> None:
    imagenes = []
    for size in TAMANOS:
        print(f"  dibujando {size}x{size}...")
        imagenes.append((size, _entrada_bmp(size, render(size))))

    cabecera = struct.pack("<HHH", 0, 1, len(imagenes))
    desplazamiento = 6 + 16 * len(imagenes)
    entradas, cuerpos = b"", b""
    for size, datos in imagenes:
        ancho = 0 if size >= 256 else size
        entradas += struct.pack(
            "<BBBBHHII", ancho, ancho, 0, 0, 1, 32, len(datos), desplazamiento
        )
        cuerpos += datos
        desplazamiento += len(datos)

    destino = Path(__file__).with_name("skyrim-ia.ico")
    destino.write_bytes(cabecera + entradas + cuerpos)
    print(f"Escrito {destino} ({destino.stat().st_size} bytes, {len(imagenes)} tamanos)")


if __name__ == "__main__":
    main()
