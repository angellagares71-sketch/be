# Solución de problemas

Empieza siempre por el diagnóstico, con el gateway arrancado:

```bash
python scripts/comprobar.py --skyrim "C:\...\Skyrim Special Edition" --config "C:\...\config.ini"
```

---

## El gateway no arranca

### `Error de configuracion: El proveedor 'openrouter' necesita una clave de API`

Falta la clave en el `.env`. Ponla en `MANTELLA_API_KEY`, o cambia a un
proveedor local (`MANTELLA_PROVIDER=ollama`), que no la necesita.

### `Error de configuracion: MANTELLA_BASE_URL debe empezar por http://`

Con `MANTELLA_PROVIDER=custom` hay que dar la URL completa, incluido el
esquema y el `/v1`: `http://localhost:8080/v1`, no `localhost:8080`.

### `no hay entorno virtual. Ejecuta antes: scripts/instalar`

No se ha ejecutado el instalador, o se borró `.venv`. Vuelve a lanzarlo.

### `[Errno 98] Address already in use` / `error while attempting to bind`

Ese puerto ya está ocupado, casi siempre por otro gateway abierto en otra
ventana. Ciérralo, o cambia `MANTELLA_PORT` en el `.env` **y** el `llm_api`
del `config.ini` para que coincidan.

### PowerShell: `no se puede cargar porque la ejecución de scripts está deshabilitada`

Arranca los scripts con el prefijo que los salta:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\arrancar.ps1
```

---

## Mantella no habla con el gateway

### El diagnóstico dice `El gateway no responde`

1. ¿Está la ventana del gateway abierta? Tiene que quedarse corriendo.
2. Comprueba a mano: `curl http://localhost:8000/health`.
3. ¿Coinciden el puerto del `.env` y el del `--gateway`?

### Mantella da error de conexión al hablar con un PNJ

Casi siempre es el `llm_api` del `config.ini`. Repasa:

- Que ponga `http://localhost:8000/v1` — **con** `/v1` y **sin** barra final.
- Que el puerto sea el mismo que `MANTELLA_PORT`.
- Que sea `http`, no `https`: el gateway es local y no usa TLS.

### Mantella se queja de que falta `GPT_SECRET_KEY.txt`

Algunas versiones exigen que el fichero exista aunque no vaya a usarlo. Créalo
junto al `config.ini` con cualquier texto no vacío (`sk-local`). La clave de
verdad la guarda el gateway en su `.env`.

### El acceso directo del Escritorio no hace nada

Abre PowerShell en la carpeta del repositorio y lanza `scripts\arrancar.ps1`
a mano: el error que salga es el mismo que se traga la ventana al cerrarse.
Lo habitual es que falte el entorno virtual (ejecuta `scripts\instalar.ps1`)
o la clave en el `.env`.

Si moviste la carpeta del repositorio despues de crear el acceso directo, las
rutas que guarda ya no valen. Vuelve a generarlo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\crear-acceso-directo.ps1 -Forzar
```

---

## Errores del proveedor

El gateway propaga el código tal cual, así que el mensaje dice mucho.

| Código | Qué pasa | Qué hacer |
|---|---|---|
| `401` | Clave inválida o caducada | Regenera la clave y actualiza `MANTELLA_API_KEY` |
| `402` | Sin saldo (típico de OpenRouter) | Recarga, o pásate a un modelo gratuito o local |
| `404` | El modelo no existe con ese nombre | Comprueba el identificador exacto en `curl http://localhost:8000/v1/models` |
| `429` | Demasiadas peticiones | El gateway ya reintenta; sube `MANTELLA_MAX_RETRIES` o baja el ritmo |
| `504` | No se pudo contactar | Revisa tu conexión, o que Ollama/LM Studio estén corriendo |

Con un proveedor local, un `504` casi siempre significa que el servidor de
modelos no está arrancado. Verifícalo:

```bash
curl http://localhost:11434/v1/models     # Ollama
curl http://localhost:1234/v1/models      # LM Studio
```

---

## Problemas de voz y texto

### El PNJ pronuncia «asterisco» o lee símbolos raros

El saneado está desactivado. Pon `MANTELLA_SANITIZE=true` en el `.env` y
reinicia el gateway.

### Se pierden palabras entre asteriscos que sí quería oír

`MANTELLA_STRIP_ACTIONS=true` borra todo lo que va entre asteriscos,
paréntesis o corchetes, incluida una cursiva de énfasis. Pon `false`: se
quitarán los símbolos pero se conservará el texto.

### Las respuestas son larguísimas

Tres frenos, combinables:

1. `MANTELLA_MAX_SENTENCES=2` en el `.env`.
2. `max_response_sentences = 2` en el `config.ini`.
3. `MANTELLA_MAX_TOKENS=150`.

Y si aun así se enrolla, añade instrucción explícita:

```ini
MANTELLA_SYSTEM_PREFIX=Responde en una o dos frases cortas como maximo.
```

### El PNJ contesta en inglés

El modelo ignora el idioma del prompt. Fuérzalo:

```ini
MANTELLA_SYSTEM_PREFIX=Responde siempre en español.
```

Revisa también el ajuste de idioma del propio Mantella y que el motor de voz
tenga voces en español.

### La voz tarda mucho en salir

- Modelo remoto: prueba uno más rápido (`mistralai/mistral-nemo` va sobrado).
- Modelo local: uno de 7–8B en GPU; los grandes en CPU no dan el ritmo.
- Baja `MANTELLA_MAX_TOKENS`: menos texto que generar y que sintetizar.
- Sube `MANTELLA_TIMEOUT` a `120` si lo que ves son cortes por espera agotada.

### El PNJ no me oye cuando hablo por el micrófono

Primero, descarta lo obvio con el diagnóstico: doble clic en
**`COMPROBAR-MICRO.cmd`**, o bien

```powershell
powershell -ExecutionPolicy Bypass -File scripts\comprobar-microfono.ps1 -Config "C:\ruta\a\config.ini"
```

Revisa los micrófonos que ve Windows, los dos permisos que hacen falta y los
ajustes de micrófono del `config.ini`, y marca cada punto `[OK]`, `[AVISO]` o
`[FALLO]`. No cambia nada: solo mira.

Lo que suele fallar, por orden:

- **El permiso de las aplicaciones de escritorio.** Es el más olvidado: aunque
  el micrófono esté «activado», Windows tiene un segundo interruptor,
  *Permitir que las aplicaciones de escritorio accedan al micrófono*. Mantella
  no es una app de la Store, así que depende de ese. Configuración >
  Privacidad > Micrófono.
- **Windows usa otro micrófono.** Si tienes auriculares, webcam y el de la
  torre, Mantella coge el que Windows tenga por defecto, que no siempre es el
  que te has puesto. Configuración > Sistema > Sonido > Entrada.
- **El micrófono está desactivado en el `config.ini`** de Mantella.
- **El umbral de audio es demasiado alto.** Si tu `config.ini` tiene
  `audio_threshold`, bájalo: con un valor alto, Mantella toma tu voz por
  ruido de fondo y no la transcribe.

Para saber si el fallo es del micrófono o de Mantella, usa el medidor de
Windows: Configuración > Sistema > Sonido > Entrada > *Probar el micrófono*.
Si la barra se mueve al hablar, el micrófono va bien y el problema está dentro
de Mantella — mira su ventana mientras hablas, que ahí sale el mensaje.

Esto es cosa de Mantella, no del gateway: el gateway solo recibe el texto que
Mantella ya ha transcrito, y nunca toca el audio.

---

## Skyrim y el mod

### El hechizo Mantella no aparece

- ¿Arrancaste desde `skse64_loader.exe` y no desde Steam?
- ¿Está `Mantella.esp` activado en el gestor de mods?
- Revisa el orden de carga con LOOT.

### Skyrim se cierra al arrancar

Suele ser incompatibilidad de versiones: SKSE debe coincidir exactamente con
tu versión de Skyrim, y Address Library también. Comprueba las dos.

---

## Reunir información para pedir ayuda

```bash
# Configuración efectiva del gateway (no expone la clave)
curl http://localhost:8000/health

# Diagnóstico completo
python scripts/comprobar.py --skyrim "..." --config "..."
```

Y arranca el gateway con `MANTELLA_LOG_LEVEL=DEBUG` en el `.env` para ver
cada petición en la ventana.

Antes de publicar cualquier registro, **borra tu clave de API** si aparece.
