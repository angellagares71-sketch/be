"""Pruebas de la carga de configuracion."""

import pytest

from mantella_gateway.config import ConfigError, load_config, load_dotenv


def test_valores_por_defecto_con_openrouter():
    cfg = load_config({"MANTELLA_API_KEY": "sk-test"})
    assert cfg.provider == "openrouter"
    assert cfg.base_url == "https://openrouter.ai/api/v1"
    assert cfg.upstream_chat_url == "https://openrouter.ai/api/v1/chat/completions"
    assert cfg.auth_headers()["Authorization"] == "Bearer sk-test"
    assert cfg.extra_headers["X-Title"] == "Mantella Gateway"


def test_ollama_no_exige_clave():
    cfg = load_config({"MANTELLA_PROVIDER": "ollama"})
    assert cfg.base_url == "http://localhost:11434/v1"
    assert "Authorization" not in cfg.auth_headers()


def test_openrouter_sin_clave_falla():
    with pytest.raises(ConfigError, match="necesita una clave"):
        load_config({"MANTELLA_PROVIDER": "openrouter"})


def test_proveedor_desconocido_falla():
    with pytest.raises(ConfigError, match="no es valido"):
        load_config({"MANTELLA_PROVIDER": "inventado"})


def test_custom_exige_base_url():
    with pytest.raises(ConfigError, match="MANTELLA_BASE_URL"):
        load_config({"MANTELLA_PROVIDER": "custom"})


def test_base_url_debe_ser_http():
    with pytest.raises(ConfigError, match="http"):
        load_config({"MANTELLA_PROVIDER": "custom", "MANTELLA_BASE_URL": "localhost:8080"})


def test_puerto_no_numerico_falla():
    with pytest.raises(ConfigError, match="MANTELLA_PORT"):
        load_config({"MANTELLA_PROVIDER": "ollama", "MANTELLA_PORT": "ocho mil"})


def test_clave_desde_fichero(tmp_path):
    fichero = tmp_path / "GPT_SECRET_KEY.txt"
    fichero.write_text("sk-desde-fichero\n", encoding="utf-8")
    cfg = load_config({"MANTELLA_API_KEY_FILE": str(fichero)})
    assert cfg.api_key == "sk-desde-fichero"


def test_clave_desde_fichero_inexistente(tmp_path):
    with pytest.raises(ConfigError, match="inexistente"):
        load_config({"MANTELLA_API_KEY_FILE": str(tmp_path / "no-existe.txt")})


def test_barra_final_en_base_url_no_duplica():
    cfg = load_config({"MANTELLA_PROVIDER": "ollama", "MANTELLA_BASE_URL": "http://x/v1/"})
    assert cfg.upstream_chat_url == "http://x/v1/chat/completions"
    assert cfg.upstream_models_url == "http://x/v1/models"


def test_load_dotenv_no_pisa_el_entorno(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        '# comentario\nMANTELLA_MODEL="un/modelo"\nexport MANTELLA_PORT=9000\nYA_DEFINIDA=nueva\nsin_igual\n',
        encoding="utf-8",
    )
    entorno = {"YA_DEFINIDA": "original"}
    anadidas = load_dotenv(env_file, entorno)

    assert entorno["MANTELLA_MODEL"] == "un/modelo"
    assert entorno["MANTELLA_PORT"] == "9000"
    assert entorno["YA_DEFINIDA"] == "original"
    assert "YA_DEFINIDA" not in anadidas


def test_load_dotenv_sin_fichero_no_falla(tmp_path):
    assert load_dotenv(tmp_path / "no-existe.env", {}) == {}
