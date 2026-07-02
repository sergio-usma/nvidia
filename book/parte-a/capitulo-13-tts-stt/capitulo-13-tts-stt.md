# Capítulo 13 — TTS y STT: Procesamiento y Generación de Voz Natural

## Introducción

El Jetson AGX Orin 64GB puede ejecutar pipelines completos de voz — transcripción (STT) y síntesis (TTS) — completamente offline y con calidad comparable a los servicios en la nube. Este capítulo cubre los dos lados del pipeline:

**STT (Speech-to-Text / Transcripción):**
- **faster-whisper** — el motor más rápido, con aceleración CTranslate2
- **whisper.cpp** — via llama.cpp container, eficiente en CPU+GPU
- Diarización de hablantes (¿quién habló cuándo?)
- Timestamps a nivel de palabra (para subtítulos y búsqueda)

**TTS (Text-to-Speech / Síntesis de voz):**
- **kokoro-tts** — voces naturales en español e inglés, API compatible OpenAI
- **piper-tts** — síntesis ultrarrápida, ideal para respuestas cortas
- Comparativa de voces disponibles en español

**Caso de uso principal:** Asistente de voz completamente offline (combinado con el LLM del Jetson). El pipeline completo STT → LLM → TTS puede responder una pregunta en menos de 3 segundos.

**Presupuesto de memoria:**

| Componente | RAM |
|-----------|-----|
| OS base | ~12 GB |
| faster-whisper (modelo large-v3) | ~3 GB |
| kokoro-tts container | ~2 GB |
| piper-tts (CPU, ultraligero) | ~0.5 GB |
| **STT + TTS simultáneos** | **~17.5 GB** — seguros juntos |
| + LLM Qwen3.5-4B (pipeline completo) | +5 GB = ~22.5 GB |

**Modo energético:** 30W para todos los escenarios — STT y TTS son modelos pequeños que no justifican MAXN. Solo activar MAXN si el LLM del pipeline es ≥14B.

---

## 13.1 STT con faster-whisper

### 13.1.1 Comparativa de Motores STT para Español

| Motor | Modelo | Velocidad (ratio vs tiempo real) | Calidad Español | WER* | RAM |
|-------|--------|----------------------------------|-----------------|------|-----|
| faster-whisper | large-v3 | ~5-8× | **Excelente** | ~8% | ~3 GB |
| faster-whisper | medium | ~12-15× | Muy buena | ~12% | ~1.5 GB |
| faster-whisper | small | ~25-30× | Buena | ~18% | ~0.5 GB |
| speaches (faster-whisper) | large-v3 | ~5× | Excelente | ~8% | ~3 GB |
| whisper.cpp (GPU) | large-v3 | ~10× | Excelente | ~8% | ~4 GB |

*WER = Word Error Rate — menor es mejor. Medido con corpus de español latinoamericano.

### 13.1.2 Instalar faster-whisper via Container NVIDIA

```bash
# Descargar el container de faster-whisper para JP 7.2
pwr-30w
docker-on

# Verificar disponibilidad del tag r39.2.0
docker pull dustynv/faster-whisper:r39.2.0 2>/dev/null \
  && echo "[OK] Tag r39.2.0 disponible" \
  || { echo "[REQUIERE VERIFICACIÓN] Tag r39.2.0 no encontrado — verificar en hub.docker.com/r/dustynv/faster-whisper"; \
       docker pull dustynv/faster-whisper:r36.4.0 && echo "Usando tag r36.4.0 como fallback"; }
```

```bash
# Iniciar faster-whisper como servidor HTTP (compatible con OpenAI Whisper API)
docker run --runtime nvidia -d \
  --name faster-whisper \
  --restart no \
  --network host \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  -e WHISPER_MODEL=large-v3 \
  -e WHISPER_DEVICE=cuda \
  -e WHISPER_COMPUTE_TYPE=float16 \
  -e WHISPER_LANGUAGE=es \
  dustynv/faster-whisper:r39.2.0

echo -n "Esperando faster-whisper (~2-3 min descarga del modelo en primera vez)"
until curl -sf http://localhost:8000/v1/audio/transcriptions > /dev/null 2>&1 \
  || curl -sf http://localhost:8000/health > /dev/null 2>&1; do
  echo -n "."; sleep 15
done
echo " [OK] faster-whisper activo en :8000"

# Monitorear el arranque
docker logs faster-whisper --follow &
```

> **NOTA sobre el puerto:** faster-whisper usa el puerto 8000 por defecto, el mismo que vLLM. **No inicie vLLM y faster-whisper simultáneamente** a menos que cambie el puerto de uno de ellos con `-e PORT=8001` o similar. Para pipelines STT→LLM, inicie primero faster-whisper, haga la transcripción, párelo, y luego inicie vLLM.

### 13.1.3 Transcripción de Audio

El método más efectivo para probar faster-whisper es usar **su propia voz** en vez de archivos de prueba genéricos: así verifica que el sistema reconoce su acento y cadencia de habla real.

```bash
# Opción A (recomendada): Grabar su propia voz con el micrófono USB del Jetson
mkdir -p ~/jetson-ai-data/audio

# Verificar que hay micrófono disponible
arecord -l
# Salida esperada (ejemplo):
# **** List of CAPTURE Hardware Devices ****
# card 2: USB [USB Audio Device], device 0: USB Audio [USB Audio]

# Grabar 15 segundos en español (hable con naturalidad, no demasiado rápido)
arecord -D hw:2,0 -f S16_LE -r 16000 -c 1 -d 15 ~/jetson-ai-data/audio/mi_voz.wav
# ⚠ Cambie hw:2,0 por el número de card que aparezca en "arecord -l"
echo "[OK] Audio grabado: ~/jetson-ai-data/audio/mi_voz.wav"

# Verificar el archivo grabado
aplay ~/jetson-ai-data/audio/mi_voz.wav
ls -lh ~/jetson-ai-data/audio/mi_voz.wav
# Esperado: ~480 KB por 15 segundos @ 16kHz mono 16bit
```

```bash
# Opción B: Transferir un audio MP3 de su teléfono via SCP (desde Windows)
# En Windows PowerShell:
# scp C:\Users\TuUsuario\Downloads\reunión.mp3 jetson:~/jetson-ai-data/audio/

# Convertir MP3 a WAV 16kHz (formato óptimo para Whisper)
sudo apt install -y ffmpeg
ffmpeg -i ~/jetson-ai-data/audio/reunion.mp3 \
  -ar 16000 -ac 1 -f wav \
  ~/jetson-ai-data/audio/reunion.wav
```

```bash
# Transcribir audio via API HTTP
curl -s http://localhost:8000/v1/audio/transcriptions \
  -F "file=@$HOME/jetson-ai-data/audio/prueba.wav" \
  -F "model=whisper-1" \
  -F "language=es" \
  -F "response_format=json" \
  | python3 -c "import sys,json; r=json.load(sys.stdin); print('Texto:', r.get('text',''))"
```

```bash
# Con timestamps a nivel de palabra
curl -s http://localhost:8000/v1/audio/transcriptions \
  -F "file=@$HOME/jetson-ai-data/audio/prueba.wav" \
  -F "model=whisper-1" \
  -F "language=es" \
  -F "response_format=verbose_json" \
  -F "timestamp_granularities[]=word" \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('Transcripción:', data.get('text', ''))
print()
print('Timestamps por palabra:')
for seg in data.get('words', []):
    print(f'  [{seg[\"start\"]:.2f}s → {seg[\"end\"]:.2f}s] {seg[\"word\"]}')"
```

```bash
# Salida esperada:
Transcripción: El Jetson AGX Orin tiene sesenta y cuatro gigabytes de memoria unificada.

Timestamps por palabra:
  [0.00s → 0.18s] El
  [0.18s → 0.52s] Jetson
  [0.52s → 0.78s] AGX
  ...
```

### 13.1.4 Diarización de Hablantes (¿Quién Habló Cuándo?)

La diarización identifica automáticamente cuántos hablantes hay en el audio y cuándo habló cada uno. Es esencial para transcripción de reuniones y conferencias.

```bash
# Instalar pyannote.audio para diarización
source ~/venvs/llm/bin/activate
pip install pyannote.audio
```

> **NOTA:** El modelo de diarización `pyannote/speaker-diarization-3.1` es "gated" — requiere:
> 1. Crear cuenta en huggingface.co
> 2. Ir a `huggingface.co/pyannote/speaker-diarization-3.1` y aceptar los términos de uso
> 3. Crear un token en `huggingface.co/settings/tokens` y configurarlo: `export HF_TOKEN="hf_XXXX"` en `~/.bash_aliases`
> ⚠ Reemplaze `hf_XXXX` con su token real de HuggingFace

```python
#!/usr/bin/env python3
"""
diarize_and_transcribe.py — Diarización + transcripción de reuniones
Identifica hablantes y combina con timestamps de Whisper.
"""
import os
import requests
import json
from pathlib import Path
from pyannote.audio import Pipeline as DiarizePipeline
import torch

HF_TOKEN = os.environ.get("HF_TOKEN", "")  # configurar en ~/.bash_aliases: export HF_TOKEN="hf_XXXX"

def diarizar(ruta_audio: str) -> list:
    """Identifica segmentos por hablante."""
    pipeline = DiarizePipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=HF_TOKEN
    )
    pipeline.to(torch.device("cuda"))  # GPU Jetson
    diarizacion = pipeline(ruta_audio)
    segmentos = []
    for turn, _, speaker in diarizacion.itertracks(yield_label=True):
        segmentos.append({
            "inicio": round(turn.start, 2),
            "fin": round(turn.end, 2),
            "hablante": speaker
        })
    return segmentos

def transcribir_segmento(ruta_audio: str, inicio: float, fin: float) -> str:
    """Transcribe un segmento específico del audio (via ffmpeg + faster-whisper API)."""
    import subprocess, tempfile, os

    # Extraer segmento con ffmpeg
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    subprocess.run([
        "ffmpeg", "-y", "-i", ruta_audio,
        "-ss", str(inicio), "-to", str(fin),
        "-f", "wav", "-ar", "16000", "-ac", "1", tmp_path
    ], capture_output=True)

    try:
        resp = requests.post(
            "http://localhost:8000/v1/audio/transcriptions",
            files={"file": ("seg.wav", open(tmp_path, "rb"))},
            data={"model": "whisper-1", "language": "es"},
            timeout=60
        )
        return resp.json().get("text", "").strip()
    finally:
        os.unlink(tmp_path)

def procesar_reunion(ruta_audio: str, salida: str = None) -> list:
    """Pipeline completo: diarizar + transcribir cada segmento."""
    print(f"Diarizando {ruta_audio}...")
    segmentos = diarizar(ruta_audio)
    print(f"Detectados {len(set(s['hablante'] for s in segmentos))} hablantes, {len(segmentos)} segmentos")

    resultado = []
    for i, seg in enumerate(segmentos):
        duracion = seg['fin'] - seg['inicio']
        if duracion < 0.5:  # ignorar segmentos muy cortos
            continue
        print(f"  [{i+1}/{len(segmentos)}] {seg['hablante']} ({seg['inicio']:.1f}s → {seg['fin']:.1f}s)...", end=" ")
        texto = transcribir_segmento(ruta_audio, seg['inicio'], seg['fin'])
        entrada = {**seg, "texto": texto}
        resultado.append(entrada)
        print(f"'{texto[:60]}...' " if len(texto) > 60 else f"'{texto}'")

    salida_path = salida or ruta_audio.replace(".wav", "_diarizado.json")
    with open(salida_path, "w", encoding="utf-8") as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Transcript diarizado: {salida_path}")
    return resultado

def formatear_como_dialogo(resultado: list) -> str:
    """Genera un formato legible tipo guión."""
    lineas = []
    hablante_actual = None
    for seg in resultado:
        if seg['hablante'] != hablante_actual:
            hablante_actual = seg['hablante']
            lineas.append(f"\n**{hablante_actual.replace('SPEAKER_', 'Persona ')}** [{seg['inicio']:.0f}s]:")
        lineas.append(f"  {seg['texto']}")
    return "\n".join(lineas)

if __name__ == "__main__":
    import sys
    ruta = sys.argv[1] if len(sys.argv) > 1 else "~/jetson-ai-data/audio/reunion.wav"
    resultado = procesar_reunion(ruta)
    print("\n" + "═"*60)
    print(formatear_como_dialogo(resultado))
```

```bash
# Ejecutar diarización de una reunión grabada
source ~/venvs/llm/bin/activate
python3 ~/scripts/diarize_and_transcribe.py ~/jetson-ai-data/audio/reunion.wav
```

---

## 13.2 TTS con kokoro-tts

### 13.2.1 Voces Disponibles en Español

kokoro-tts ofrece múltiples voces con diferentes acentos y registros:

| Voice ID | Idioma | Género | Acento | Descripción |
|---------|--------|--------|--------|-------------|
| `es_e` | Español | Masculino | Neutro | Voz masculina clara para presentaciones |
| `es_f` | Español | Femenino | Neutro | Voz femenina natural para asistentes |
| `af_bella` | Inglés | Femenino | Americano | Alta calidad, ideal para contenido bilingüe |
| `af_sarah` | Inglés | Femenino | Americano | Voz calmada, ideal para lecturas largas |
| `bm_george` | Inglés | Masculino | Británico | Profesional, ideal para narración |
| `am_adam` | Inglés | Masculino | Americano | Casual, conversacional |

### 13.2.2 Instalar kokoro-tts

```bash
# Descargar container kokoro-tts
docker pull dustynv/kokoro-tts:r39.2.0 2>/dev/null \
  || { echo "[REQUIERE VERIFICACIÓN] usando fallback r36.4.0"; \
       docker pull dustynv/kokoro-tts:r36.4.0; }

# Iniciar kokoro-tts como servidor API (compatible con OpenAI TTS API)
docker run --runtime nvidia -d \
  --name kokoro-tts \
  --restart no \
  --network host \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  dustynv/kokoro-tts:r39.2.0

echo -n "Esperando kokoro-tts (~60 segundos)"
until curl -sf http://localhost:8880/v1/audio/speech > /dev/null 2>&1 \
  || curl -sf http://localhost:8880/health > /dev/null 2>&1; do
  echo -n "."; sleep 10
done
echo " [OK] kokoro-tts en :8880"

docker logs kokoro-tts --follow &
```

### 13.2.3 Síntesis de Voz con kokoro-tts

```bash
# Test básico de síntesis de voz
mkdir -p ~/jetson-ai-data/audio/tts

# Generar audio en español
curl -s http://localhost:8880/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "kokoro",
    "input": "Bienvenido al Jetson AGX Orin sesenta y cuatro gigabytes. Sistema de inteligencia artificial en el borde completamente offline.",
    "voice": "es_f",
    "speed": 1.0,
    "response_format": "wav"
  }' -o ~/jetson-ai-data/audio/tts/saludo_es.wav

# Verificar que se generó el archivo
ls -lh ~/jetson-ai-data/audio/tts/saludo_es.wav
# Salida esperada: -rw-r--r-- 1 jetson jetson 185K saludo_es.wav

# Reproducir el audio (requiere altavoz o auriculares conectados)
aplay ~/jetson-ai-data/audio/tts/saludo_es.wav
```

```python
#!/usr/bin/env python3
"""
tts_kokoro.py — Síntesis de voz con kokoro-tts
"""
import requests
import subprocess
import tempfile
import os
from pathlib import Path

OUTPUT_DIR = Path.home() / "jetson-ai-data" / "audio" / "tts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

KOKORO_PORT = 8880

VOCES = {
    "es_masculino": "es_e",
    "es_femenino": "es_f",
    "en_bella": "af_bella",
    "en_george": "bm_george",
    "en_sarah": "af_sarah"
}

def sintetizar_voz(texto: str, voz: str = "es_f", velocidad: float = 1.0,
                   nombre_archivo: str = None) -> str:
    """Sintetiza texto a voz y guarda el archivo WAV."""
    resp = requests.post(
        f"http://localhost:{KOKORO_PORT}/v1/audio/speech",
        json={
            "model": "kokoro",
            "input": texto,
            "voice": voz,
            "speed": velocidad,
            "response_format": "wav"
        },
        timeout=60
    )
    resp.raise_for_status()

    nombre = nombre_archivo or f"tts_{hash(texto) % 10000}.wav"
    ruta = OUTPUT_DIR / nombre
    with open(ruta, "wb") as f:
        f.write(resp.content)
    return str(ruta)

def reproducir_audio(ruta: str) -> None:
    """Reproduce un archivo WAV via aplay (altavoz del sistema)."""
    subprocess.run(["aplay", "-q", ruta], check=True)

def sintetizar_y_reproducir(texto: str, voz: str = "es_f") -> None:
    """Pipeline completo: texto → síntesis → reproducción."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        ruta_tmp = tmp.name

    try:
        resp = requests.post(
            f"http://localhost:{KOKORO_PORT}/v1/audio/speech",
            json={"model": "kokoro", "input": texto, "voice": voz, "speed": 1.0, "response_format": "wav"},
            timeout=60
        )
        resp.raise_for_status()
        with open(ruta_tmp, "wb") as f:
            f.write(resp.content)
        reproducir_audio(ruta_tmp)
    finally:
        os.unlink(ruta_tmp)

def comparar_voces(texto: str) -> None:
    """Genera el mismo texto con todas las voces disponibles."""
    for nombre_voz, voice_id in VOCES.items():
        print(f"Generando voz '{nombre_voz}' ({voice_id})...")
        ruta = sintetizar_voz(texto, voz=voice_id, nombre_archivo=f"comparacion_{nombre_voz}.wav")
        print(f"  → {ruta}")

if __name__ == "__main__":
    import sys
    texto = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else \
        "El Jetson AGX Orin es una plataforma de computación en el borde para inteligencia artificial."
    print(f"Sintetizando: '{texto}'")
    ruta = sintetizar_voz(texto, voz="es_f")
    print(f"[OK] Audio generado: {ruta}")
    reproducir_audio(ruta)
```

---

## 13.3 TTS con piper-tts (Síntesis Ultrarrápida)

Piper-tts es un sintetizador neuronal ultraligero que corre completamente en CPU con latencia <200ms. Ideal para respuestas cortas en el asistente de voz.

```bash
# Instalar piper directamente (sin container)
source ~/venvs/llm/bin/activate
pip install piper-tts

# Descargar voces en español
mkdir -p ~/jetson-ai-data/models/piper-voices

# Voz española femenina (es_ES-mls-medium)
python3 -c "
from piper import PiperVoice
import urllib.request, os

MODELS_DIR = os.path.expanduser('~/jetson-ai-data/models/piper-voices')
voice_url = 'https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/mls_10246/medium/es_ES-mls_10246-medium.onnx'
config_url = voice_url.replace('.onnx', '.onnx.json')

print('Descargando modelo piper (voz española)...')
urllib.request.urlretrieve(voice_url, f'{MODELS_DIR}/es_ES-mls_10246-medium.onnx')
urllib.request.urlretrieve(config_url, f'{MODELS_DIR}/es_ES-mls_10246-medium.onnx.json')
print('[OK] Voz española descargada')
"
```

```python
#!/usr/bin/env python3
"""
tts_piper.py — Síntesis ultra-rápida con piper (<200ms latencia)
Ideal para respuestas cortas en pipelines de asistente de voz.
"""
import subprocess
import sys
import os
from pathlib import Path

PIPER_VOICE = str(Path.home() / "jetson-ai-data/models/piper-voices/es_ES-mls_10246-medium.onnx")
OUTPUT_DIR = Path.home() / "jetson-ai-data/audio/tts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def sintetizar_piper(texto: str, nombre_archivo: str = "piper_output.wav") -> str:
    """Sintetiza texto usando piper directamente (sin servidor HTTP)."""
    ruta_salida = str(OUTPUT_DIR / nombre_archivo)
    subprocess.run(
        ["python3", "-m", "piper", "--model", PIPER_VOICE,
         "--output_file", ruta_salida],
        input=texto.encode("utf-8"),
        check=True,
        capture_output=True
    )
    return ruta_salida

def reproducir_y_sintetizar_piper(texto: str) -> None:
    """Pipeline completo texto → piper → aplay."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
        ruta = sintetizar_piper(texto, tmp.name)
        subprocess.run(["aplay", "-q", ruta])

if __name__ == "__main__":
    texto = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Hola, soy el asistente del Jetson."
    print(f"Sintetizando con piper: '{texto}'")
    ruta = sintetizar_piper(texto)
    print(f"[OK] {ruta}")
    subprocess.run(["aplay", "-q", ruta])
```

### 13.3.1 Tabla Comparativa kokoro-tts vs piper

| Característica | kokoro-tts | piper-tts |
|--------------|-----------|-----------|
| Latencia (respuesta corta) | ~800ms | ~150ms |
| Latencia (párrafo) | ~2-3s | ~500ms |
| Calidad de voz | Excelente | Muy buena |
| Voces en español | `es_e`, `es_f` | 20+ voces regionales |
| Requiere GPU | Sí (mejor calidad) | No (CPU puro) |
| API HTTP | Sí (OpenAI compatible) | No (CLI) |
| Streaming | Parcial | No |

**Recomendación:** Use piper para respuestas cortas en tiempo real (<1 oración), kokoro-tts para narración larga o cuando necesite la API HTTP.

---

## 13.4 Pipeline Completo: STT → LLM → TTS (Asistente de Voz)

<!-- INFOGRAFÍA: Pipeline STT→LLM→TTS en el Jetson AGX Orin — diagrama de flujo mostrando: Micrófono USB → pyaudio (VAD) → faster-whisper (STT) → texto → vLLM Qwen3.5-4B (LLM) → respuesta de texto → piper-tts (TTS) → WAV → altavoz USB. Incluir latencias de cada etapa: grabación ~1s, STT ~0.5s, LLM ~1-2s, TTS <200ms. Total: <3s. Paleta NVIDIA #0F3D3D / #1D9CB8, texto mínimo 10pt, optimizado para KDP Kindle dark/light — pendiente de diseño gráfico -->

Este es el pipeline de asistente de voz offline completo del Jetson. Para la latencia mínima, combine faster-whisper (large-v3 para calidad) + Qwen3.5-4B via vLLM + piper-tts para respuestas:

```bash
Micrófono USB
    ↓ grabación con pyaudio (VAD — detección de voz)      ~1.0s
    ↓ faster-whisper → texto transcrito                   ~0.5s
    ↓ vLLM Qwen3.5-4B (→ qwen4b, ~50 tok/s a 30W)        ~1.0s
    ↓ respuesta de texto
    ↓ piper-tts → WAV                                     <0.2s
    ↓ aplay → altavoz USB
Latencia total objetivo: < 3 segundos
```

```bash
# Instalar pyaudio para captura de audio en tiempo real
sudo apt install -y portaudio19-dev python3-pyaudio
source ~/venvs/llm/bin/activate
pip install pyaudio webrtcvad
```

```python
#!/usr/bin/env python3
"""
voice_assistant_pipeline.py — Asistente de voz offline completo
STT (faster-whisper) → LLM (vLLM qwen4b) → TTS (piper)
Latencia objetivo: < 3 segundos
Modo energético: 30W para modelos pequeños (qwen4b + faster-whisper + piper)
"""
import pyaudio
import wave
import requests
import subprocess
import tempfile
import time
import os
from pathlib import Path
import webrtcvad

# ── Configuración ────────────────────────────────────────────────────────────
STT_URL = "http://localhost:8000/v1/audio/transcriptions"
LLM_URL = "http://localhost:8001/v1/chat/completions"  # qwen4b en puerto alternativo
LLM_MODEL = "qwen4b"
PIPER_VOICE = str(Path.home() / "jetson-ai-data/models/piper-voices/es_ES-mls_10246-medium.onnx")

# Audio config
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK = 320  # 20ms de audio @ 16kHz
FORMAT = pyaudio.paInt16

def grabar_hasta_silencio(max_segundos: int = 15, silencio_ms: int = 1500) -> bytes:
    """
    Graba desde el micrófono hasta detectar silencio (VAD).
    Retorna el audio como bytes WAV.
    """
    vad = webrtcvad.Vad(2)  # agresividad 2 (0-3)
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS,
                       rate=SAMPLE_RATE, input=True, frames_per_buffer=CHUNK)

    frames = []
    silencio_frames = 0
    max_frames = max_segundos * (SAMPLE_RATE // CHUNK)
    frames_silencio_umbral = silencio_ms // 20  # frames de 20ms

    print("[MIC] Escuchando... (hable ahora)")
    hablando = False

    for _ in range(max_frames):
        frame = stream.read(CHUNK, exception_on_overflow=False)
        es_voz = vad.is_speech(frame, SAMPLE_RATE)

        if es_voz:
            hablando = True
            silencio_frames = 0
            frames.append(frame)
        elif hablando:
            frames.append(frame)
            silencio_frames += 1
            if silencio_frames >= frames_silencio_umbral:
                break

    stream.stop_stream()
    stream.close()
    audio.terminate()

    if not frames:
        return b""

    # Convertir a WAV en memoria
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        with wave.open(tmp.name, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(audio.get_sample_size(FORMAT))
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b"".join(frames))
        with open(tmp.name, "rb") as f:
            audio_bytes = f.read()
        os.unlink(tmp.name)
    return audio_bytes

def transcribir_audio(audio_bytes: bytes) -> str:
    """Transcribe audio via faster-whisper API."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        resp = requests.post(
            STT_URL,
            files={"file": ("audio.wav", open(tmp_path, "rb"))},
            data={"model": "whisper-1", "language": "es"},
            timeout=30
        )
        return resp.json().get("text", "").strip()
    except Exception as e:
        return f"[Error STT: {e}]"
    finally:
        os.unlink(tmp_path)

def generar_respuesta(texto: str, historial: list) -> str:
    """Llama al LLM con historial de conversación."""
    historial.append({"role": "user", "content": texto})
    resp = requests.post(
        LLM_URL,
        json={
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": "Eres un asistente de voz del Jetson AGX Orin. Responde en español con respuestas cortas y claras (máximo 3 oraciones). No uses markdown ni listas."}
            ] + historial,
            "max_tokens": 200
        },
        timeout=60
    )
    respuesta = resp.json()["choices"][0]["message"]["content"]
    historial.append({"role": "assistant", "content": respuesta})
    return respuesta

def reproducir_texto(texto: str) -> None:
    """Síntesis de voz con piper y reproducción inmediata."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        subprocess.run(
            ["python3", "-m", "piper", "--model", PIPER_VOICE, "--output_file", tmp_path],
            input=texto.encode("utf-8"), capture_output=True, check=True
        )
        subprocess.run(["aplay", "-q", tmp_path])
    except Exception as e:
        print(f"[Error TTS: {e}]")
    finally:
        os.unlink(tmp_path)

def main():
    historial = []
    print("═" * 50)
    print("Asistente de Voz — Jetson AGX Orin 64GB")
    print("Modo: offline completo (STT + LLM + TTS)")
    print("Presione Ctrl+C para salir")
    print("═" * 50)

    while True:
        try:
            # Grabación con VAD
            audio = grabar_hasta_silencio()
            if not audio:
                print("(Silencio detectado, esperando...)")
                continue

            # STT
            t0 = time.time()
            texto = transcribir_audio(audio)
            if not texto or len(texto) < 3:
                continue
            print(f"[STT] Usted: {texto} ({time.time()-t0:.1f}s)")

            # LLM
            t1 = time.time()
            respuesta = generar_respuesta(texto, historial)
            print(f"[LLM] Asistente: {respuesta} ({time.time()-t1:.1f}s)")

            # TTS
            t2 = time.time()
            reproducir_texto(respuesta)
            print(f"[TTS] Audio reproducido ({time.time()-t2:.1f}s)")
            print(f"[OK]  Latencia total: {time.time()-t0:.1f}s")
            print("─" * 50)

        except KeyboardInterrupt:
            print("\nAsistente detenido.")
            break
        except Exception as e:
            print(f"Error: {e}")
            continue

if __name__ == "__main__":
    # Verificar servicios antes de iniciar
    import sys
    for nombre, url in [("faster-whisper STT", STT_URL.replace("/v1/audio/transcriptions", "/health")),
                        ("vLLM LLM", LLM_URL.replace("/chat/completions", "/models"))]:
        try:
            resp = requests.get(url, timeout=3)
            print(f"[OK] {nombre} activo")
        except:
            print(f"[ERROR] {nombre} no responde en {url}")
            print(f"   Inicie el servicio primero y vuelva a ejecutar este script")
            sys.exit(1)
    main()
```

```bash
# Lanzar el asistente de voz (prerrequisitos en puertos separados)
pwr-30w   # suficiente para qwen4b + faster-whisper + piper

# Terminal 1: faster-whisper en :8000
docker run --runtime nvidia -d --name faster-whisper --restart no \
  --network host -e WHISPER_MODEL=large-v3 -e WHISPER_DEVICE=cuda \
  dustynv/faster-whisper:r39.2.0

# Terminal 2: qwen4b en :8001 (puerto diferente para no conflictar con whisper)
docker run --runtime nvidia -d --name qwen35-4b --restart no \
  --network host --ipc host --shm-size 8g \
  ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve cyankiwi/Qwen3.5-4B-AWQ-4bit \
      --gpu-memory-utilization 0.25 --served-model-name qwen4b \
      --host 0.0.0.0 --port 8001"

# Esperar a que ambos estén listos
echo -n "Esperando faster-whisper"
until curl -sf http://localhost:8000/health > /dev/null; do echo -n "."; sleep 10; done
echo " [OK]"
echo -n "Esperando qwen4b"
until curl -sf http://localhost:8001/v1/models > /dev/null; do echo -n "."; sleep 10; done
echo " [OK]"

# Iniciar el asistente
source ~/venvs/llm/bin/activate
python3 ~/scripts/voice_assistant_pipeline.py
```

---

## 13.5 Monitoreo

```bash
# Ver logs de faster-whisper
docker logs faster-whisper --follow

# Ver logs de kokoro-tts
docker logs kokoro-tts --follow

# Estadísticas de recursos
docker stats faster-whisper kokoro-tts --no-stream

# Verificar dispositivos de audio
aplay -l        # altavoces disponibles
arecord -l      # micrófonos disponibles

# Test de audio de entrada
arecord -D hw:0,0 -f S16_LE -r 16000 -c 1 -d 3 /tmp/test_audio.wav
aplay /tmp/test_audio.wav
```

---

## 13.6 Aliases

```bash
# Agregar a ~/.bash_aliases
cat >> ~/.bash_aliases << 'EOF'

# ── TTS + STT ────────────────────────────────────────────────────────────
alias start-whisper='docker run --runtime nvidia -d --name faster-whisper --restart no \
  --network host \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  -e WHISPER_MODEL=large-v3 -e WHISPER_DEVICE=cuda \
  dustynv/faster-whisper:r39.2.0 \
  && echo "faster-whisper iniciando en :8000 (ver logs: docker logs faster-whisper -f)"'
alias stop-whisper='docker stop faster-whisper && docker rm faster-whisper && echo "[OK] faster-whisper detenido"'
alias start-kokoro='docker run --runtime nvidia -d --name kokoro-tts --restart no \
  --network host \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  dustynv/kokoro-tts:r39.2.0 \
  && echo "kokoro-tts iniciando en :8880 (ver logs: docker logs kokoro-tts -f)"'
alias stop-kokoro='docker stop kokoro-tts && docker rm kokoro-tts && echo "[OK] kokoro-tts detenido"'
alias whisper-logs='docker logs faster-whisper --follow'
alias kokoro-logs='docker logs kokoro-tts --follow'
alias stt-stats='docker stats faster-whisper kokoro-tts --no-stream 2>/dev/null; jtop --once 2>/dev/null || true'
alias voice-assistant='source ~/venvs/llm/bin/activate && python3 ~/scripts/voice_assistant_pipeline.py'
alias transcribir='source ~/venvs/llm/bin/activate && python3 ~/scripts/diarize_and_transcribe.py'
alias tts-es='source ~/venvs/llm/bin/activate && python3 ~/scripts/tts_kokoro.py'
alias tts-rapido='source ~/venvs/llm/bin/activate && python3 ~/scripts/tts_piper.py'
EOF

source ~/.bash_aliases || source ~/.bashrc
```

---

## 13.7 Solución de Problemas

### faster-whisper: `CUDA out of memory` con modelo large-v3

```bash
# Si hay poca RAM libre, usar el modelo medium en su lugar
docker stop faster-whisper && docker rm faster-whisper
docker run --runtime nvidia -d --name faster-whisper --restart no \
  --network host \
  -e WHISPER_MODEL=medium \
  -e WHISPER_DEVICE=cuda \
  dustynv/faster-whisper:r39.2.0
```

### kokoro-tts: Error `No voice found`

```bash
# Verificar que la voz existe en el container
docker exec kokoro-tts ls /voices/ 2>/dev/null || echo "Directorio de voces no encontrado"

# Listar voces disponibles en el container
docker exec kokoro-tts find / -name "*.pt" 2>/dev/null | head -5

# Usar voice ID exacto soportado por la versión instalada
curl -s http://localhost:8880/v1/voices 2>/dev/null | python3 -m json.tool
```

### arecord: `cannot open audio device hw:0,0`

```bash
# Listar dispositivos de audio disponibles
aplay -l
arecord -l

# Usar el dispositivo correcto (ajustar hw:X,Y según la salida)
arecord -D hw:1,0 -f S16_LE -r 16000 -c 1 -d 3 /tmp/test.wav
aplay -D hw:1,0 /tmp/test.wav

# Configurar el dispositivo por defecto
cat >> ~/.asoundrc << 'EOF'
defaults.pcm.card 1
defaults.ctl.card 1
EOF
```

### El pipeline de asistente tiene alta latencia (>5 segundos)

```bash
# Diagnóstico: medir cada etapa por separado
time curl -s http://localhost:8000/v1/audio/transcriptions \
  -F "file=@/tmp/test_audio.wav" -F "model=whisper-1" > /dev/null
# Si > 2s: usar modelo 'medium' de Whisper en lugar de 'large-v3'

time curl -s http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen4b","messages":[{"role":"user","content":"Di hola."}],"max_tokens":20}' > /dev/null
# Si > 1s: usar max_tokens más bajo o cambiar a pwr-maxn temporal

# piper es siempre < 200ms y no necesita optimización
```

---

## Casos de Uso Reales

### Caso 1: Dictado de informes de campo (STT)

Un técnico de campo dicta observaciones directamente desde el teléfono vía WhatsApp. El bot (OpenClaw + faster-whisper) transcribe el audio a texto estructurado y lo guarda en un informe:

```bash
# Script que recibe un audio WAV y retorna JSON estructurado
# Útil para integrarse con el bot de Telegram del Capítulo 20
~/scripts/transcribe_and_structure.sh ~/jetson-ai-data/audio/informe_campo.wav
```

```json
{
  "fecha": "2026-06-28",
  "tecnico": "Carlos Martínez",
  "ubicacion": "Bodega Norte, estante 3",
  "observacion": "Se detecta humedad en la pared izquierda, posible filtración desde el techo. Requiere revisión de impermeabilización en zona A-3.",
  "prioridad": "alta",
  "tokens_whisper": 42,
  "tiempo_transcripcion_seg": 0.8
}
```

### Caso 2: Narración automática de contenido (TTS)

Sistema que convierte artículos de blog o documentos PDF en audio MP3 para consumo en el carro o durante el ejercicio:

```bash
# Convertir un PDF a audio narrado en español con kokoro-tts
python3 -c "
import subprocess, requests
from pathlib import Path

# Extraer texto del PDF
texto = subprocess.check_output(['pdftotext', 'articulo.pdf', '-'], text=True)

# Dividir en párrafos (kokoro maneja hasta ~300 palabras por request)
parrafos = [p.strip() for p in texto.split('\n\n') if p.strip()]

with open('narración.mp3', 'wb') as out:
    for i, parrafo in enumerate(parrafos[:10]):  # primeros 10 párrafos
        print(f'Narando párrafo {i+1}/{len(parrafos)}...')
        r = requests.post('http://localhost:8880/v1/audio/speech',
                         json={'model': 'kokoro', 'input': parrafo, 'voice': 'es_ES-mls_10246-medium'})
        out.write(r.content)
"
```

```bash
# Salida esperada:
Narrando párrafo 1/10...
Narrando párrafo 2/10...
...
[OK] narración.mp3 generado — 4.2 MB, ~8 minutos de audio
```

### Caso 3: Asistente de idiomas (STT + LLM + TTS)

Corrector de pronunciación en inglés: el usuario habla en inglés, faster-whisper transcribe, el LLM evalúa la gramática y pronunciación, y piper responde con la versión correcta en voz:

```bash
# Activar el pipeline de asistente de idiomas
python3 ~/scripts/voice_assistant_pipeline.py \
  --system "Eres un profesor de inglés. El usuario está practicando inglés. Corrige cualquier error gramatical o de vocabulario de forma amigable y breve. Responde SIEMPRE en inglés." \
  --language en \
  --voice en_US-amy-medium
```

```bash
[ESCUCHANDO] Habla ahora...
[STT] You transcript: "Yesterday I go to the market"
[LLM] Correction: "Good try! The correct form is 'Yesterday I went to the market' — 'went' is the past tense of 'go'. Keep practicing!"
[TTS] Reproduciendo respuesta (0.18s)...
```

---

## Resumen del Capítulo

El Jetson AGX Orin procesa voz completamente offline con calidad profesional:

- **faster-whisper large-v3** — mejor calidad en español (~8% WER), usa GPU CUDA 13
- **kokoro-tts** — síntesis natural en español e inglés, API HTTP compatible OpenAI
- **piper-tts** — síntesis ultrarrápida (<200ms) en CPU, ideal para el asistente de voz en tiempo real
- **Diarización** con pyannote.audio + GPU — identifica hablantes en reuniones grabadas
- **Pipeline completo STT → LLM → TTS** en <3 segundos con modelos 30W (faster-whisper medium + Qwen3.5-4B + piper)
- Los dos contenedores (faster-whisper y kokoro-tts) usan 30W y juntos consumen ~5 GB — dejan >55 GB libres

Los capítulos siguientes expanden estos pipelines: el de generación de imágenes y video (Capítulo 19) usa estos mismos contenedores de audio como base para proyectos multimedia completos, y el de despliegue en producción (Capítulo 20) cubre cómo ejecutar el asistente de voz de forma fiable sin riesgos de OOM tras un reinicio.
