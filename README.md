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

**Windows** (PowerShell, en la carpeta del repositorio):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\instalar.ps1
notepad .env                                                   # pon tu clave
powershell -ExecutionPolicy Bypass -File scripts\arrancar.ps1
```

Para dejarlo a un doble clic, crea un acceso directo **Skyrim IA** en el
Escritorio:

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
python scripts/comprobar.py
```

Busca Skyrim y el `config.ini` de Mantella por su cuenta, así que normalmente
no hace falta darle ninguna ruta. Revisa Python, Skyrim, SKSE, los mods
requeridos, el `config.ini` y el propio gateway, y marca cada punto como
`[OK]`, `[AVISO]` o `[FALLO]`.

Si no encuentras la carpeta de Mantella, esto te dice dónde está:

```bash
python scripts/comprobar.py --buscar
```

Y si prefieres darle las rutas a mano, siguen valiendo `--skyrim` y `--config`.

### Sin tocar la consola

En Windows hay dos ficheros en la raíz del repositorio que hacen lo mismo con
un **doble clic**, y dejan el resultado en un `.txt` al lado:

| Doble clic en | Qué hace |
|---|---|
| `Jugar.bat` | Arranca el gateway y el juego |
| `Buscar Mantella.bat` | Busca Skyrim y el `config.ini` y enseña las rutas |
| `Comprobar instalacion.bat` | Diagnóstico completo |

Solo necesitan Python instalado — no hace falta ni el entorno virtual ni
descargar nada más, porque el diagnóstico usa únicamente la biblioteca
estándar. Si no tienes `git`, puedes bajar el repositorio como ZIP desde
GitHub (botón verde **Code** → **Download ZIP**), descomprimirlo y hacer doble
clic igual.

## Uso diario

En Windows, doble clic en `Jugar.bat`: arranca el gateway en su ventana, espera
a que responda y lanza Skyrim con SKSE. Solo queda arrancar Mantella Software.

A mano, o fuera de Windows:

```bash
python scripts/jugar.py              # gateway + juego
python scripts/jugar.py --solo-gateway
```

Y el orden completo, si prefieres hacerlo paso a paso:

1. Arranca el gateway (`scripts/arrancar`) y deja la ventana abierta.
2. Arranca Mantella como siempre.
3. Arranca Skyrim **desde SKSE** (`skse64_loader.exe`), no desde Steam.
4. Dentro del juego, lanza el hechizo Mantella sobre un PNJ y habla.

## Estructura

| Ruta | Qué es |
|---|---|
| `server/mantella_gateway/` | El servidor: configuración, saneado de texto, cliente del proveedor y app HTTP |
| `server/tests/` | 79 pruebas, sin salida a la red |
| `scripts/instalar.*` | Entorno virtual, dependencias y `.env` |
| `scripts/arrancar.*` | Arranca el gateway |
| `scripts/crear-acceso-directo.ps1` | Crea el acceso directo «Skyrim IA» en el Escritorio |
| `assets/` | Icono del acceso directo y el script que lo genera |
| `scripts/comprobar.py` | Diagnóstico de la instalación, localiza Skyrim y Mantella solo |
| `scripts/jugar.py` | Arranca el gateway, espera a que responda y lanza Skyrim con SKSE |
| `*.bat` | Los mismos diagnósticos, a doble clic en Windows |
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
python -m pytest        # 79 pruebas, todas offline
```
