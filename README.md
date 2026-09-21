# Mantella Gateway — Skyrim con IA

Servidor local que conecta el mod [Mantella](https://www.nexusmods.com/skyrimspecialedition/mods/98631)
(PNJs de Skyrim con voz e IA) con el proveedor de modelos que tú elijas, y
que además **limpia el texto antes de que lo lea el motor de voz**.

```
Skyrim + Mantella  ──►  este gateway  ──►  OpenRouter / OpenAI / Ollama / LM Studio
   (localhost:8000)      sanea el texto        el modelo que quieras
```

## Por qué un gateway en medio

Mantella habla el dialecto de la API de OpenAI y le da igual con quién habla,
así que basta con apuntarlo a `http://localhost:8000/v1`. A cambio ganas:

- **Texto limpio para el TTS.** El motor de voz lee *literalmente* lo que
  recibe: pronuncia los asteriscos, los guiones de lista y el markdown. El
  gateway quita `**negritas**`, acotaciones de rol (`*se cruza de brazos*`,
  `(suspira)`, `[mira al suelo]`), emojis, enlaces y bloques de código.
- **Frases completas en streaming.** Mantella sintetiza frase a frase; el
  gateway acumula hasta cerrar una frase en vez de soltar fragmentos sueltos.
- **Cambiar de modelo sin tocar Skyrim.** El proveedor y el modelo viven en un
  `.env`; el juego no se entera.
- **Reintentos.** Los 429 y los 5xx del proveedor se reintentan solos, con
  espera creciente, en lugar de cortarte la conversación a media partida.
- **Límite de frases y prefijo de sistema** para acortar respuestas o forzar
  idioma sin editar los prompts internos de Mantella.

## Instalación rápida

Requisitos previos: Skyrim SE/AE/VR, SKSE, el mod Mantella ya instalado y
Python 3.10 o superior. La guía completa está en
[`docs/INSTALACION.md`](docs/INSTALACION.md).

### Windows: un doble clic

Haz doble clic en **`INSTALAR-SKYRIM-IA.cmd`**. Instala las dependencias, te
pregunta por el proveedor y la clave, comprueba que responde, crea el acceso
directo del Escritorio y te ofrece arrancar.

Si el acceso directo **Skyrim IA** no esta en tu Escritorio, o lo borraste sin
querer, haz doble clic en **`CREAR-ACCESO-DIRECTO.cmd`**: lo vuelve a poner sin
reinstalar nada.

Después solo queda una línea en el `config.ini` de Mantella:

```ini
llm_api = http://localhost:8000/v1
```

### Paso a paso, si lo prefieres

**Windows** (PowerShell, en la carpeta del repositorio):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\instalar.ps1
notepad .env                                                   # pon tu clave
powershell -ExecutionPolicy Bypass -File scripts\arrancar.ps1
```

Para dejarlo a un doble clic, crea un acceso directo **Skyrim IA** en el
Escritorio (o haz doble clic en `CREAR-ACCESO-DIRECTO.cmd`, que hace esto
mismo):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\crear-acceso-directo.ps1
```

**Linux / macOS:**

```bash
./scripts/instalar.sh
$EDITOR .env
./scripts/arrancar.sh
```

Después, en el `config.ini` de Mantella cambia una línea:

```ini
llm_api = http://localhost:8000/v1
```

Las demás claves que conviene tocar están en
[`config/mantella-config-fragmento.ini`](config/mantella-config-fragmento.ini).

## Comprobar que todo está bien

```bash
python scripts/comprobar.py \
  --skyrim "C:/Program Files (x86)/Steam/steamapps/common/Skyrim Special Edition" \
  --config "C:/ruta/a/MantellaSoftware/config.ini"
```

Revisa Python, Skyrim, SKSE, los mods requeridos, el `config.ini` y el propio
gateway, y marca cada punto como `[OK]`, `[AVISO]` o `[FALLO]`.

## Uso diario

1. Arranca el gateway (`scripts/arrancar`) y deja la ventana abierta.
2. Arranca Mantella como siempre.
3. Arranca Skyrim **desde SKSE** (`skse64_loader.exe`), no desde Steam.
4. Dentro del juego, lanza el hechizo Mantella sobre un PNJ y habla.

## Estructura

| Ruta | Qué es |
|---|---|
| `server/mantella_gateway/` | El servidor: configuración, saneado de texto, cliente del proveedor y app HTTP |
| `server/tests/` | 56 pruebas, sin salida a la red |
| `scripts/instalar.*` | Entorno virtual, dependencias y `.env` |
| `INSTALAR-SKYRIM-IA.cmd` | Instalación completa de un doble clic (Windows) |
| `CREAR-ACCESO-DIRECTO.cmd` | Vuelve a poner el acceso directo en el Escritorio, de un doble clic (Windows) |
| `scripts/configurar.ps1` | Pregunta proveedor y clave, y escribe el `.env` |
| `scripts/probar-proveedor.py` | Manda una petición real para validar clave y modelo |
| `scripts/arrancar.*` | Arranca el gateway |
| `scripts/crear-acceso-directo.ps1` | Crea el acceso directo «Skyrim IA» en el Escritorio |
| `assets/` | Icono del acceso directo y el script que lo genera |
| `scripts/comprobar.py` | Diagnóstico de la instalación |
| `config/gateway.env.ejemplo` | Todos los ajustes, comentados |
| `config/mantella-config-fragmento.ini` | Las claves a cambiar en el `config.ini` de Mantella |
| `docs/` | Instalación, configuración y solución de problemas |

## Documentación

- [Instalación paso a paso](docs/INSTALACION.md)
- [Configuración](docs/CONFIGURACION.md)
- [Solución de problemas](docs/SOLUCION-PROBLEMAS.md)

## Desarrollo

```bash
cd server
python -m pytest        # 56 pruebas, todas offline
```
