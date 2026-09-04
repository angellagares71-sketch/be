"""Cliente HTTP hacia el proveedor de modelos, con reintentos."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator

import httpx

from .config import GatewayConfig

log = logging.getLogger("mantella_gateway.upstream")

#: Codigos que merecen otro intento: limite de tasa y fallos de servidor.
REINTENTABLES = frozenset({408, 409, 425, 429, 500, 502, 503, 504})


class UpstreamError(RuntimeError):
    """El proveedor no devolvio una respuesta utilizable."""

    def __init__(self, message: str, status_code: int = 502, detail: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


def build_client(config: GatewayConfig) -> httpx.AsyncClient:
    """Crea el cliente compartido con los tiempos de espera configurados."""
    timeout = httpx.Timeout(
        config.request_timeout,
        connect=config.connect_timeout,
        read=config.request_timeout,
    )
    return httpx.AsyncClient(timeout=timeout, follow_redirects=True)


def prepare_payload(body: dict[str, Any], config: GatewayConfig) -> dict[str, Any]:
    """Completa la peticion de Mantella con los valores del gateway.

    Mantella manda el modelo que tenga en su config.ini; si es un
    marcador de posicion o falta, se usa el del gateway. Los parametros de
    generacion solo se rellenan cuando la peticion no los trae.
    """
    payload = dict(body)

    modelo = str(payload.get("model") or "").strip()
    if not modelo or modelo.lower() in {"mantella", "gateway", "default", "auto"}:
        payload["model"] = config.model
    if not payload.get("model"):
        raise UpstreamError(
            "No hay modelo definido: indica MANTELLA_MODEL o el campo 'model' en config.ini",
            status_code=400,
        )

    if config.temperature is not None:
        payload.setdefault("temperature", config.temperature)
    if config.top_p is not None:
        payload.setdefault("top_p", config.top_p)
    if config.max_tokens is not None:
        payload.setdefault("max_tokens", config.max_tokens)

    if config.system_prefix:
        mensajes = list(payload.get("messages") or [])
        mensajes.insert(0, {"role": "system", "content": config.system_prefix})
        payload["messages"] = mensajes

    return payload


async def post_chat(
    client: httpx.AsyncClient,
    config: GatewayConfig,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Peticion sin streaming, reintentando los fallos transitorios."""
    ultimo: Exception | None = None

    for intento in range(config.max_retries + 1):
        try:
            respuesta = await client.post(
                config.upstream_chat_url,
                json=payload,
                headers=config.auth_headers(),
            )
        except httpx.HTTPError as exc:
            ultimo = exc
            log.warning("Fallo de red hacia el proveedor (intento %d): %s", intento + 1, exc)
        else:
            if respuesta.status_code in REINTENTABLES and intento < config.max_retries:
                log.warning(
                    "El proveedor respondio %d (intento %d), reintentando",
                    respuesta.status_code,
                    intento + 1,
                )
            elif respuesta.status_code >= 400:
                raise UpstreamError(
                    f"El proveedor respondio {respuesta.status_code}",
                    status_code=respuesta.status_code,
                    detail=respuesta.text[:2000],
                )
            else:
                try:
                    return respuesta.json()
                except ValueError as exc:
                    raise UpstreamError(
                        "El proveedor devolvio una respuesta que no es JSON",
                        detail=respuesta.text[:2000],
                    ) from exc

        if intento < config.max_retries:
            await asyncio.sleep(config.retry_backoff * (2**intento))

    raise UpstreamError(
        "No se pudo contactar con el proveedor tras varios intentos",
        status_code=504,
        detail=str(ultimo) if ultimo else "",
    )


async def stream_chat(
    client: httpx.AsyncClient,
    config: GatewayConfig,
    payload: dict[str, Any],
) -> AsyncIterator[str]:
    """Peticion en streaming; devuelve las lineas SSE crudas del proveedor.

    Solo se reintenta antes de recibir el primer byte: una vez empezado el
    stream, repetirlo duplicaria texto ya entregado a Mantella.
    """
    ultimo: Exception | None = None

    for intento in range(config.max_retries + 1):
        try:
            async with client.stream(
                "POST",
                config.upstream_chat_url,
                json=payload,
                headers=config.auth_headers(),
            ) as respuesta:
                if respuesta.status_code >= 400:
                    cuerpo = (await respuesta.aread()).decode("utf-8", "replace")
                    if respuesta.status_code in REINTENTABLES and intento < config.max_retries:
                        log.warning(
                            "El proveedor respondio %d en streaming (intento %d), reintentando",
                            respuesta.status_code,
                            intento + 1,
                        )
                        await asyncio.sleep(config.retry_backoff * (2**intento))
                        continue
                    raise UpstreamError(
                        f"El proveedor respondio {respuesta.status_code}",
                        status_code=respuesta.status_code,
                        detail=cuerpo[:2000],
                    )

                async for linea in respuesta.aiter_lines():
                    yield linea
                return
        except httpx.HTTPError as exc:
            ultimo = exc
            log.warning("Fallo de red en streaming (intento %d): %s", intento + 1, exc)
            if intento < config.max_retries:
                await asyncio.sleep(config.retry_backoff * (2**intento))

    raise UpstreamError(
        "No se pudo abrir el stream con el proveedor",
        status_code=504,
        detail=str(ultimo) if ultimo else "",
    )


async def list_models(client: httpx.AsyncClient, config: GatewayConfig) -> dict[str, Any]:
    """Reenvia el catalogo de modelos del proveedor."""
    try:
        respuesta = await client.get(config.upstream_models_url, headers=config.auth_headers())
    except httpx.HTTPError as exc:
        raise UpstreamError("No se pudo consultar el catalogo de modelos", status_code=504, detail=str(exc)) from exc

    if respuesta.status_code >= 400:
        raise UpstreamError(
            f"El proveedor respondio {respuesta.status_code} al pedir los modelos",
            status_code=respuesta.status_code,
            detail=respuesta.text[:2000],
        )
    try:
        return respuesta.json()
    except ValueError as exc:
        raise UpstreamError("El catalogo de modelos no es JSON valido") from exc
