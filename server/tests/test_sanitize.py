"""Pruebas del saneado de texto para el motor de voz."""

import pytest

from mantella_gateway.sanitize import (
    SentenceStreamSanitizer,
    limit_sentences,
    sanitize_for_tts,
    split_sentences,
)


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("**Hola** viajero", "Hola viajero"),
        ("*se cruza de brazos* Que quieres?", "Que quieres?"),
        ("(suspira) Otro dia mas.", "Otro dia mas."),
        ("[mira al suelo] Vete.", "Vete."),
        ("# Titulo\nTexto normal", "Titulo Texto normal"),
        ("- primero\n- segundo", "primero segundo"),
        ("Mira `esto` de cerca", "Mira esto de cerca"),
        ("Ve a [Riften](https://ejemplo.com) ya", "Ve a Riften ya"),
        ("Lydia: Te sigo, mi thane.", "Te sigo, mi thane."),
        ("Vale 😀 gracias", "Vale gracias"),
        ("Espera —tengo algo— para ti", "Espera, tengo algo, para ti"),
        ("> Cita antigua", "Cita antigua"),
        ("", ""),
        ("   ", ""),
    ],
)
def test_sanitize_for_tts(entrada, esperado):
    assert sanitize_for_tts(entrada) == esperado


def test_las_acciones_se_conservan_si_se_pide():
    texto = "*asiente* Claro."
    # Sin quitar acciones los asteriscos igualmente desaparecen, pero el
    # texto de la acotacion se conserva para que lo lea el TTS.
    assert sanitize_for_tts(texto, strip_actions=False) == "asiente Claro."


def test_no_se_pierde_el_dialogo_entre_acciones():
    texto = "*se gira* Bienvenido a Riften. *escupe* No te fies de nadie."
    assert sanitize_for_tts(texto) == "Bienvenido a Riften. No te fies de nadie."


def test_bloque_de_codigo_eliminado():
    texto = "Toma esto:\n```python\nprint('hola')\n```\nY vete."
    assert sanitize_for_tts(texto) == "Toma esto: Y vete."


def test_prefijo_de_hablante_solo_al_principio():
    texto = "Guardia: recuerdo cuando yo era como tu: aventurero."
    assert sanitize_for_tts(texto) == "recuerdo cuando yo era como tu: aventurero."


def test_split_sentences_respeta_abreviaturas():
    assert split_sentences("Habla con el Sr. Black. Luego vuelve.") == [
        "Habla con el Sr. Black.",
        "Luego vuelve.",
    ]


def test_split_sentences_con_signos_y_comillas():
    frases = split_sentences('Quien anda ahi? "Nadie." Sigue tu camino!')
    assert frases == ['Quien anda ahi?', '"Nadie."', 'Sigue tu camino!']


def test_limit_sentences():
    texto = "Una. Dos. Tres. Cuatro."
    assert limit_sentences(texto, 2) == "Una. Dos."
    assert limit_sentences(texto, 0) == texto
    assert limit_sentences(texto, 10) == texto


class TestStreamSanitizer:
    def test_emite_frases_completas(self):
        s = SentenceStreamSanitizer()
        assert s.feed("Hola ") == ""
        assert s.feed("viaje") == ""
        salida = s.feed("ro. ")
        assert salida == "Hola viajero."
        assert s.feed("Que tal?") == ""
        assert s.flush() == " Que tal?"

    def test_reconstruye_el_texto_completo(self):
        s = SentenceStreamSanitizer()
        trozos = ["*asiente* ", "Bienve", "nido a ", "Riften. ", "No te ", "fies de nadie."]
        salida = "".join(s.feed(t) for t in trozos) + s.flush()
        assert salida == "Bienvenido a Riften. No te fies de nadie."

    def test_respeta_el_limite_de_frases(self):
        s = SentenceStreamSanitizer(max_sentences=2)
        salida = s.feed("Una. Dos. Tres. Cuatro.")
        assert salida == "Una. Dos."
        assert s.finished is True
        assert s.feed(" Cinco.") == ""
        assert s.flush() == ""

    def test_flush_vacio_no_produce_nada(self):
        s = SentenceStreamSanitizer()
        assert s.flush() == ""

    def test_una_acotacion_sola_no_cuenta_como_frase(self):
        s = SentenceStreamSanitizer()
        assert s.feed("*gruñe.* ") == ""
        assert s.feed("Largo de aqui.") == ""
        assert s.flush() == "Largo de aqui."
