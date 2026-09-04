#!/usr/bin/env bash
# Instala el gateway de Mantella en Linux o macOS.
set -euo pipefail

raiz="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
venv="$raiz/.venv"
python="${PYTHON:-python3}"

echo "Instalando el gateway de Mantella en $raiz"

if ! command -v "$python" >/dev/null 2>&1; then
    echo "Error: no se encuentra '$python'. Instala Python 3.10 o superior." >&2
    exit 1
fi

version="$("$python" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
if ! "$python" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
    echo "Error: se necesita Python 3.10 o superior; se encontro $version." >&2
    exit 1
fi
echo "  Python $version encontrado"

if [ ! -d "$venv" ]; then
    echo "  Creando el entorno virtual..."
    "$python" -m venv "$venv"
fi

echo "  Instalando dependencias..."
"$venv/bin/pip" install --quiet --upgrade pip
"$venv/bin/pip" install --quiet -r "$raiz/server/requirements.txt"
echo "  Dependencias instaladas"

if [ -f "$raiz/.env" ]; then
    echo "  Ya existe .env, no se toca"
else
    cp "$raiz/config/gateway.env.ejemplo" "$raiz/.env"
    echo "  Creado .env a partir del ejemplo"
fi

echo
echo "Instalacion terminada."
echo "Siguiente paso: edita .env y pon tu clave de API en MANTELLA_API_KEY."
echo "Despues arranca el gateway con:  ./scripts/arrancar.sh"
