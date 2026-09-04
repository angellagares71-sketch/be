"""Utilidades compartidas: un proveedor simulado sin salir a la red."""

from __future__ import annotations

import json
from typing import Callable

import httpx
import pytest

from mantella_gateway.app import create_app
from mantella_gateway.config import load_config


@pytest.fixture
def hacer_config():
    def _hacer(**overrides):
        env = {"MANTELLA_PROVIDER": "ollama", "MANTELLA_MODEL": "modelo-test"}
        env.update({k: str(v) for k, v in overrides.items()})
        return load_config(env)

    return _hacer


def respuesta_completa(texto: str) -> dict:
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 1,
        "model": "modelo-test",
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": texto}, "finish_reason": "stop"}
        ],
    }


def sse_de(trozos: list[str], model: str = "modelo-test") -> str:
    """Construye un cuerpo SSE como el que devuelve un proveedor real."""
    lineas = []
    for trozo in trozos:
        evento = {
            "id": "chatcmpl-1",
            "object": "chat.completion.chunk",
            "created": 1,
            "model": model,
            "choices": [{"index": 0, "delta": {"content": trozo}, "finish_reason": None}],
        }
        lineas.append(f"data: {json.dumps(evento)}\n\n")
    cierre = {
        "id": "chatcmpl-1",
        "object": "chat.completion.chunk",
        "created": 1,
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    lineas.append(f"data: {json.dumps(cierre)}\n\n")
    lineas.append("data: [DONE]\n\n")
    return "".join(lineas)


@pytest.fixture
def montar_app():
    """Crea la app con un transporte simulado y devuelve (app, peticiones)."""

    def _montar(handler: Callable[[httpx.Request], httpx.Response], config):
        peticiones: list[httpx.Request] = []

        def _registrar(request: httpx.Request) -> httpx.Response:
            peticiones.append(request)
            return handler(request)

        app = create_app(config)
        app.state.client = httpx.AsyncClient(transport=httpx.MockTransport(_registrar))
        return app, peticiones

    return _montar
