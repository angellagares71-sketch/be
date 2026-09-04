"""Gateway local compatible con OpenAI para el mod Mantella de Skyrim."""

from .config import GatewayConfig, load_config
from .sanitize import sanitize_for_tts

__all__ = ["GatewayConfig", "load_config", "sanitize_for_tts", "__version__"]
__version__ = "1.0.0"
