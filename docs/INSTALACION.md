# Instalación paso a paso

Guía completa desde cero. Si ya tienes Mantella funcionando y solo quieres
añadir el gateway, salta al [paso 4](#4-instalar-el-gateway).

> **Sobre las versiones de Mantella.** Los nombres de las secciones del
> `config.ini` y algunos requisitos han cambiado entre versiones. Cuando esta
> guía y la documentación oficial de tu versión no coincidan, **haz caso a la
> oficial**: guíate por el *nombre de la clave*, que sí se ha mantenido.

---

## 1. Requisitos del juego

| Componente | Dónde |
|---|---|
| Skyrim Special Edition / Anniversary / VR | Steam |
| SKSE64 (o SKSEVR) | <https://skse.silverlock.org/> |
| SkyUI | Nexus Mods |
| PapyrusUtil SE | Nexus Mods |
| Address Library for SKSE Plugins | Nexus Mods |

Instálalos con **Mod Organizer 2** o **Vortex**, no a mano. Comprueba que
Skyrim arranca desde `skse64_loader.exe` antes de seguir.

## 2. Instalar el mod Mantella

1. Descarga **Mantella** de Nexus Mods e instálalo con tu gestor de mods.
2. Descarga **Mantella Software** (el paquete aparte con el ejecutable) y
   descomprímelo en una carpeta *fuera* de la de Skyrim, por ejemplo
   `C:\Mantella\MantellaSoftware`.
3. Arráncalo una vez para que genere su `config.ini`, y ciérralo.

## 3. Motor de voz

Elige uno:

- **xVASynth** — ligero, funciona en CPU, es la opción segura para empezar.
- **XTTS** — suena bastante mejor, pero quiere GPU con VRAM suficiente.

Instálalo y anota su carpeta: hará falta en el `config.ini` y en el script de
diagnóstico.

## 4. Instalar el gateway

Clona o descarga este repositorio y ejecuta el instalador. Crea un entorno
virtual, instala las dependencias y te deja un `.env` a partir del ejemplo.

**Windows** (PowerShell):

```powershell
cd C:\ruta\al\repositorio
powershell -ExecutionPolicy Bypass -File scripts\instalar.ps1
```

**Linux / macOS:**

```bash
cd /ruta/al/repositorio
./scripts/instalar.sh
```

Si te dice que no encuentra Python, instálalo desde
<https://www.python.org/downloads/> marcando **«Add python.exe to PATH»**.

## 5. Elegir proveedor y modelo

Abre el `.env` que acaba de crearse en la raíz del repositorio.

### Opción A — OpenRouter (recomendada para empezar)

Da acceso a muchos modelos con una sola clave, y tiene opciones baratas.
Saca la clave en <https://openrouter.ai/keys>.

```ini
MANTELLA_PROVIDER=openrouter
MANTELLA_API_KEY=sk-or-v1-...tu-clave...
MANTELLA_MODEL=mistralai/mistral-nemo
```

### Opción B — Local con Ollama (sin coste ni conexión)

Instala [Ollama](https://ollama.com), descarga un modelo y déjalo corriendo:

```bash
ollama pull llama3.1:8b
```

```ini
MANTELLA_PROVIDER=ollama
MANTELLA_MODEL=llama3.1:8b
```

No hace falta clave. LM Studio (`lmstudio`) y KoboldCpp (`koboldcpp`)
funcionan igual, cada uno en su puerto por defecto.

### Opción C — OpenAI

```ini
MANTELLA_PROVIDER=openai
MANTELLA_API_KEY=sk-...tu-clave...
MANTELLA_MODEL=gpt-4o-mini
```

El resto de ajustes están comentados en
[`config/gateway.env.ejemplo`](../config/gateway.env.ejemplo) y explicados en
[CONFIGURACION.md](CONFIGURACION.md).

## 6. Arrancar el gateway

**Windows:**

```powershell
powershell -ExecutionPolicy Bypass -File scripts\arrancar.ps1
```

**Linux / macOS:**

```bash
./scripts/arrancar.sh
```

Deberías ver algo así:

```
Gateway listo en http://127.0.0.1:8000/v1 -> https://openrouter.ai/api/v1 (openrouter)
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Deja esa ventana abierta mientras juegas.** Para comprobarlo desde otra:

```bash
curl http://localhost:8000/health
```

### Acceso directo en el Escritorio (opcional)

Para no tener que abrir PowerShell cada vez:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\crear-acceso-directo.ps1
```

Deja un **Skyrim IA** en tu Escritorio que arranca el gateway con doble clic.
La ventana se queda abierta, que es justo lo que hace falta mientras juegas.

| Opcion | Para que |
|---|---|
| `-Forzar` | Sobrescribe uno que ya exista |
| `-Nombre "Otro"` | Cambia el nombre del acceso directo |
| `-Destino "C:\ruta"` | Lo crea en otra carpeta en vez del Escritorio |

Detecta el Escritorio real con `[Environment]::GetFolderPath("Desktop")`, asi
que funciona aunque OneDrive lo haya movido. Si por politicas del sistema no
puede crear el `.lnk`, deja un `.cmd` equivalente, que Windows lanza igual.

## 7. Apuntar Mantella al gateway

Abre el `config.ini` de Mantella Software y cambia:

```ini
llm_api = http://localhost:8000/v1
model = mantella
```

Poner `model = mantella` hace que el modelo lo decida el `.env` del gateway,
así que en adelante cambias de modelo sin volver a tocar este fichero.

Revisa también que `skyrim_folder` y `skyrim_mod_folder` apunten a tus
carpetas reales. El resto de claves recomendadas están en
[`config/mantella-config-fragmento.ini`](../config/mantella-config-fragmento.ini).

> Algunas versiones de Mantella se niegan a arrancar si no existe
> `GPT_SECRET_KEY.txt`. Créalo con cualquier texto no vacío (`sk-local` vale):
> la clave de verdad la guarda el gateway en su `.env`.

## 8. Comprobar la instalación

Con el gateway arrancado:

```bash
python scripts/comprobar.py ^
  --skyrim "C:\Program Files (x86)\Steam\steamapps\common\Skyrim Special Edition" ^
  --config "C:\Mantella\MantellaSoftware\config.ini" ^
  --xvasynth "C:\Program Files (x86)\Steam\steamapps\common\xVASynth"
```

No pares hasta que salga **0 fallos**. Los `[AVISO]` son opcionales.

## 9. Jugar

1. Gateway arrancado.
2. Mantella Software arrancado.
3. Skyrim desde `skse64_loader.exe` (**no** desde Steam).
4. En el juego: hechizo Mantella sobre un PNJ y a hablar.

Si algo falla, [SOLUCION-PROBLEMAS.md](SOLUCION-PROBLEMAS.md).
