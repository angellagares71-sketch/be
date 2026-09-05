#!/usr/bin/env python3
"""Manda una peticion real al proveedor configurado en el .env.

Sirve para que un error de clave, de saldo o de modelo salga durante la
instalacion y no a mitad de una conversacion con un PNJ.

    python scripts/probar-proveedor.py
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "server"))

try:
    from mantella_gateway.config import ConfigError, load_config, load_dotenv
except ImportError:
    print("No se encuentra el paquete del gateway. Ejecuta antes scripts/instalar.", file=sys.stderr)
    raise SystemExit(2)


def main() -> int:
    entorno: dict[str, str] = {}
    load_dotenv(RAIZ / ".env", entorno)
    if not entorno:
        print("No hay fichero .env. Ejecuta scripts/configurar primero.", file=sys.stderr)
        return 2

    try:
        config = load_config(entorno)
    except ConfigError as exc:
        print(f"  Configuracion invalida: {exc}", file=sys.stderr)
        return 1

    cuerpo = json.dumps(
        {
            "model": config.model,
            "messages": [{"role": "user", "content": "Di solamente: listo"}],
            "max_tokens": 20,
        }
    ).encode("utf-8")

    peticion = urllib.request.Request(
        config.upstream_chat_url,
        data=cuerpo,
        headers={"Content-Type": "application/json", **config.auth_headers()},
    )

    try:
        with urllib.request.urlopen(peticion, timeout=30) as respuesta:
            datos = json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detalle = exc.read().decode("utf-8", "replace")[:300]
        print(f"  El proveedor respondio {exc.code}.", file=sys.stderr)
        print(f"  {_pista(exc.code, config.provider)}", file=sys.stderr)
        if detalle.strip():
            print(f"  Detalle: {detalle}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"  No se pudo conectar con {config.base_url}: {exc.reason}", file=sys.stderr)
        if config.provider in {"ollama", "lmstudio", "koboldcpp"}:
            print(f"  Arranca {config.provider} y vuelve a intentarlo.", file=sys.stderr)
        return 1
    except (ValueError, OSError) as exc:
        print(f"  Respuesta invalida del proveedor: {exc}", file=sys.stderr)
        return 1

    try:
        texto = datos["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, AttributeError):
        print("  El proveedor contesto, pero con un formato inesperado.", file=sys.stderr)
        return 1

    print(f"  Conexion correcta. El modelo {config.model} respondio: {texto[:60]!r}")
    return 0


def _pista(codigo: int, proveedor: str) -> str:
    pistas = {
        401: "La clave no es valida. Genera una nueva y vuelve a configurar.",
        403: "La clave no tiene permiso para este modelo.",
        402: "No hay saldo en la cuenta. Recarga o usa un modelo gratuito.",
        404: f"El modelo no existe en {proveedor}. Revisa su identificador exacto.",
        429: "Demasiadas peticiones. Espera un momento y reintenta.",
    }
    return pistas.get(codigo, "Revisa la clave y el modelo en el fichero .env.")


if __name__ == "__main__":
    raise SystemExit(main())
