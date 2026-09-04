"""Adaptacion del texto del modelo al motor de voz de Mantella.

El TTS (xVASynth, XTTS o Piper) lee literalmente lo que recibe: los
asteriscos, las vinetas y el markdown acaban pronunciados o rompen la
sintesis. Estas funciones dejan una linea de dialogo limpia.
"""

from __future__ import annotations

import re

# Acciones de rol: *se cruza de brazos*, (suspira), [mira al suelo].
_ACCION_ASTERISCO = re.compile(r"\*[^*\n]{1,200}\*")
_ACCION_PARENTESIS = re.compile(r"\((?:[^()\n]{1,200})\)")
_ACCION_CORCHETE = re.compile(r"\[(?:[^\[\]\n]{1,200})\]")

# Markdown estructural.
_BLOQUE_CODIGO = re.compile(r"```.*?```", re.DOTALL)
_CODIGO_INLINE = re.compile(r"`([^`\n]*)`")
_ENCABEZADO = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)
_CITA = re.compile(r"^\s{0,3}>\s?", re.MULTILINE)
_VINETA = re.compile(r"^\s{0,3}(?:[-*+]|\d{1,3}[.)])\s+", re.MULTILINE)
_ENLACE = re.compile(r"\[([^\]\n]*)\]\((?:[^)\s]+)(?:\s+\"[^\"]*\")?\)")
_NEGRITA = re.compile(r"(\*\*|__)(.+?)\1", re.DOTALL)
_CURSIVA = re.compile(r"(?<![\w*_])([*_])(?!\s)(.+?)(?<!\s)\1(?![\w*_])", re.DOTALL)
_REGLA = re.compile(r"^\s{0,3}(?:[-*_]\s*){3,}$", re.MULTILINE)

# Nombre del hablante al principio: "Lydia: hola". Se exige que lo anterior
# a los dos puntos parezca un nombre propio; si no, "Toma esto: ..." acabaria
# perdiendo media frase.
_PREFIJO_HABLANTE = re.compile(r"^\s*(?P<nombre>[^\s:][^:\n]{0,39}):\s+")

#: Particulas que pueden ir en minuscula dentro de un nombre.
_PARTICULAS = frozenset(
    {"de", "del", "la", "las", "el", "los", "y", "of", "the", "von", "van", "da", "di"}
)

_EMOJI = re.compile(
    "["
    "\U0001f300-\U0001faff"
    "\U00002600-\U000027bf"
    "\U0001f1e6-\U0001f1ff"
    "\U0000fe00-\U0000fe0f"
    "\U00002190-\U000021ff"
    "]+"
)

_ESPACIOS = re.compile(r"[ \t ]+")
_SALTOS = re.compile(r"\s*\n\s*")

# Fin de frase: puntuacion seguida de espacio/fin, respetando comillas y cierres.
_FIN_FRASE = re.compile(r"[.!?…]+[\"'»)\]]*(?=\s|$)")

# En streaming el fin del texto acumulado no cierra frase: el trozo siguiente
# puede continuarla. Solo se cierra ante un espacio que ya ha llegado.
_FIN_FRASE_STREAM = re.compile(r"[.!?…]+[\"'»)\]]*(?=\s)")

_ABREVIATURAS = {
    "sr", "sra", "srta", "dr", "dra", "st", "mr", "mrs", "ms", "vs", "etc",
    "ej", "aprox", "num", "pag", "jr", "prof",
}


def _markdown_previo(text: str) -> str:
    """Markdown que debe resolverse antes de detectar acotaciones."""
    text = _BLOQUE_CODIGO.sub(" ", text)
    text = _CODIGO_INLINE.sub(r"\1", text)
    text = _ENLACE.sub(r"\1", text)
    # Las negritas primero: `**texto**` contiene `*texto*` y el detector de
    # acotaciones lo confundiria con una accion, borrando el texto.
    text = _NEGRITA.sub(r"\2", text)
    return text


def _markdown_posterior(text: str) -> str:
    """Markdown estructural, ya sin acotaciones por medio."""
    text = _REGLA.sub(" ", text)
    text = _ENCABEZADO.sub("", text)
    text = _CITA.sub("", text)
    text = _VINETA.sub("", text)
    text = _CURSIVA.sub(r"\2", text)
    return text


def strip_markdown(text: str) -> str:
    """Quita el markdown dejando solo el texto legible."""
    return _markdown_posterior(_markdown_previo(text))


def strip_stage_directions(text: str) -> str:
    """Elimina acotaciones de rol que el TTS no deberia pronunciar."""
    text = _ACCION_ASTERISCO.sub(" ", text)
    text = _ACCION_PARENTESIS.sub(" ", text)
    text = _ACCION_CORCHETE.sub(" ", text)
    return text


def _parece_nombre(texto: str) -> bool:
    """True si `texto` puede ser el nombre de un PNJ y no dialogo normal."""
    palabras = texto.split()
    if not 1 <= len(palabras) <= 4:
        return False
    for palabra in palabras:
        limpia = palabra.strip("'.-")
        if not limpia:
            return False
        if limpia.lower() in _PARTICULAS:
            continue
        if not limpia[0].isupper():
            return False
    return True


def _strip_speaker_prefix(text: str) -> str:
    """Quita "Lydia: " del principio, solo si es de verdad un nombre."""
    match = _PREFIJO_HABLANTE.match(text)
    if match and _parece_nombre(match.group("nombre")):
        return text[match.end() :]
    return text


def _tidy(text: str) -> str:
    text = _SALTOS.sub(" ", text)
    text = _ESPACIOS.sub(" ", text)
    text = re.sub(r"\s+([,.;:!?…])", r"\1", text)
    text = re.sub(r"([¿¡])\s+", r"\1", text)
    return text.strip().strip('"').strip()


def sanitize_for_tts(
    text: str,
    *,
    strip_actions: bool = True,
    strip_speaker_prefix: bool = True,
) -> str:
    """Devuelve una linea de dialogo apta para sintesis de voz."""
    if not text:
        return ""

    # Orden importante: negritas -> acotaciones -> resto del markdown.
    cleaned = _markdown_previo(text)
    if strip_actions:
        cleaned = strip_stage_directions(cleaned)
    cleaned = _markdown_posterior(cleaned)
    # Los asteriscos sueltos que sobrevivan no aportan nada al TTS.
    cleaned = cleaned.replace("*", " ").replace("_", " ")
    cleaned = _EMOJI.sub(" ", cleaned)
    cleaned = cleaned.replace("—", ", ").replace("–", ", ")
    cleaned = _tidy(cleaned)
    if strip_speaker_prefix:
        cleaned = _strip_speaker_prefix(cleaned)
    return cleaned.strip()


def split_sentences(text: str) -> list[str]:
    """Parte el texto en frases, sin cortar en abreviaturas comunes."""
    if not text.strip():
        return []

    frases: list[str] = []
    inicio = 0
    for match in _FIN_FRASE.finditer(text):
        fin = match.end()
        anterior = text[inicio:fin]
        palabra = re.search(r"([\wÁÉÍÓÚÜÑáéíóúüñ]+)\.?$", anterior.rstrip("\"'»)]"))
        if palabra and palabra.group(1).lower() in _ABREVIATURAS:
            continue
        frase = anterior.strip()
        if frase:
            frases.append(frase)
        inicio = fin
    resto = text[inicio:].strip()
    if resto:
        frases.append(resto)
    return frases


def limit_sentences(text: str, max_sentences: int) -> str:
    """Recorta la respuesta a las primeras `max_sentences` frases."""
    if max_sentences <= 0:
        return text
    frases = split_sentences(text)
    if len(frases) <= max_sentences:
        return text
    return " ".join(frases[:max_sentences]).strip()


class SentenceStreamSanitizer:
    """Sanea una respuesta en streaming sin romper frases por la mitad.

    Mantella reproduce el audio frase a frase, asi que el gateway acumula
    hasta cerrar una frase, la limpia y la emite entera. `flush()` devuelve
    lo que quede pendiente al terminar el stream.
    """

    def __init__(self, *, strip_actions: bool = True, max_sentences: int = 0) -> None:
        self._strip_actions = strip_actions
        self._max_sentences = max_sentences
        self._buffer = ""
        self._emitidas = 0
        self._primera = True

    @property
    def finished(self) -> bool:
        """True cuando ya se alcanzo el limite de frases configurado."""
        return self._max_sentences > 0 and self._emitidas >= self._max_sentences

    def feed(self, chunk: str) -> str:
        """Anade texto y devuelve las frases completas ya saneadas."""
        if self.finished or not chunk:
            return ""
        self._buffer += chunk

        salida: list[str] = []
        while True:
            match = _FIN_FRASE_STREAM.search(self._buffer)
            if not match:
                break
            bruto, self._buffer = self._buffer[: match.end()], self._buffer[match.end() :]
            frase = self._emit(bruto)
            if frase:
                salida.append(frase)
            if self.finished:
                self._buffer = ""
                break
        return "".join(salida)

    def flush(self) -> str:
        """Emite el resto del buffer al cerrarse el stream."""
        if self.finished:
            self._buffer = ""
            return ""
        pendiente, self._buffer = self._buffer, ""
        return self._emit(pendiente)

    def _emit(self, bruto: str) -> str:
        limpio = sanitize_for_tts(
            bruto,
            strip_actions=self._strip_actions,
            strip_speaker_prefix=self._primera,
        )
        if not limpio:
            return ""
        # Solo se separa con espacio si ya se habia emitido algo antes.
        prefijo = "" if self._primera else " "
        self._primera = False
        self._emitidas += 1
        return prefijo + limpio
