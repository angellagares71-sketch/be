"""Carga y validacion de la configuracion del gateway.

La configuracion se lee de variables de entorno. Si existe un fichero .env
en el directorio de trabajo (o el indicado por MANTELLA_GATEWAY_ENV) sus
valores se cargan primero, sin pisar las variables ya definidas en el
entorno real.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

#: Proveedores conocidos: url base por defecto y si exigen clave de API.
PROVIDERS: dict[str, dict[str, object]] = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "requires_key": True,
        "default_model": "mistralai/mistral-nemo",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "requires_key": True,
        "default_model": "gpt-4o-mini",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "requires_key": False,
        "default_model": "llama3.1:8b",
    },
    "lmstudio": {
        "base_url": "http://localhost:1234/v1",
        "requires_key": False,
        "default_model": "local-model",
    },
    "koboldcpp": {
        "base_url": "http://localhost:5001/v1",
        "requires_key": False,
        "default_model": "koboldcpp",
    },
    "custom": {
        "base_url": "",
        "requires_key": False,
        "default_model": "",
    },
}


class ConfigError(ValueError):
    """La configuracion suministrada no es utilizable."""


def _as_bool(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "y", "on", "si", "sí"}


def _as_int(raw: str, name: str) -> int:
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ConfigError(f"{name} debe ser un numero entero, se recibio {raw!r}") from exc


def _as_float(raw: str, name: str) -> float:
    try:
        return float(raw.strip())
    except ValueError as exc:
        raise ConfigError(f"{name} debe ser un numero, se recibio {raw!r}") from exc


def load_dotenv(path: str | os.PathLike[str], environ: dict[str, str] | None = None) -> dict[str, str]:
    """Vuelca un fichero .env en `environ` sin sobrescribir lo ya definido.

    Devuelve solo las claves que se han anadido, para poder registrarlas.
    """
    target = os.environ if environ is None else environ
    added: dict[str, str] = {}
    file = Path(path)
    if not file.is_file():
        return added

    for line in file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key and key not in target:
            target[key] = value
            added[key] = value
    return added


@dataclass(frozen=True)
class GatewayConfig:
    """Ajustes efectivos del gateway."""

    # Servidor local al que apunta Mantella.
    host: str = "127.0.0.1"
    port: int = 8000

    # Proveedor de arriba.
    provider: str = "openrouter"
    base_url: str = ""
    api_key: str = ""
    model: str = ""

    # Parametros de generacion aplicados cuando Mantella no los envia.
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None

    # Robustez.
    request_timeout: float = 60.0
    connect_timeout: float = 10.0
    max_retries: int = 2
    retry_backoff: float = 1.0

    # Adaptacion del texto al TTS de Mantella.
    sanitize_output: bool = True
    strip_actions: bool = True
    max_sentences: int = 0  # 0 = sin limite

    # Prefijo opcional inyectado como primer mensaje de sistema.
    system_prefix: str = ""

    log_level: str = "INFO"
    extra_headers: dict[str, str] = field(default_factory=dict)

    @property
    def upstream_chat_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/chat/completions"

    @property
    def upstream_models_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/models"

    def auth_headers(self) -> dict[str, str]:
        headers = dict(self.extra_headers)
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


def _read_api_key(env: dict[str, str]) -> str:
    """La clave puede venir de una variable o de un fichero (estilo Mantella)."""
    key_file = env.get("MANTELLA_API_KEY_FILE", "").strip()
    if key_file:
        path = Path(key_file)
        if not path.is_file():
            raise ConfigError(f"MANTELLA_API_KEY_FILE apunta a un fichero inexistente: {key_file}")
        return path.read_text(encoding="utf-8").strip()
    return env.get("MANTELLA_API_KEY", "").strip()


def load_config(env: dict[str, str] | None = None) -> GatewayConfig:
    """Construye la configuracion a partir del entorno, validandola."""
    env = dict(os.environ if env is None else env)

    provider = env.get("MANTELLA_PROVIDER", "openrouter").strip().lower()
    if provider not in PROVIDERS:
        conocidos = ", ".join(sorted(PROVIDERS))
        raise ConfigError(f"MANTELLA_PROVIDER={provider!r} no es valido. Opciones: {conocidos}")
    perfil = PROVIDERS[provider]

    base_url = env.get("MANTELLA_BASE_URL", "").strip() or str(perfil["base_url"])
    if not base_url:
        raise ConfigError(
            "Con MANTELLA_PROVIDER=custom hay que indicar MANTELLA_BASE_URL "
            "(por ejemplo http://localhost:8080/v1)"
        )
    if not base_url.startswith(("http://", "https://")):
        raise ConfigError(f"MANTELLA_BASE_URL debe empezar por http:// o https://, se recibio {base_url!r}")

    api_key = _read_api_key(env)
    if perfil["requires_key"] and not api_key:
        raise ConfigError(
            f"El proveedor {provider!r} necesita una clave de API. "
            "Define MANTELLA_API_KEY o MANTELLA_API_KEY_FILE."
        )

    model = env.get("MANTELLA_MODEL", "").strip() or str(perfil["default_model"])

    extra_headers: dict[str, str] = {}
    if provider == "openrouter":
        # OpenRouter usa estas cabeceras para atribuir el trafico.
        extra_headers["HTTP-Referer"] = env.get(
            "MANTELLA_REFERER", "https://github.com/angellagares71-sketch/be"
        )
        extra_headers["X-Title"] = env.get("MANTELLA_APP_TITLE", "Mantella Gateway")

    def opt_float(name: str) -> float | None:
        raw = env.get(name, "").strip()
        return _as_float(raw, name) if raw else None

    def opt_int(name: str) -> int | None:
        raw = env.get(name, "").strip()
        return _as_int(raw, name) if raw else None

    return GatewayConfig(
        host=env.get("MANTELLA_HOST", "127.0.0.1").strip(),
        port=_as_int(env.get("MANTELLA_PORT", "8000"), "MANTELLA_PORT"),
        provider=provider,
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=opt_float("MANTELLA_TEMPERATURE"),
        top_p=opt_float("MANTELLA_TOP_P"),
        max_tokens=opt_int("MANTELLA_MAX_TOKENS"),
        request_timeout=_as_float(env.get("MANTELLA_TIMEOUT", "60"), "MANTELLA_TIMEOUT"),
        connect_timeout=_as_float(env.get("MANTELLA_CONNECT_TIMEOUT", "10"), "MANTELLA_CONNECT_TIMEOUT"),
        max_retries=_as_int(env.get("MANTELLA_MAX_RETRIES", "2"), "MANTELLA_MAX_RETRIES"),
        retry_backoff=_as_float(env.get("MANTELLA_RETRY_BACKOFF", "1.0"), "MANTELLA_RETRY_BACKOFF"),
        sanitize_output=_as_bool(env.get("MANTELLA_SANITIZE", "true")),
        strip_actions=_as_bool(env.get("MANTELLA_STRIP_ACTIONS", "true")),
        max_sentences=_as_int(env.get("MANTELLA_MAX_SENTENCES", "0"), "MANTELLA_MAX_SENTENCES"),
        system_prefix=env.get("MANTELLA_SYSTEM_PREFIX", ""),
        log_level=env.get("MANTELLA_LOG_LEVEL", "INFO").strip().upper(),
        extra_headers=extra_headers,
    )
