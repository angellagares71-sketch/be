"""Servidor compatible con la API de OpenAI al que apunta Mantella.

Mantella habla el dialecto `/v1/chat/completions` de OpenAI. Este gateway
lo expone en local, reenvia al proveedor configurado y devuelve el texto ya
adaptado al motor de voz.
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from . import upstream
from .config import GatewayConfig, load_config
from .sanitize import SentenceStreamSanitizer, limit_sentences, sanitize_for_tts

log = logging.getLogger("mantella_gateway")

VERSION = "1.0.0"


def _sanitize_choices(datos: dict[str, Any], config: GatewayConfig) -> dict[str, Any]:
    """Limpia el texto de cada `choice` de una respuesta completa."""
    if not config.sanitize_output:
        return datos

    for choice in datos.get("choices") or []:
        mensaje = choice.get("message")
        if not isinstance(mensaje, dict):
            continue
        contenido = mensaje.get("content")
        if not isinstance(contenido, str):
            continue
        limpio = sanitize_for_tts(contenido, strip_actions=config.strip_actions)
        mensaje["content"] = limit_sentences(limpio, config.max_sentences)
    return datos


async def _sse_saneado(
    lineas: AsyncIterator[str],
    config: GatewayConfig,
) -> AsyncIterator[str]:
    """Reescribe el stream SSE del proveedor saneando cada frase.

    Se emiten frases completas en lugar de fragmentos sueltos: es lo que
    necesita el TTS de Mantella, que sintetiza frase a frase.
    """
    sanitizer = SentenceStreamSanitizer(
        strip_actions=config.strip_actions,
        max_sentences=config.max_sentences,
    )
    ultimo_evento: dict[str, Any] | None = None
    terminado = False

    async for linea in lineas:
        if not linea.strip():
            continue
        if not linea.startswith("data:"):
            # Comentarios SSE (`: keep-alive`) y cabeceras se dejan pasar.
            yield f"{linea}\n\n"
            continue

        carga = linea[len("data:") :].strip()
        if carga == "[DONE]":
            terminado = True
            break

        try:
            evento = json.loads(carga)
        except ValueError:
            log.debug("Fragmento SSE ilegible, se descarta: %r", carga[:200])
            continue

        ultimo_evento = evento
        choices = evento.get("choices") or []
        if not choices:
            continue

        delta = choices[0].get("delta") or {}
        texto = delta.get("content")
        if not isinstance(texto, str) or not texto:
            # Puede ser el evento de cierre (finish_reason) sin contenido.
            if choices[0].get("finish_reason"):
                continue
            continue

        saneado = sanitizer.feed(texto)
        if saneado:
            salida = json.loads(json.dumps(evento))
            salida["choices"][0]["delta"] = {"role": "assistant", "content": saneado}
            salida["choices"][0].pop("finish_reason", None)
            yield f"data: {json.dumps(salida, ensure_ascii=False)}\n\n"

        if sanitizer.finished:
            break

    resto = sanitizer.flush()
    if resto:
        plantilla = ultimo_evento or {
            "id": f"chatcmpl-gw-{int(time.time())}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": config.model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": None}],
        }
        salida = json.loads(json.dumps(plantilla))
        salida.setdefault("choices", [{"index": 0}])
        salida["choices"][0]["delta"] = {"role": "assistant", "content": resto}
        salida["choices"][0].pop("finish_reason", None)
        yield f"data: {json.dumps(salida, ensure_ascii=False)}\n\n"

    cierre = {
        "id": (ultimo_evento or {}).get("id", f"chatcmpl-gw-{int(time.time())}"),
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": (ultimo_evento or {}).get("model", config.model),
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield f"data: {json.dumps(cierre, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"
    if not terminado:
        log.debug("El stream del proveedor se cerro sin enviar [DONE]")


async def _sse_directo(lineas: AsyncIterator[str]) -> AsyncIterator[str]:
    """Reenvia el stream tal cual cuando el saneado esta desactivado."""
    async for linea in lineas:
        if linea.strip():
            yield f"{linea}\n\n"


def create_app(config: GatewayConfig | None = None) -> FastAPI:
    """Construye la aplicacion. `config` se inyecta en los tests."""
    ajustes = config or load_config()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Si ya hay un cliente inyectado (tests), se respeta y no se cierra:
        # su ciclo de vida lo gobierna quien lo creo.
        propio = app.state.client is None
        if propio:
            app.state.client = upstream.build_client(app.state.config)
        log.info(
            "Gateway listo en http://%s:%d/v1 -> %s (%s)",
            app.state.config.host,
            app.state.config.port,
            app.state.config.base_url,
            app.state.config.provider,
        )
        try:
            yield
        finally:
            if propio:
                await app.state.client.aclose()

    app = FastAPI(title="Mantella Gateway", version=VERSION, lifespan=lifespan)
    app.state.config = ajustes
    app.state.client = None

    @app.exception_handler(upstream.UpstreamError)
    async def _upstream_error(_: Request, exc: upstream.UpstreamError) -> JSONResponse:
        log.error("Error del proveedor: %s (%s)", exc, exc.detail[:500])
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"message": str(exc), "type": "upstream_error", "detail": exc.detail}},
        )

    @app.get("/health")
    async def health() -> dict[str, Any]:
        cfg: GatewayConfig = app.state.config
        return {
            "status": "ok",
            "version": VERSION,
            "provider": cfg.provider,
            "base_url": cfg.base_url,
            "model": cfg.model,
            "api_key_configurada": bool(cfg.api_key),
            "sanitize_output": cfg.sanitize_output,
            "max_sentences": cfg.max_sentences,
        }

    @app.get("/v1/models")
    async def models() -> dict[str, Any]:
        return await upstream.list_models(app.state.client, app.state.config)

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request):
        cfg: GatewayConfig = app.state.config
        try:
            body = await request.json()
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"error": {"message": "El cuerpo de la peticion no es JSON valido"}},
            )
        if not isinstance(body, dict):
            return JSONResponse(
                status_code=400,
                content={"error": {"message": "Se esperaba un objeto JSON"}},
            )

        payload = upstream.prepare_payload(body, cfg)

        if payload.get("stream"):
            lineas = upstream.stream_chat(app.state.client, cfg, payload)
            generador = _sse_saneado(lineas, cfg) if cfg.sanitize_output else _sse_directo(lineas)
            return StreamingResponse(
                generador,
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )

        datos = await upstream.post_chat(app.state.client, cfg, payload)
        return JSONResponse(content=_sanitize_choices(datos, cfg))

    return app
