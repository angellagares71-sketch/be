# Configuración

Todos los ajustes del gateway viven en el fichero `.env` de la raíz. El
ejemplo comentado está en
[`config/gateway.env.ejemplo`](../config/gateway.env.ejemplo).

Los cambios requieren reiniciar el gateway (Ctrl+C y volver a arrancarlo).

---

## Proveedor y modelo

| Variable | Por defecto | Qué hace |
|---|---|---|
| `MANTELLA_PROVIDER` | `openrouter` | `openrouter`, `openai`, `ollama`, `lmstudio`, `koboldcpp` o `custom` |
| `MANTELLA_API_KEY` | *(vacío)* | Clave del proveedor. Obligatoria en `openrouter` y `openai` |
| `MANTELLA_API_KEY_FILE` | *(vacío)* | Alternativa: ruta a un fichero con la clave (sirve el `GPT_SECRET_KEY.txt` de Mantella) |
| `MANTELLA_MODEL` | según proveedor | Modelo a usar cuando Mantella no impone uno |
| `MANTELLA_BASE_URL` | según proveedor | URL del proveedor. Obligatoria con `custom` |

URLs por defecto de cada proveedor:

| Proveedor | URL | ¿Clave? | Modelo por defecto |
|---|---|---|---|
| `openrouter` | `https://openrouter.ai/api/v1` | sí | `mistralai/mistral-nemo` |
| `openai` | `https://api.openai.com/v1` | sí | `gpt-4o-mini` |
| `ollama` | `http://localhost:11434/v1` | no | `llama3.1:8b` |
| `lmstudio` | `http://localhost:1234/v1` | no | `local-model` |
| `koboldcpp` | `http://localhost:5001/v1` | no | `koboldcpp` |
| `custom` | *(la que pongas)* | no | *(el que pongas)* |

### Quién decide el modelo

El `model` del `config.ini` de Mantella tiene prioridad, **salvo** que esté
vacío o valga `mantella`, `gateway`, `default` o `auto`. En ese caso manda
`MANTELLA_MODEL`. Poner `model = mantella` en el `config.ini` es lo más
cómodo: cambias de modelo editando solo el `.env`.

---

## Servidor local

| Variable | Por defecto | Qué hace |
|---|---|---|
| `MANTELLA_HOST` | `127.0.0.1` | Interfaz de escucha |
| `MANTELLA_PORT` | `8000` | Puerto. Debe coincidir con el `llm_api` del `config.ini` |

Si cambias el puerto, actualiza también el `config.ini` de Mantella.

Deja `MANTELLA_HOST` en `127.0.0.1` salvo que juegues desde otro equipo: con
`0.0.0.0` el gateway queda expuesto a tu red local **sin autenticación**, y
cualquiera en esa red podría gastar tu clave de API.

---

## Adaptación al motor de voz

Aquí está el valor real del gateway. El TTS lee literalmente lo que le llega.

| Variable | Por defecto | Qué hace |
|---|---|---|
| `MANTELLA_SANITIZE` | `true` | Interruptor general de la limpieza |
| `MANTELLA_STRIP_ACTIONS` | `true` | Elimina acotaciones de rol |
| `MANTELLA_MAX_SENTENCES` | `0` | Corta a N frases. `0` = sin límite |

Con `MANTELLA_SANITIZE=true` se quitan:

- Negritas y cursivas (`**así**`, `_así_`) dejando el texto.
- Encabezados, citas, viñetas y listas numeradas.
- Bloques de código y `código en línea`.
- Enlaces: `[Riften](https://...)` → `Riften`.
- Emojis y símbolos que el TTS no sabe pronunciar.
- El nombre del hablante al principio (`Lydia: hola` → `hola`), solo cuando
  de verdad parece un nombre propio.
- Rayas y guiones largos, convertidos en pausas con coma.

Con `MANTELLA_STRIP_ACTIONS=true` se eliminan además las acotaciones:
`*se cruza de brazos*`, `(suspira)`, `[mira al suelo]`.

> **Cuidado con `MANTELLA_STRIP_ACTIONS`.** Borra *todo* lo que vaya entre
> asteriscos, paréntesis o corchetes, incluida una cursiva de énfasis normal
> (`es *muy* peligroso` pierde el «muy»). En la práctica compensa: los modelos
> usan esa notación casi siempre para acciones. Si prefieres que se lean, pon
> `false` y solo se quitarán los símbolos, no el texto.

### Ejemplo

Respuesta cruda del modelo:

```
*se gira lentamente* **Bienvenido** a Riften. No te fíes de nadie 😉
```

Lo que recibe Mantella:

```
Bienvenido a Riften. No te fíes de nadie
```

### Streaming

En streaming el gateway acumula hasta cerrar una frase y la manda entera, en
lugar de reenviar fragmentos sueltos. Es lo que necesita Mantella, que
sintetiza frase a frase. Una frase no se cierra hasta que llega un espacio
después de la puntuación, así que `Sr. Black` no se parte por la mitad.

---

## Generación

| Variable | Por defecto | Qué hace |
|---|---|---|
| `MANTELLA_TEMPERATURE` | *(sin fijar)* | Creatividad. `0.8`–`1.0` va bien para rol |
| `MANTELLA_TOP_P` | *(sin fijar)* | Muestreo por núcleo |
| `MANTELLA_MAX_TOKENS` | *(sin fijar)* | Longitud máxima de la respuesta |
| `MANTELLA_SYSTEM_PREFIX` | *(vacío)* | Mensaje de sistema añadido al principio de cada petición |

Estos valores **solo se aplican si Mantella no manda el suyo**: nunca pisan lo
que llega en la petición.

`MANTELLA_SYSTEM_PREFIX` es la forma de forzar idioma o tono sin tocar los
prompts internos de Mantella:

```ini
MANTELLA_SYSTEM_PREFIX=Responde siempre en español, en una o dos frases cortas, sin describir acciones.
```

---

## Robustez

| Variable | Por defecto | Qué hace |
|---|---|---|
| `MANTELLA_TIMEOUT` | `60` | Segundos de espera por respuesta |
| `MANTELLA_CONNECT_TIMEOUT` | `10` | Segundos para establecer la conexión |
| `MANTELLA_MAX_RETRIES` | `2` | Reintentos ante fallos transitorios |
| `MANTELLA_RETRY_BACKOFF` | `1.0` | Segundos base; la espera se duplica en cada intento |

Se reintentan los códigos 408, 409, 425, 429, 500, 502, 503 y 504, y los
fallos de red. En streaming solo se reintenta **antes** del primer byte: una
vez empezada la respuesta, repetirla duplicaría texto ya hablado.

Con modelos locales lentos sube `MANTELLA_TIMEOUT` a `120` o más.

---

## Diagnóstico

| Variable | Por defecto | Qué hace |
|---|---|---|
| `MANTELLA_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

`DEBUG` registra cada petición y cada fragmento SSE descartado.

El endpoint `GET /health` devuelve la configuración efectiva:

```json
{
  "status": "ok",
  "provider": "openrouter",
  "model": "mistralai/mistral-nemo",
  "api_key_configurada": true,
  "sanitize_output": true,
  "max_sentences": 0
}
```

Nunca expone la clave, solo si hay una configurada.

---

## Endpoints

| Método | Ruta | Para qué |
|---|---|---|
| `GET` | `/health` | Estado y configuración efectiva |
| `GET` | `/v1/models` | Catálogo de modelos del proveedor |
| `POST` | `/v1/chat/completions` | El que usa Mantella. Con y sin streaming |
