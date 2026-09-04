"""Arranque del gateway: `python -m mantella_gateway`."""

from __future__ import annotations

import logging
import os
import sys

import uvicorn

from .app import create_app
from .config import ConfigError, load_config, load_dotenv


def main() -> int:
    load_dotenv(os.environ.get("MANTELLA_GATEWAY_ENV", ".env"))

    try:
        config = load_config()
    except ConfigError as exc:
        print(f"Error de configuracion: {exc}", file=sys.stderr)
        print("Revisa tu fichero .env (parte de config/gateway.env.ejemplo).", file=sys.stderr)
        return 2

    logging.basicConfig(
        level=getattr(logging, config.log_level, logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    uvicorn.run(
        create_app(config),
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
