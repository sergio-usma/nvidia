# Capítulo 24 — Asistente de Voz Offline Completo

## Introducción

Un asistente de voz completamente offline: habla, el Jetson escucha, procesa y responde con voz natural. Sin enviar nada a la nube. Sin costos de API. Sin necesidad de conexión a internet.

La clave técnica es la latencia. Un asistente de voz es inútil si tarda 10 segundos en responder. Este capítulo construye el pipeline optimizado para mantener latencia menor a 3 segundos desde que termina de hablar hasta que escucha la respuesta — usando los tres modelos más rápidos disponibles en el Jetson.

**Pipeline técnico:**
```
Micrófono USB → VAD → faster-whisper (STT) → qwen3:7b (LLM) → piper-tts (TTS) → Speaker
```

**Por qué piper-tts en lugar de kokoro-tts:** Para asistentes de voz, la velocidad del TTS importa más que la calidad máxima de audio. piper-tts genera audio en ~200ms (vs ~1-2s de kokoro). La calidad es perfectamente aceptable para conversación.

**Prerrequisitos:**
- Capítulo 18 completado (faster-whisper, piper-tts disponibles)
- Ollama con `qwen3:7b` instalado
- Micrófono USB conectado al Jetson
- Speaker USB o jack de audio

**Latencia objetivo por componente:**
- STT (faster-whisper, modelo small): ~400ms para frases cortas
- LLM (qwen3:7b, respuesta breve): ~800–1200ms
- TTS (piper-tts): ~200ms
- **Total: ~1.5–2 segundos** (frases cortas) a **~3 segundos** (respuestas largas)

**Modo de energía:** 30W (3 modelos pequeños coexistiendo — ~13 GB total, bien dentro de los 64 GB)

---

## 24.1 Prerrequisito — Verificación de Hardware de Audio

```bash
# Verificar micrófonos USB detectados
arecord -l
```

```
# Salida esperada (con micrófono USB conectado)
**** List of CAPTURE Hardware Devices ****
card 1: USB Audio Device [USB Audio Device], device 0: USB Audio (hw:1,0)
  Subdevices: 1/1
  Subdevice #0: subdevice #0
```

```bash
# Verificar speakers
aplay -l
```

```
# Salida esperada
**** List of PLAYBACK Hardware Devices ****
card 1: USB Audio Device [USB Audio Device], device 0: USB Audio (hw:1,0)
```

```bash
# Instalar ALSA y PyAudio
sudo apt install -y portaudio19-dev python3-pyaudio alsa-utils
pip install pyaudio sounddevice soundfile webrtcvad
```

---

## 24.2 Prerrequisito — Iniciar los Servicios

```bash
# Verificar recursos
check-ready 30 "voice-assistant"
pwr-30w

# 1. Iniciar faster-whisper (STT) — usar modelo small para velocidad
docker run -d \
  --name faster-whisper \
  --runtime nvidia \
  --restart no \
  --network host \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  -e WHISPER_MODEL=small \
  dustynv/faster-whisper:1.0.3-r39.2.0

# 2. Iniciar piper-tts (TTS rápido)
docker run -d \
  --name piper-tts \
  --restart no \
  --network host \
  dustynv/piper-tts:r39.2.0

# 3. Iniciar Ollama con modelo cargado
sudo systemctl start ollama
sleep 3
# Pre-cargar el modelo para reducir latencia del primer mensaje
curl -s http://localhost:11434/api/generate \
  -d '{"model": "qwen3:7b", "prompt": "Hola", "stream": false}' > /dev/null

# Esperar que todos estén listos
echo "Esperando servicios..."
until curl -sf http://localhost:8000/v1/models > /dev/null 2>&1; do sleep 5; echo "  faster-whisper..."; done
until curl -sf http://localhost:10200/voices > /dev/null 2>&1; do sleep 5; echo "  piper-tts..."; done
echo "[OK] Todos los servicios listos"
```

---

## 24.3 Módulo VAD — Detección de Actividad de Voz

```python
# voice_assistant/vad.py
"""
Voice Activity Detection — detecta cuándo el usuario está hablando.
Usa WebRTC VAD para activación con bajo latencia.
"""
import collections
import struct
import pyaudio
import webrtcvad

SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30  # 30ms por frame (WebRTC VAD soporta 10, 20, 30ms)
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000 * 2)  # bytes


class AudioCapture:
    """Captura audio del micrófono con detección de actividad de voz."""
    
    def __init__(self, aggressiveness: int = 2, silence_frames: int = 20):
        """
        Args:
            aggressiveness: 0-3. 0=menos agresivo (más falsos positivos), 3=más agresivo
            silence_frames: frames de silencio para considerar que terminó de hablar
        """
        self.vad = webrtcvad.Vad(aggressiveness)
        self.silence_frames = silence_frames
        self.pa = pyaudio.PyAudio()
        
        # Buffer circular de frames para capturar contexto pre-voz
        self.ring_buffer = collections.deque(maxlen=15)
    
    def get_device_index(self) -> int:
        """Encuentra el índice del micrófono USB."""
        for i in range(self.pa.get_device_count()):
            info = self.pa.get_device_info_by_index(i)
            if info["maxInputChannels"] > 0:
                if "USB" in info["name"] or "usb" in info["name"].lower():
                    return i
        return None  # usa el dispositivo por defecto
    
    def escuchar(self) -> bytes | None:
        """
        Escucha hasta que el usuario habla y termina.
        Returns: bytes del audio capturado, o None si hubo error.
        """
        device_index = self.get_device_index()
        
        stream = self.pa.open(
            rate=SAMPLE_RATE,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=int(FRAME_SIZE / 2)
        )
        
        print("[MIC] Escuchando... (hable ahora)")
        
        frames_activados = []
        silencio_consecutivo = 0
        hablando = False
        
        try:
            while True:
                data = stream.read(int(FRAME_SIZE / 2), exception_on_overflow=False)
                
                es_voz = False
                try:
                    es_voz = self.vad.is_speech(data, SAMPLE_RATE)
                except:
                    pass
                
                if not hablando:
                    self.ring_buffer.append(data)
                    # Activar si la mayoría de los últimos frames son voz
                    n_voz = sum(1 for f in self.ring_buffer 
                               if self._is_speech(f))
                    if n_voz > 0.75 * len(self.ring_buffer):
                        hablando = True
                        frames_activados.extend(list(self.ring_buffer))
                        self.ring_buffer.clear()
                        print("  (detectada voz)")
                else:
                    frames_activados.append(data)
                    if es_voz:
                        silencio_consecutivo = 0
                    else:
                        silencio_consecutivo += 1
                        if silencio_consecutivo > self.silence_frames:
                            print("  (silencio detectado — procesando)")
                            break
        
        finally:
            stream.stop_stream()
            stream.close()
        
        return b"".join(frames_activados) if frames_activados else None
    
    def _is_speech(self, data: bytes) -> bool:
        try:
            return self.vad.is_speech(data, SAMPLE_RATE)
        except:
            return False
    
    def cerrar(self):
        self.pa.terminate()
```

---

## 24.4 Módulo STT — Speech-to-Text

> **NOTA — STT alternativo:** Este módulo usa `faster-whisper` via HTTP por su baja latencia y fácil configuración. NVIDIA Riva (`nvidia/riva-speech`) es una alternativa de mayor rendimiento con soporte de streaming nativo, pero requiere más RAM y configuración adicional. Ver Capítulo 18 §18.6.

```python
# voice_assistant/stt.py
"""
Speech-to-Text usando faster-whisper via HTTP API.
"""
import io
import struct
import wave
import requests


STT_URL = "http://localhost:8000/v1/audio/transcriptions"
STT_MODEL = "small"  # balance velocidad/calidad para asistente de voz


def audio_bytes_a_wav(audio_bytes: bytes, sample_rate: int = 16000) -> bytes:
    """Convierte bytes de audio PCM16 a formato WAV en memoria."""
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit = 2 bytes
        wf.setframerate(sample_rate)
        wf.writeframes(audio_bytes)
    return wav_buffer.getvalue()


def transcribir(audio_bytes: bytes, idioma: str = "es") -> str:
    """
    Transcribe audio PCM16 a texto.
    
    Args:
        audio_bytes: Audio en formato PCM16 16kHz mono
        idioma: Código de idioma ISO 639-1 ("es", "en", etc.)
    
    Returns:
        Texto transcrito, o "" si no se detectó habla.
    """
    wav_bytes = audio_bytes_a_wav(audio_bytes)
    
    files = {"file": ("audio.wav", wav_bytes, "audio/wav")}
    data = {
        "model": STT_MODEL,
        "language": idioma
    }
    
    try:
        resp = requests.post(STT_URL, files=files, data=data, timeout=30)
        
        if resp.status_code == 200:
            texto = resp.json().get("text", "").strip()
            return texto
        else:
            print(f"  [WARN]  STT error {resp.status_code}")
            return ""
    except requests.Timeout:
        print("  [WARN]  STT timeout")
        return ""
```

---

## 24.5 Módulo LLM — Procesamiento de Lenguaje Natural

```python
# voice_assistant/llm.py
"""
Módulo LLM para el asistente de voz.
Optimizado para respuestas CORTAS y rápidas.
"""
from openai import OpenAI

OLLAMA_URL = "http://localhost:11434/v1"
MODELO = "qwen3:7b"

SISTEMA = """Eres un asistente de voz personal. Reglas CRÍTICAS:
1. Respuestas MUY CORTAS: máximo 2-3 oraciones
2. Sin listas, bullets ni markdown
3. Lenguaje conversacional, natural
4. Si no sabes algo, dilo directamente en una oración
5. Responde en el mismo idioma que te hablen
6. Para preguntas de matemáticas o datos: da solo la respuesta, sin explicación a menos que se pida"""


class AsistenteLLM:
    """LLM con historial de conversación para contexto."""
    
    def __init__(self, max_historial: int = 10):
        self.cliente = OpenAI(base_url=OLLAMA_URL, api_key="ollama")
        self.historial = []
        self.max_historial = max_historial
    
    def responder(self, mensaje: str) -> str:
        """
        Genera una respuesta al mensaje del usuario.
        Mantiene el historial para contexto conversacional.
        """
        self.historial.append({"role": "user", "content": mensaje})
        
        # Limitar historial para no sobrecargar el contexto
        mensajes_contexto = (
            [{"role": "system", "content": SISTEMA}] +
            self.historial[-self.max_historial:]
        )
        
        respuesta = self.cliente.chat.completions.create(
            model=MODELO,
            messages=mensajes_contexto,
            max_tokens=150,  # límite bajo para respuestas rápidas
            temperature=0.7
        )
        
        texto_respuesta = respuesta.choices[0].message.content.strip()
        self.historial.append({"role": "assistant", "content": texto_respuesta})
        
        # Mantener el historial dentro del límite
        if len(self.historial) > self.max_historial * 2:
            self.historial = self.historial[-(self.max_historial * 2):]
        
        return texto_respuesta
    
    def resetear(self):
        """Limpia el historial para empezar una nueva conversación."""
        self.historial = []
        print("  [OK] Historial de conversación reiniciado")
```

---

## 24.6 Módulo TTS — Texto a Voz

```python
# voice_assistant/tts.py
"""
Text-to-Speech usando piper-tts via HTTP API.
piper-tts tiene baja latencia (~200ms) ideal para asistentes de voz.
"""
import io
import subprocess
import requests
import soundfile as sf
import sounddevice as sd


PIPER_URL = "http://localhost:10200"
VOZ_DEFAULT = "es_ES-mls_10246-low"  # Español España — verificar disponibilidad en su instalación


def listar_voces() -> list:
    """Lista las voces disponibles en el servidor piper-tts."""
    try:
        resp = requests.get(f"{PIPER_URL}/voices", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return []


def sintetizar_y_reproducir(texto: str, voz: str = None) -> bool:
    """
    Sintetiza texto a voz y lo reproduce inmediatamente.
    
    Args:
        texto: Texto a sintetizar
        voz: ID de la voz piper. Si None, usa la voz por defecto del servidor.
    
    Returns:
        True si se reprodujo correctamente.
    """
    if not texto.strip():
        return True
    
    try:
        # Solicitar síntesis
        payload = {"text": texto}
        if voz:
            payload["voice"] = voz
        
        resp = requests.post(
            f"{PIPER_URL}/synthesize",
            json=payload,
            timeout=15
        )
        
        if resp.status_code != 200:
            print(f"  [WARN]  TTS error {resp.status_code}")
            return False
        
        # Reproducir audio
        audio_bytes = io.BytesIO(resp.content)
        data, samplerate = sf.read(audio_bytes)
        sd.play(data, samplerate)
        sd.wait()  # Esperar a que termine la reproducción
        return True
        
    except Exception as e:
        # Fallback: usar espeak si piper falla
        print(f"  [WARN]  TTS error: {str(e)[:50]} — usando espeak como fallback")
        subprocess.run(
            ["espeak-ng", "-l", "es", "-s", "150", texto],
            capture_output=True
        )
        return False
```

---

## 24.7 Orquestador Principal del Asistente

```python
# voice_assistant.py
"""
Orquestador principal del asistente de voz offline.
Integra VAD → STT → LLM → TTS en un loop de conversación.
"""
import time
import sys

from voice_assistant.vad import AudioCapture
from voice_assistant.stt import transcribir
from voice_assistant.llm import AsistenteLLM
from voice_assistant.tts import sintetizar_y_reproducir, listar_voces


COMANDOS_SALIDA = {"adiós", "adios", "salir", "exit", "hasta luego", "bye"}
COMANDOS_RESET = {"reiniciar", "nueva conversación", "nueva conversacion", "reset"}


def iniciar_asistente(idioma: str = "es", voz_tts: str = None):
    """
    Inicia el bucle principal del asistente de voz.
    
    Args:
        idioma: Idioma para STT (código ISO: "es", "en", "fr")
        voz_tts: ID de voz piper-tts (None = voz por defecto)
    """
    print("""
╔══════════════════════════════════════════════════════════╗
║       ASISTENTE DE VOZ OFFLINE — JETSON AGX ORIN        ║
║       STT: faster-whisper (small)                        ║
║       LLM: qwen3:7b (Ollama)                             ║
║       TTS: piper-tts                                     ║
╠══════════════════════════════════════════════════════════╣
║  Diga "adiós" o "salir" para terminar                    ║
║  Diga "reiniciar" para nueva conversación                ║
╚══════════════════════════════════════════════════════════╝
""")
    
    # Verificar voces disponibles
    voces = listar_voces()
    if voces:
        print(f"Voces TTS disponibles: {len(voces)}")
        for v in voces[:3]:
            print(f"  - {v}")
        if not voz_tts and voces:
            voz_tts = voces[0] if isinstance(voces[0], str) else None
    
    # Iniciar mensaje de bienvenida
    bienvenida = "Hola, soy su asistente personal. ¿En qué puedo ayudarle?"
    print(f"\nAsistente: {bienvenida}")
    sintetizar_y_reproducir(bienvenida, voz_tts)
    
    # Inicializar componentes
    captura = AudioCapture(aggressiveness=2, silence_frames=25)
    llm = AsistenteLLM(max_historial=12)
    
    try:
        while True:
            # 1. Capturar audio con VAD
            audio_bytes = captura.escuchar()
            
            if not audio_bytes:
                continue
            
            # 2. STT — Transcribir
            t_inicio = time.time()
            texto_usuario = transcribir(audio_bytes, idioma)
            t_stt = time.time() - t_inicio
            
            if not texto_usuario:
                print("  (no se detectó habla clara)")
                continue
            
            print(f"\nUsted: {texto_usuario}")
            print(f"  [STT: {t_stt:.2f}s]")
            
            # Verificar comandos especiales
            texto_lower = texto_usuario.lower().strip()
            
            if any(cmd in texto_lower for cmd in COMANDOS_SALIDA):
                despedida = "¡Hasta luego! Fue un placer asistirle."
                print(f"Asistente: {despedida}")
                sintetizar_y_reproducir(despedida, voz_tts)
                break
            
            if any(cmd in texto_lower for cmd in COMANDOS_RESET):
                llm.resetear()
                respuesta = "Conversación reiniciada. ¿En qué puedo ayudarle?"
                print(f"Asistente: {respuesta}")
                sintetizar_y_reproducir(respuesta, voz_tts)
                continue
            
            # 3. LLM — Generar respuesta
            t_inicio = time.time()
            respuesta = llm.responder(texto_usuario)
            t_llm = time.time() - t_inicio
            
            # 4. TTS — Sintetizar y reproducir
            t_inicio = time.time()
            sintetizar_y_reproducir(respuesta, voz_tts)
            t_tts = time.time() - t_inicio
            
            print(f"Asistente: {respuesta}")
            print(f"  [LLM: {t_llm:.2f}s | TTS: {t_tts:.2f}s | Total: {t_stt+t_llm+t_tts:.2f}s]")
    
    except KeyboardInterrupt:
        print("\n\nAsistente interrumpido por el usuario.")
    finally:
        captura.cerrar()
        print("[OK] Asistente de voz cerrado")


if __name__ == "__main__":
    idioma = sys.argv[1] if len(sys.argv) > 1 else "es"
    iniciar_asistente(idioma=idioma)
```

```bash
# Crear la estructura del proyecto
mkdir -p ~/projects/voice-assistant/voice_assistant
# (copie los módulos a sus respectivas rutas)
touch ~/projects/voice-assistant/voice_assistant/__init__.py

# Instalar dependencias adicionales
pip install webrtcvad sounddevice soundfile

# Iniciar el asistente
cd ~/projects/voice-assistant
python voice_assistant.py es
```

---

## 24.8 Benchmarking de Latencia

```python
# benchmark_latencia.py — medir la latencia real del pipeline
import time
import requests

print("═══ Benchmark de Latencia — Asistente de Voz ═══")

# STT Benchmark
texto_test = "Buenos días, ¿cómo estás hoy?"
import wave, io
# Crear audio de silencio de 2 segundos como test
wav_buf = io.BytesIO()
with wave.open(wav_buf, "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(16000)
    wf.writeframes(b'\x00' * 16000 * 2 * 2)  # 2 segundos de silencio

t = time.time()
resp = requests.post(
    "http://localhost:8000/v1/audio/transcriptions",
    files={"file": ("test.wav", wav_buf.getvalue(), "audio/wav")},
    data={"model": "small", "language": "es"},
    timeout=30
)
print(f"  STT (2s silencio): {time.time()-t:.3f}s → {resp.status_code}")

# LLM Benchmark
from openai import OpenAI
cliente = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

t = time.time()
resp_llm = cliente.chat.completions.create(
    model="qwen3:7b",
    messages=[{"role": "user", "content": "¿Qué hora es ahora mismo?"}],
    max_tokens=50
)
t_llm = time.time() - t
tps = resp_llm.usage.completion_tokens / t_llm
print(f"  LLM (50 tokens): {t_llm:.3f}s → {resp_llm.usage.completion_tokens} tokens @ {tps:.1f} tok/s")

# TTS Benchmark
t = time.time()
resp_tts = requests.post(
    "http://localhost:10200/synthesize",
    json={"text": "El asistente está funcionando correctamente."},
    timeout=15
)
print(f"  TTS (frase corta): {time.time()-t:.3f}s → {resp_tts.status_code}")

print(f"\n  Latencia estimada total: {0.4 + t_llm + 0.2:.2f}s (STT+LLM+TTS para frase típica)")
```

---

## 24.9 Limpieza Post-Pipeline

```bash
# Detener los servicios del asistente de voz
docker stop faster-whisper && docker rm faster-whisper
docker stop piper-tts && docker rm piper-tts
sudo systemctl stop ollama

sync && echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
pwr-15w

free -h | awk '/^Mem:/{printf "RAM libre: %s de %s\n", $7, $2}'
echo "[OK] Asistente de voz detenido"
```

---

## 24.10 Verificación Final

```bash
echo "╔═══════════════════════════════════════════════════════╗"
echo "║    VERIFICACIÓN CAPÍTULO 24 — ASISTENTE DE VOZ       ║"
echo "╚═══════════════════════════════════════════════════════╝"

echo ""
echo "── Hardware de audio ──"
arecord -l 2>/dev/null | grep -q "card" \
  && echo "  [OK] Micrófono detectado" || echo "  ○  No se detectó micrófono USB"
aplay -l 2>/dev/null | grep -q "card" \
  && echo "  [OK] Speaker detectado" || echo "  ○  No se detectó speaker"

echo ""
echo "── Python audio ──"
python3 -c "import pyaudio; print('  [OK] pyaudio')" 2>/dev/null || echo "  ○  pip install pyaudio"
python3 -c "import webrtcvad; print('  [OK] webrtcvad')" 2>/dev/null || echo "  ○  pip install webrtcvad"
python3 -c "import sounddevice; print('  [OK] sounddevice')" 2>/dev/null || echo "  ○  pip install sounddevice"

echo ""
echo "── Servicios ──"
curl -sf http://localhost:8000/v1/models > /dev/null 2>&1 && echo "  [OK] faster-whisper" || echo "  ○  faster-whisper offline"
curl -sf http://localhost:10200/voices > /dev/null 2>&1 && echo "  [OK] piper-tts" || echo "  ○  piper-tts offline"
curl -sf http://localhost:11434/api/version > /dev/null && echo "  [OK] Ollama" || echo "  ○  Ollama offline"

echo ""
echo "═════════════════════════════════════════════════════════"
```

---

## 24.11 Escalabilidad y Extensiones

### 24.11.1 Canal de Texto vía Telegram como Fallback

Cuando no haya micrófono disponible (trabajo remoto, entorno ruidoso), el mismo asistente puede atender consultas de texto por Telegram y responder con audio generado por kokoro-tts.

**Flujo con N8N** (ver Capítulo 14):

```yaml
Nodo 1 — Telegram Trigger:
  tipo: telegram_trigger
  evento: message_received
  filtro: texto

Nodo 2 — Execute Command (LLM):
  tipo: execute_command
  comando: |
    python3 ~/projects/voice-assistant/modules/llm.py \
      --input "{{message_text}}" \
      --output-text /tmp/va_response.txt
  timeout: 30

Nodo 3 — Execute Command (TTS):
  tipo: execute_command
  comando: |
    python3 ~/projects/voice-assistant/modules/tts.py \
      --input /tmp/va_response.txt \
      --output /tmp/va_response.wav
  timeout: 15

Nodo 4 — Send Voice:
  tipo: telegram_send_voice
  chat_id: {{chat_id}}
  archivo: /tmp/va_response.wav
```

**Flujo con OpenClaw** (ver Capítulo 11A):

```json
"agents": {
  "voice_assistant": {
    "description": "Asistente de voz — responde con audio",
    "command": "python3 ~/projects/voice-assistant/telegram_mode.py --input {{input}}",
    "channels": ["telegram"],
    "reply_with_voice": true
  }
}
```

### 24.11.2 Modo Mixto con OpenRouter

Para consultas complejas que superen la capacidad del modelo local, derive al cloud manteniendo el pipeline de voz intacto:

```python
import os
from openai import OpenAI

USE_LOCAL = os.getenv("USE_LOCAL_LLM", "true").lower() == "true"

if USE_LOCAL:
    cliente = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    MODELO  = "qwen3:7b"
else:
    cliente = OpenAI(
        base_url=os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1"),
        api_key=os.getenv("OPENROUTER_API_KEY", ""),
    )
    MODELO = "meta-llama/llama-3.3-70b-instruct:free"
```

### 24.11.3 Evaluación de Backend para Mínima Latencia

La latencia es el factor crítico en un asistente de voz: el usuario espera respuesta en menos de 3 segundos. Cada backend impacta diferente en ese objetivo:

| Backend | Primer token (qwen3:7b) | VRAM usada | Startup | Recomendación |
|---|---|---|---|---|
| **Ollama** (qwen3:7b) | ~800–1200 ms | ~5.5 GB | Inmediato (precargado) | Actual — buen balance |
| **llama.cpp** (qwen3:4b Q4_K_M) | **~300–500 ms** | ~2.5 GB | Inmediato | **Mejor opción** para minimizar latencia |
| **llama.cpp** (qwen3:7b Q4_K_M) | ~600–900 ms | ~4 GB | Inmediato | Buena opción si se prefiere mayor calidad |
| **vLLM** (qwen3:7b) | ~1500–2000 ms (primer call) | ~6 GB | 30–60 seg | No recomendado — startup penaliza latencia |

> **CONSEJO:** Para el asistente de voz, **llama.cpp con `qwen3:4b Q4_K_M`** es la opción con menor latencia de primer token. El modelo 4B es suficientemente capaz para respuestas de asistente de voz conversacional. Si nota que las respuestas pierden coherencia en conversaciones largas, cambie a `qwen3:7b Q4_K_M`.

**Configurar llama.cpp como servidor alternativo:**

```bash
# Instalar llama.cpp (ver Capítulo 12 — sección llama.cpp)
# Descargar modelo GGUF de qwen3:4b
huggingface-cli download Qwen/Qwen3-4B-GGUF \
  --include "Qwen3-4B-Q4_K_M.gguf" \
  --local-dir ~/data/models/gguf/

# Lanzar servidor llama.cpp en puerto alternativo
~/bin/llama-server \
  --model ~/data/models/gguf/Qwen3-4B-Q4_K_M.gguf \
  --ctx-size 4096 \
  --n-gpu-layers 99 \
  --port 11435 \
  --host 0.0.0.0 &

# Cambiar el módulo LLM del asistente para usar llama.cpp
# En modules/llm.py: OLLAMA_URL = "http://localhost:11435"
```

---

> **Próximo paso:** El Capítulo 25 construye el sistema RAG (Retrieval Augmented Generation) para consultar documentos empresariales con respuestas citadas con sus fuentes.
