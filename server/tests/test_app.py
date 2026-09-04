"""Pruebas del gateway extremo a extremo contra un proveedor simulado."""

from __future__ import annotations

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from conftest import respuesta_completa, sse_de


def _textos_del_sse(cuerpo: str) -> list[str]:
    """Extrae el contenido de los deltas de un cuerpo SSE."""
    textos = []
    for linea in cuerpo.splitlines():
        if not linea.startswith("data:"):
            continue
        carga = linea[len("data:") :].strip()
        if carga == "[DONE]":
            continue
        evento = json.loads(carga)
        contenido = evento["choices"][0].get("delta", {}).get("content")
        if contenido:
            textos.append(contenido)
    return textos


class TestSalud:
    def test_health_describe_la_configuracion(self, hacer_config, montar_app):
        app, _ = montar_app(lambda r: httpx.Response(200, json={}), hacer_config())
        with TestClient(app) as cliente:
            datos = cliente.get("/health").json()
        assert datos["status"] == "ok"
        assert datos["provider"] == "ollama"
        assert datos["model"] == "modelo-test"
        assert datos["api_key_configurada"] is False


class TestChatSinStreaming:
    def test_sanea_la_respuesta(self, hacer_config, montar_app):
        cruda = "*se gira* **Bienvenido** a Riften. No te fies de nadie."
        app, _ = montar_app(
            lambda r: httpx.Response(200, json=respuesta_completa(cruda)), hacer_config()
        )
        with TestClient(app) as cliente:
            r = cliente.post("/v1/chat/completions", json={"messages": [{"role": "user", "content": "hola"}]})
        assert r.status_code == 200
        assert r.json()["choices"][0]["message"]["content"] == (
            "Bienvenido a Riften. No te fies de nadie."
        )

    def test_se_puede_desactivar_el_saneado(self, hacer_config, montar_app):
        cruda = "*se gira* Hola."
        app, _ = montar_app(
            lambda r: httpx.Response(200, json=respuesta_completa(cruda)),
            hacer_config(MANTELLA_SANITIZE="false"),
        )
        with TestClient(app) as cliente:
            r = cliente.post("/v1/chat/completions", json={"messages": []})
        assert r.json()["choices"][0]["message"]["content"] == cruda

    def test_limita_el_numero_de_frases(self, hacer_config, montar_app):
        app, _ = montar_app(
            lambda r: httpx.Response(200, json=respuesta_completa("Una. Dos. Tres. Cuatro.")),
            hacer_config(MANTELLA_MAX_SENTENCES=2),
        )
        with TestClient(app) as cliente:
            r = cliente.post("/v1/chat/completions", json={"messages": []})
        assert r.json()["choices"][0]["message"]["content"] == "Una. Dos."

    def test_rellena_el_modelo_del_gateway(self, hacer_config, montar_app):
        app, peticiones = montar_app(
            lambda r: httpx.Response(200, json=respuesta_completa("Hola.")), hacer_config()
        )
        with TestClient(app) as cliente:
            cliente.post("/v1/chat/completions", json={"messages": [], "model": "  "})
        assert json.loads(peticiones[0].content)["model"] == "modelo-test"

    def test_respeta_el_modelo_que_manda_mantella(self, hacer_config, montar_app):
        app, peticiones = montar_app(
            lambda r: httpx.Response(200, json=respuesta_completa("Hola.")), hacer_config()
        )
        with TestClient(app) as cliente:
            cliente.post("/v1/chat/completions", json={"messages": [], "model": "otro/modelo"})
        assert json.loads(peticiones[0].content)["model"] == "otro/modelo"

    def test_aplica_parametros_por_defecto_sin_pisar_los_recibidos(self, hacer_config, montar_app):
        app, peticiones = montar_app(
            lambda r: httpx.Response(200, json=respuesta_completa("Hola.")),
            hacer_config(MANTELLA_TEMPERATURE="0.9", MANTELLA_MAX_TOKENS="200"),
        )
        with TestClient(app) as cliente:
            cliente.post("/v1/chat/completions", json={"messages": [], "temperature": 0.2})
        enviado = json.loads(peticiones[0].content)
        assert enviado["temperature"] == 0.2  # el de Mantella manda
        assert enviado["max_tokens"] == 200  # este lo pone el gateway

    def test_inyecta_el_prefijo_de_sistema(self, hacer_config, montar_app):
        app, peticiones = montar_app(
            lambda r: httpx.Response(200, json=respuesta_completa("Hola.")),
            hacer_config(MANTELLA_SYSTEM_PREFIX="Responde siempre en espanol."),
        )
        with TestClient(app) as cliente:
            cliente.post("/v1/chat/completions", json={"messages": [{"role": "user", "content": "hi"}]})
        mensajes = json.loads(peticiones[0].content)["messages"]
        assert mensajes[0] == {"role": "system", "content": "Responde siempre en espanol."}
        assert mensajes[1]["content"] == "hi"

    def test_cuerpo_no_json_da_400(self, hacer_config, montar_app):
        app, _ = montar_app(lambda r: httpx.Response(200, json={}), hacer_config())
        with TestClient(app) as cliente:
            r = cliente.post(
                "/v1/chat/completions",
                content=b"esto no es json",
                headers={"Content-Type": "application/json"},
            )
        assert r.status_code == 400


class TestErroresDelProveedor:
    def test_propaga_el_codigo_de_error(self, hacer_config, montar_app):
        app, _ = montar_app(
            lambda r: httpx.Response(401, text="clave invalida"),
            hacer_config(MANTELLA_MAX_RETRIES=0),
        )
        with TestClient(app) as cliente:
            r = cliente.post("/v1/chat/completions", json={"messages": []})
        assert r.status_code == 401
        assert "clave invalida" in r.json()["error"]["detail"]

    def test_reintenta_los_fallos_transitorios(self, hacer_config, montar_app):
        intentos = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            intentos["n"] += 1
            if intentos["n"] == 1:
                return httpx.Response(429, text="demasiadas peticiones")
            return httpx.Response(200, json=respuesta_completa("A la segunda va."))

        app, _ = montar_app(
            handler, hacer_config(MANTELLA_MAX_RETRIES=2, MANTELLA_RETRY_BACKOFF="0.01")
        )
        with TestClient(app) as cliente:
            r = cliente.post("/v1/chat/completions", json={"messages": []})
        assert intentos["n"] == 2
        assert r.status_code == 200
        assert r.json()["choices"][0]["message"]["content"] == "A la segunda va."

    def test_agota_los_reintentos_y_devuelve_error(self, hacer_config, montar_app):
        app, peticiones = montar_app(
            lambda r: httpx.Response(503, text="caido"),
            hacer_config(MANTELLA_MAX_RETRIES=2, MANTELLA_RETRY_BACKOFF="0.01"),
        )
        with TestClient(app) as cliente:
            r = cliente.post("/v1/chat/completions", json={"messages": []})
        assert len(peticiones) == 3
        assert r.status_code == 503

    def test_error_de_red_da_504(self, hacer_config, montar_app):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("sin conexion", request=request)

        app, _ = montar_app(
            handler, hacer_config(MANTELLA_MAX_RETRIES=1, MANTELLA_RETRY_BACKOFF="0.01")
        )
        with TestClient(app) as cliente:
            r = cliente.post("/v1/chat/completions", json={"messages": []})
        assert r.status_code == 504


class TestStreaming:
    def test_emite_frases_completas_saneadas(self, hacer_config, montar_app):
        trozos = ["*asiente* ", "Bienve", "nido a ", "Riften. ", "No te ", "fies de nadie."]
        app, _ = montar_app(
            lambda r: httpx.Response(200, text=sse_de(trozos), headers={"content-type": "text/event-stream"}),
            hacer_config(),
        )
        with TestClient(app) as cliente:
            r = cliente.post("/v1/chat/completions", json={"messages": [], "stream": True})
        assert r.status_code == 200
        textos = _textos_del_sse(r.text)
        assert "".join(textos) == "Bienvenido a Riften. No te fies de nadie."
        # Cada evento debe llevar una frase entera, no un fragmento suelto.
        assert textos[0] == "Bienvenido a Riften."
        assert r.text.rstrip().endswith("data: [DONE]")

    def test_stream_sin_saneado_pasa_tal_cual(self, hacer_config, montar_app):
        trozos = ["*asiente* ", "Hola."]
        app, _ = montar_app(
            lambda r: httpx.Response(200, text=sse_de(trozos), headers={"content-type": "text/event-stream"}),
            hacer_config(MANTELLA_SANITIZE="false"),
        )
        with TestClient(app) as cliente:
            r = cliente.post("/v1/chat/completions", json={"messages": [], "stream": True})
        assert "".join(_textos_del_sse(r.text)) == "*asiente* Hola."

    def test_stream_respeta_el_limite_de_frases(self, hacer_config, montar_app):
        trozos = ["Una. ", "Dos. ", "Tres. ", "Cuatro."]
        app, _ = montar_app(
            lambda r: httpx.Response(200, text=sse_de(trozos), headers={"content-type": "text/event-stream"}),
            hacer_config(MANTELLA_MAX_SENTENCES=2),
        )
        with TestClient(app) as cliente:
            r = cliente.post("/v1/chat/completions", json={"messages": [], "stream": True})
        assert "".join(_textos_del_sse(r.text)) == "Una. Dos."

    def test_stream_con_error_del_proveedor(self, hacer_config, montar_app):
        app, _ = montar_app(
            lambda r: httpx.Response(401, text="clave invalida"),
            hacer_config(MANTELLA_MAX_RETRIES=0),
        )
        with TestClient(app) as cliente, pytest.raises(Exception):
            cliente.post("/v1/chat/completions", json={"messages": [], "stream": True})


class TestModelos:
    def test_reenvia_el_catalogo(self, hacer_config, montar_app):
        catalogo = {"object": "list", "data": [{"id": "modelo-test"}]}
        app, peticiones = montar_app(lambda r: httpx.Response(200, json=catalogo), hacer_config())
        with TestClient(app) as cliente:
            r = cliente.get("/v1/models")
        assert r.json() == catalogo
        assert peticiones[0].url.path.endswith("/models")
