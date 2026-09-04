#!/usr/bin/env bash
# Arranca el gateway de Mantella. Dejalo corriendo mientras juegas.
set -euo pipefail

raiz="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python="$raiz/.venv/bin/python"

if [ ! -x "$python" ]; then
    echo "Error: no hay entorno virtual. Ejecuta antes: ./scripts/instalar.sh" >&2
    exit 1
fi
if [ ! -f "$raiz/.env" ]; then
    echo "Aviso: no hay fichero .env; se usaran los valores por defecto." >&2
fi

echo "Arrancando el gateway. Dejalo corriendo mientras juegas (Ctrl+C para parar)."
echo

cd "$raiz/server"
export MANTELLA_GATEWAY_ENV="$raiz/.env"
exec "$python" -m mantella_gateway
