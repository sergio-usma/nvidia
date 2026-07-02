# Capítulo 22 — Bot de Transcripción y Análisis de Reuniones

## Introducción

Cada reunión, conferencia o clase genera información valiosa que se pierde porque nadie tiene tiempo de transcribirla manualmente. Este capítulo construye un sistema automatizado que procesa archivos de audio, los transcribe con faster-whisper, los analiza con un LLM y entrega el resultado completo por email — sin conexión a servicios externos y sin costos recurrentes.

**Caso de uso principal:** Deja una reunión de equipo grabada en el Jetson. Al terminar, ejecutas un comando. 15 minutos después recibes en tu email la transcripción completa + resumen ejecutivo + puntos de acción.

**Prerrequisitos:**
- Capítulo 18 completado (faster-whisper disponible)
- Ollama activo con `qwen3:7b`
- Cuenta de email con acceso SMTP (Gmail con App Password funciona)
- `ffmpeg` instalado

**Tiempo de procesamiento por hora de audio:**
- Transcripción (large-v3): ~8–12 minutos
- Análisis LLM: ~3–5 minutos
- Email: ~5 segundos
- **Total: ~15–20 minutos por hora de reunión**

**Modo de energía:** 30W para STT → MAXN para análisis LLM → 15W al terminar

---

## 22.1 Prerrequisito — Verificación del Sistema

```bash
# Verificar recursos antes de iniciar
check-ready 20 "transcription-bot"

# Iniciar faster-whisper (modelo medium para español, large-v3 para máxima calidad)
docker run -d \
  --name faster-whisper \
  --runtime nvidia \
  --restart no \
  --network host \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  -e WHISPER_MODEL=large-v3 \
  dustynv/faster-whisper:1.0.3-r39.2.0

echo "Esperando que cargue el modelo (puede tardar 1-2 min la primera vez)..."
until curl -sf http://localhost:8000/health > /dev/null 2>&1 || \
      curl -sf http://localhost:8000/v1/models > /dev/null 2>&1; do
  sleep 10
  echo "  ..."
done
echo "[OK] faster-whisper listo en puerto 8000"

# STT usa 30W (modelo grande, pero solo inferencia secuencial)
pwr-30w
```

---

## 22.2 Estructura del Proyecto

```bash
mkdir -p ~/projects/transcription-bot/{scripts,input,output,config}
cd ~/projects/transcription-bot
```

```bash
transcription-bot/
├── scripts/
│   ├── 01_transcribe.py     # Transcripción con faster-whisper
│   ├── 02_analyze.py        # Análisis con LLM
│   ├── 03_send_email.py     # Envío por SMTP
│   └── utils.py             # Formateadores comunes
├── config/
│   └── settings.json        # Configuración SMTP + preferencias
├── input/                   # Archivos de audio a procesar
└── output/                  # Transcripciones + análisis guardados
```

---

## 22.3 Configuración

```bash
# Crear archivo de configuración
cat > ~/projects/transcription-bot/config/settings.json << 'EOF'
{
    "smtp": {
        "host": "smtp.gmail.com",
        "port": 587,
        "user": "su_email@gmail.com",
        "password": "xxxx xxxx xxxx xxxx",
        "destinatario": "destino@empresa.com",
        "nombre_remitente": "Jetson Transcription Bot"
    },
    "whisper": {
        "model": "large-v3",
        "language": "es",
        "base_url": "http://localhost:8000"
    },
    "llm": {
        "model": "qwen3:7b",
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama"
    },
    "analisis": {
        "idioma_salida": "es",
        "max_tokens_resumen": 800,
        "max_tokens_puntos": 600
    }
}
EOF
```

> **Gmail App Password:** En Google Account → Seguridad → Verificación en 2 pasos → Contraseñas de aplicaciones → Generar. Copie las 16 letras (sin espacios) como valor de `password`. Con la verificación en 2 pasos, NUNCA use su contraseña real.

> **NOTA — OAuth2 como alternativa:** Si el App Password es bloqueado por la política de seguridad de su organización, puede autenticar Gmail mediante OAuth2 con la biblioteca `google-auth-oauthlib`. Más seguro pero requiere registrar una aplicación en Google Cloud Console. Vea la documentación oficial de Google para la guía de migración.

> **NOTA — STT alternativo:** Este capítulo usa `faster-whisper` por su facilidad de integración. NVIDIA Riva (`nvidia/riva-speech`) ofrece mayor rendimiento y soporte de diarización nativa, pero requiere más memoria y configuración. Ver Capítulo 18 §18.6 para instrucciones de Riva.

---

## 22.4 Script 1 — Transcripción con faster-whisper

```python
# scripts/01_transcribe.py
"""
Transcribe un archivo de audio usando el servidor faster-whisper local.
Produce: texto completo + segmentos con timestamps.
"""
import json
import sys
import time
import requests
from pathlib import Path


def cargar_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "settings.json"
    with open(config_path) as f:
        return json.load(f)


def convertir_a_wav(ruta_entrada: Path) -> Path:
    """Convierte el audio a WAV 16kHz mono (formato óptimo para Whisper)."""
    import subprocess
    
    ruta_wav = ruta_entrada.parent / f"{ruta_entrada.stem}_converted.wav"
    
    if ruta_entrada.suffix.lower() == ".wav":
        # Verificar que ya está en el formato correcto
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_streams", "-of", "json", str(ruta_entrada)],
            capture_output=True, text=True
        )
        info = json.loads(result.stdout)
        for stream in info.get("streams", []):
            if stream.get("codec_type") == "audio":
                if stream.get("sample_rate") == "16000" and stream.get("channels") == 1:
                    return ruta_entrada  # Ya está en formato correcto
    
    print(f"  Convirtiendo a WAV 16kHz mono...")
    subprocess.run([
        "ffmpeg", "-y", "-i", str(ruta_entrada),
        "-ar", "16000", "-ac", "1",
        str(ruta_wav)
    ], capture_output=True, check=True)
    
    return ruta_wav


def transcribir(ruta_audio: str, config: dict = None) -> dict:
    """
    Transcribe un archivo de audio.
    
    Returns:
        dict con 'texto_completo', 'segmentos', 'duracion_audio', 'tiempo_proceso'
    """
    if config is None:
        config = cargar_config()
    
    cfg_whisper = config["whisper"]
    ruta = Path(ruta_audio)
    
    if not ruta.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {ruta_audio}")
    
    print(f"[STT] Transcribiendo: {ruta.name}")
    
    # Convertir si es necesario
    ruta_procesada = convertir_a_wav(ruta)
    tamanio_mb = ruta_procesada.stat().st_size / 1024 / 1024
    print(f"  Tamaño: {tamanio_mb:.1f} MB")
    
    inicio = time.time()
    
    # Enviar al servidor faster-whisper
    with open(ruta_procesada, "rb") as f:
        files = {"file": (ruta.name, f, "audio/wav")}
        data = {
            "model": cfg_whisper["model"],
            "response_format": "verbose_json",  # incluye segmentos con timestamps
        }
        if cfg_whisper.get("language"):
            data["language"] = cfg_whisper["language"]
        
        print(f"  Modelo: {cfg_whisper['model']} | Idioma: {cfg_whisper.get('language', 'auto')}")
        print("  Transcribiendo... (esto puede tardar varios minutos)")
        
        resp = requests.post(
            f"{cfg_whisper['base_url']}/v1/audio/transcriptions",
            files=files,
            data=data,
            timeout=1800  # 30 min máximo para audios muy largos
        )
    
    if resp.status_code != 200:
        raise RuntimeError(f"Error HTTP {resp.status_code}: {resp.text[:200]}")
    
    tiempo_proceso = time.time() - inicio
    resultado_raw = resp.json()
    
    # Extraer información
    texto_completo = resultado_raw.get("text", "").strip()
    segmentos = resultado_raw.get("segments", [])
    duracion_audio = resultado_raw.get("duration", 0)
    
    palabras = len(texto_completo.split())
    
    # Calcular velocidad de procesamiento
    if duracion_audio > 0:
        factor_velocidad = duracion_audio / tiempo_proceso
    else:
        factor_velocidad = 0
    
    print(f"\n  [OK] Transcripción completada:")
    print(f"     Duración del audio: {duracion_audio/60:.1f} min")
    print(f"     Tiempo de proceso: {tiempo_proceso/60:.1f} min")
    print(f"     Velocidad: {factor_velocidad:.1f}x tiempo real")
    print(f"     Palabras transcritas: {palabras:,}")
    
    # Limpiar el WAV convertido si se creó uno nuevo
    if ruta_procesada != ruta and ruta_procesada.exists():
        ruta_procesada.unlink()
    
    return {
        "archivo_original": str(ruta),
        "nombre_archivo": ruta.name,
        "texto_completo": texto_completo,
        "segmentos": segmentos,
        "duracion_audio_seg": duracion_audio,
        "palabras_totales": palabras,
        "tiempo_proceso_seg": tiempo_proceso,
        "modelo": cfg_whisper["model"],
        "idioma": cfg_whisper.get("language", "auto")
    }


def formatear_con_timestamps(segmentos: list) -> str:
    """Formatea los segmentos con timestamps legibles."""
    lineas = []
    for seg in segmentos:
        inicio = seg.get("start", 0)
        min_i = int(inicio // 60)
        seg_i = int(inicio % 60)
        texto = seg.get("text", "").strip()
        lineas.append(f"[{min_i:02d}:{seg_i:02d}] {texto}")
    return "\n".join(lineas)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python 01_transcribe.py <audio.mp3|wav> [output.json]")
        sys.exit(1)
    
    ruta_audio = sys.argv[1]
    salida = sys.argv[2] if len(sys.argv) > 2 else None
    
    resultado = transcribir(ruta_audio)
    
    if salida:
        with open(salida, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)
        print(f"\n[OK] Guardado en: {salida}")
    else:
        print("\n── Primeros 500 caracteres ──")
        print(resultado["texto_completo"][:500])
```

---

## 22.5 Script 2 — Análisis con LLM

```python
# scripts/02_analyze.py
"""
Analiza la transcripción con un LLM y produce:
- Resumen ejecutivo
- Puntos clave
- Elementos de acción con responsables
- Índice por timestamp
"""
import json
import sys
import time
from pathlib import Path
from openai import OpenAI


def cargar_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "settings.json"
    with open(config_path) as f:
        return json.load(f)


def analizar_transcripcion(transcripcion: dict, config: dict = None) -> dict:
    """Genera análisis completo de la transcripción."""
    if config is None:
        config = cargar_config()
    
    cfg_llm = config["llm"]
    cfg_analisis = config["analisis"]
    idioma = cfg_analisis.get("idioma_salida", "es")
    
    cliente = OpenAI(base_url=cfg_llm["base_url"], api_key=cfg_llm["api_key"])
    
    texto = transcripcion["texto_completo"]
    nombre = transcripcion["nombre_archivo"]
    duracion_min = transcripcion["duracion_audio_seg"] / 60
    
    print(f"\n[LLM] Analizando: {nombre} ({duracion_min:.1f} min de audio)")
    
    # Si el texto es muy largo, tomar los primeros 12000 caracteres para el análisis
    texto_para_analisis = texto[:12000]
    if len(texto) > 12000:
        texto_para_analisis += "\n\n[... transcripción continúa ...]"
        print(f"  [WARN]  Texto truncado a 12,000 caracteres para el análisis (total: {len(texto):,})")
    
    resultados = {}
    
    # ── Resumen ejecutivo ──────────────────────────────────
    print("  Generando resumen ejecutivo...")
    inicio = time.time()
    
    prompt_resumen = f"""Analiza esta transcripción de reunión/conferencia y genera un resumen ejecutivo en {idioma}.

El resumen debe:
- Tener entre 200-300 palabras
- Estar en párrafos fluidos (no bullet points)  
- Capturar los temas principales discutidos
- Ser comprensible sin leer la transcripción completa

TRANSCRIPCIÓN:
{texto_para_analisis}

RESUMEN EJECUTIVO:"""
    
    resp = cliente.chat.completions.create(
        model=cfg_llm["model"],
        messages=[{"role": "user", "content": prompt_resumen}],
        max_tokens=cfg_analisis.get("max_tokens_resumen", 800)
    )
    resultados["resumen"] = resp.choices[0].message.content.strip()
    print(f"     [OK] ({time.time()-inicio:.1f}s)")
    
    # ── Puntos clave ──────────────────────────────────────
    print("  Extrayendo puntos clave...")
    inicio = time.time()
    
    prompt_puntos = f"""De esta transcripción, extrae los 5-8 puntos clave más importantes en {idioma}.

Formato EXACTO:
• [Punto clave conciso en una oración]
• [Punto clave conciso en una oración]
...

TRANSCRIPCIÓN:
{texto_para_analisis}

PUNTOS CLAVE:"""
    
    resp = cliente.chat.completions.create(
        model=cfg_llm["model"],
        messages=[{"role": "user", "content": prompt_puntos}],
        max_tokens=cfg_analisis.get("max_tokens_puntos", 600)
    )
    resultados["puntos_clave"] = resp.choices[0].message.content.strip()
    print(f"     [OK] ({time.time()-inicio:.1f}s)")
    
    # ── Elementos de acción ───────────────────────────────
    print("  Identificando elementos de acción...")
    inicio = time.time()
    
    prompt_acciones = f"""Identifica todos los elementos de acción, compromisos y tareas mencionados en esta transcripción.

Para cada uno especifica (si está mencionado):
- Qué debe hacerse
- Quién es responsable (si se menciona)
- Cuándo (si se menciona algún plazo)

Si no hay elementos de acción claros, indica "No se identificaron elementos de acción concretos."

TRANSCRIPCIÓN:
{texto_para_analisis}

ELEMENTOS DE ACCIÓN:"""
    
    resp = cliente.chat.completions.create(
        model=cfg_llm["model"],
        messages=[{"role": "user", "content": prompt_acciones}],
        max_tokens=500
    )
    resultados["elementos_accion"] = resp.choices[0].message.content.strip()
    print(f"     [OK] ({time.time()-inicio:.1f}s)")
    
    # ── Índice por timestamps ─────────────────────────────
    # Crear índice simple a partir de los segmentos
    segmentos = transcripcion.get("segmentos", [])
    if segmentos:
        print("  Generando índice por timestamps...")
        # Tomar 1 segmento cada ~5 minutos
        indice_items = []
        ultimo_min = -5
        for seg in segmentos:
            min_actual = seg.get("start", 0) / 60
            if min_actual - ultimo_min >= 5:
                min_i = int(seg.get("start", 0) // 60)
                seg_i = int(seg.get("start", 0) % 60)
                texto_seg = seg.get("text", "")[:80].strip()
                indice_items.append(f"[{min_i:02d}:{seg_i:02d}] {texto_seg}...")
                ultimo_min = min_actual
        resultados["indice_timestamps"] = "\n".join(indice_items)
    else:
        resultados["indice_timestamps"] = "Timestamps no disponibles"
    
    return resultados


def formatear_informe(transcripcion: dict, analisis: dict) -> str:
    """Genera el informe final en texto plano."""
    nombre = transcripcion["nombre_archivo"]
    duracion_min = int(transcripcion["duracion_audio_seg"] / 60)
    duracion_seg = int(transcripcion["duracion_audio_seg"] % 60)
    palabras = transcripcion["palabras_totales"]
    modelo = transcripcion["modelo"]
    
    separador = "═" * 60
    
    informe = f"""
{separador}
INFORME DE TRANSCRIPCIÓN Y ANÁLISIS
{separador}
Archivo: {nombre}
Duración: {duracion_min} min {duracion_seg} seg
Palabras transcritas: {palabras:,}
Modelo STT: {modelo}
Generado por: Jetson AGX Orin AGX 64GB (JP 7.2)
{separador}

RESUMEN EJECUTIVO
─────────────────
{analisis.get('resumen', 'No disponible')}

PUNTOS CLAVE
────────────
{analisis.get('puntos_clave', 'No disponible')}

ELEMENTOS DE ACCIÓN
───────────────────
{analisis.get('elementos_accion', 'No disponible')}

ÍNDICE POR TIMESTAMPS
─────────────────────
{analisis.get('indice_timestamps', 'No disponible')}

{separador}
TRANSCRIPCIÓN COMPLETA
{separador}
{transcripcion.get('texto_completo', '')}
"""
    return informe.strip()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python 02_analyze.py transcripcion.json [informe_salida.txt]")
        sys.exit(1)
    
    with open(sys.argv[1], encoding="utf-8") as f:
        transcripcion = json.load(f)
    
    analisis = analizar_transcripcion(transcripcion)
    informe = formatear_informe(transcripcion, analisis)
    
    salida = sys.argv[2] if len(sys.argv) > 2 else None
    if salida:
        with open(salida, "w", encoding="utf-8") as f:
            f.write(informe)
        print(f"\n[OK] Informe guardado en: {salida}")
    else:
        print("\n── Primeras 1000 líneas del informe ──")
        for linea in informe.split("\n")[:40]:
            print(linea)
```

---

## 22.6 Script 3 — Envío por Email

```python
# scripts/03_send_email.py
"""
Envía la transcripción y el análisis por email con adjuntos.
Soporta Gmail con App Password.
"""
import json
import smtplib
import sys
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


def cargar_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "settings.json"
    with open(config_path) as f:
        return json.load(f)


def enviar_informe(
    transcripcion: dict,
    analisis: dict,
    informe_txt: str,
    config: dict = None
) -> bool:
    """Envía el informe completo por email."""
    if config is None:
        config = cargar_config()
    
    cfg_smtp = config["smtp"]
    
    nombre = transcripcion["nombre_archivo"]
    duracion_min = int(transcripcion["duracion_audio_seg"] / 60)
    
    # ── Construir el email ────────────────────────────────
    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"[Transcripción] {nombre} ({duracion_min} min)"
    msg["From"] = f"{cfg_smtp['nombre_remitente']} <{cfg_smtp['user']}>"
    msg["To"] = cfg_smtp["destinatario"]
    
    # Cuerpo HTML
    resumen = analisis.get("resumen", "No disponible")
    puntos = analisis.get("puntos_clave", "No disponible")
    acciones = analisis.get("elementos_accion", "No disponible")
    
    cuerpo_html = f"""
<html><body style="font-family: Arial, sans-serif; max-width: 800px;">
<h2> Transcripción: {nombre}</h2>
<p><strong>Duración del audio:</strong> {duracion_min} minutos | 
   <strong>Palabras:</strong> {transcripcion['palabras_totales']:,} |
   <strong>Modelo:</strong> {transcripcion['modelo']}</p>

<hr>
<h3>Resumen Ejecutivo</h3>
<p>{resumen.replace(chr(10), '<br>')}</p>

<hr>
<h3>Puntos Clave</h3>
<p>{puntos.replace(chr(10), '<br>')}</p>

<hr>
<h3>Elementos de Acción</h3>
<p>{acciones.replace(chr(10), '<br>')}</p>

<hr>
<p><small>La transcripción completa se adjunta como archivo .txt</small></p>
<p><small>Generado por Jetson AGX Orin 64GB con JetPack 7.2</small></p>
</body></html>"""
    
    msg.attach(MIMEText(cuerpo_html, "html", "utf-8"))
    
    # Adjuntar transcripción completa
    adjunto = MIMEBase("application", "octet-stream")
    adjunto.set_payload(informe_txt.encode("utf-8"))
    encoders.encode_base64(adjunto)
    nombre_adjunto = nombre.replace(" ", "_").replace(".mp3", "").replace(".wav", "")
    adjunto.add_header(
        "Content-Disposition",
        f"attachment; filename={nombre_adjunto}_transcripcion.txt"
    )
    msg.attach(adjunto)
    
    # ── Enviar ────────────────────────────────────────────
    try:
        print(f"[EMAIL] Enviando a: {cfg_smtp['destinatario']}")
        with smtplib.SMTP(cfg_smtp["host"], cfg_smtp["port"]) as server:
            server.starttls()
            server.login(cfg_smtp["user"], cfg_smtp["password"])
            server.sendmail(
                cfg_smtp["user"],
                cfg_smtp["destinatario"],
                msg.as_string()
            )
        print(f"  [OK] Email enviado correctamente")
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("  [ERROR] Error de autenticación SMTP")
        print("     Para Gmail: use un App Password (no su contraseña normal)")
        print("     Google Account → Seguridad → Contraseñas de aplicaciones")
        return False
    except Exception as e:
        print(f"  [ERROR] Error enviando email: {str(e)}")
        return False
```

---

## 22.7 Orquestador Completo

```bash
# transcription_bot.sh
#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT_AUDIO="${1:-}"
ENVIAR_EMAIL="${2:-si}"  # "si" o "no"

if [ -z "$INPUT_AUDIO" ]; then
  echo "Uso: $0 <audio.mp3|wav|m4a> [si|no (email)]"
  echo "Ejemplos:"
  echo "  $0 input/reunion.mp3          # transcribe y envía por email"
  echo "  $0 input/reunion.mp3 no       # transcribe, guarda localmente"
  exit 1
fi

if [ ! -f "$INPUT_AUDIO" ]; then
  echo "[ERROR] Archivo no encontrado: $INPUT_AUDIO"
  exit 1
fi

NOMBRE=$(basename "$INPUT_AUDIO" | sed 's/\.[^.]*$//')
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_BASE="$SCRIPT_DIR/output/${NOMBRE}_${TIMESTAMP}"
TMP_JSON="${OUTPUT_BASE}_transcripcion.json"
INFORME_TXT="${OUTPUT_BASE}_informe.txt"

# Crear directorio de salida
mkdir -p "$(dirname "$OUTPUT_BASE")"

echo "══════════════════════════════════════════════════════"
echo "  BOT DE TRANSCRIPCIÓN — JETSON AGX ORIN"
echo "  Archivo: $INPUT_AUDIO"
echo "══════════════════════════════════════════════════════"

# ── Activar entorno virtual ────────────────────────────
source ~/venvs/dev/bin/activate

# ── Verificar faster-whisper ──────────────────────────
if ! docker ps | grep -q faster-whisper; then
  echo "[WARN]  faster-whisper no activo — iniciando..."
  pwr-30w
  docker run -d \
    --name faster-whisper \
    --runtime nvidia \
    --restart no \
    --network host \
    -v $HOME/.cache/huggingface:/root/.cache/huggingface \
    -e WHISPER_MODEL=large-v3 \
    dustynv/faster-whisper:1.0.3-r39.2.0
  
  echo "  Esperando que cargue el modelo..."
  until curl -sf http://localhost:8000/v1/models > /dev/null 2>&1; do
    sleep 10; echo "  ..."
  done
  echo "  [OK] faster-whisper listo"
fi

# ── Verificar Ollama ──────────────────────────────────
if ! curl -sf http://localhost:11434/api/version > /dev/null; then
  echo "[WARN]  Ollama no activo — iniciando..."
  sudo systemctl start ollama
  sleep 5
fi

# ── PASO 1: Transcripción (30W — STT) ────────────────
echo ""
echo "PASO 1/3 — Transcribiendo audio..."
pwr-30w
TIEMPO_INICIO=$(date +%s)
python "$SCRIPT_DIR/scripts/01_transcribe.py" "$INPUT_AUDIO" "$TMP_JSON"
TIEMPO_1=$(( $(date +%s) - TIEMPO_INICIO ))
echo "  [TIEMPO]  Transcripción: ${TIEMPO_1}s ($((TIEMPO_1/60)) min)"

# ── PASO 2: Análisis LLM (MAXN — texto largo) ────────
echo ""
echo "PASO 2/3 — Analizando con LLM..."
pwr-maxn
TIEMPO_INICIO=$(date +%s)

python3 - << 'PYTHON_EOF'
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
# Importar scripts
import importlib.util

def load_script(name):
    spec = importlib.util.spec_from_file_location(name, f"scripts/{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

s01 = load_script("01_transcribe")
s02 = load_script("02_analyze")
s03 = load_script("03_send_email")

# Cargar transcripción
import os
tmp_json = os.environ.get("TMP_JSON")
informe_txt = os.environ.get("INFORME_TXT")

with open(tmp_json, encoding="utf-8") as f:
    transcripcion = json.load(f)

# Analizar
analisis = s02.analizar_transcripcion(transcripcion)
informe = s02.formatear_informe(transcripcion, analisis)

# Guardar informe
with open(informe_txt, "w", encoding="utf-8") as f:
    f.write(informe)

# Guardar analisis por separado
with open(tmp_json.replace("_transcripcion.json", "_analisis.json"), "w", encoding="utf-8") as f:
    json.dump(analisis, f, ensure_ascii=False, indent=2)

print(f"\n[OK] Informe guardado: {informe_txt}")

# Enviar email si se solicitó
import sys as _sys
if os.environ.get("ENVIAR_EMAIL", "si").lower() == "si":
    s03.enviar_informe(transcripcion, analisis, informe)
else:
    print("[NOTA] Email desactivado — guardando solo localmente")

PYTHON_EOF

export TMP_JSON="$TMP_JSON"
export INFORME_TXT="$INFORME_TXT"
export ENVIAR_EMAIL="$ENVIAR_EMAIL"

TIEMPO_2=$(( $(date +%s) - TIEMPO_INICIO ))
echo "  [TIEMPO]  Análisis: ${TIEMPO_2}s"

# ── PASO 3: Limpieza ──────────────────────────────────
echo ""
echo "PASO 3/3 — Limpieza del sistema..."
pwr-15w
sync
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

TIEMPO_TOTAL=$(( TIEMPO_1 + TIEMPO_2 ))

echo ""
echo "══════════════════════════════════════════════════════"
echo "  [OK] PROCESO COMPLETADO"
echo "  [FILE] Transcripción: $TMP_JSON"
echo "   Informe: $INFORME_TXT"
echo "  [TIEMPO]  Tiempo total: $((TIEMPO_TOTAL/60)) min $((TIEMPO_TOTAL%60)) seg"
echo "══════════════════════════════════════════════════════"
```

```bash
# Hacer ejecutable
chmod +x transcription_bot.sh

# Ejecutar
./transcription_bot.sh input/reunion_equipo.mp3
```

---

## 22.8 Caso de Uso — Procesamiento por Lotes

Para procesar múltiples archivos automáticamente:

```bash
# batch_transcribe.sh — procesa todos los archivos en el directorio input/
#!/bin/bash

DIRECTORIO_INPUT="$HOME/projects/transcription-bot/input"
PROCESADOS=0
ERRORES=0

for archivo in "$DIRECTORIO_INPUT"/*.{mp3,wav,m4a,ogg} 2>/dev/null; do
  [ -f "$archivo" ] || continue
  
  echo ""
  echo "═══ Procesando: $(basename $archivo) ═══"
  
  if ./transcription_bot.sh "$archivo" "si"; then
    PROCESADOS=$((PROCESADOS+1))
    # Mover a carpeta de procesados para no repetir
    mkdir -p "$DIRECTORIO_INPUT/procesados"
    mv "$archivo" "$DIRECTORIO_INPUT/procesados/"
  else
    ERRORES=$((ERRORES+1))
    echo "[ERROR] Error procesando: $archivo"
  fi
  
  # Esperar 30 segundos entre archivos para enfriar el sistema
  sleep 30
done

echo ""
echo "Resumen: $PROCESADOS procesados correctamente, $ERRORES errores"
```

---

## 22.9 Limpieza Post-Pipeline

```bash
# Después de terminar todas las transcripciones

# Detener faster-whisper
docker stop faster-whisper && docker rm faster-whisper

# Detener Ollama
sudo systemctl stop ollama

# Limpiar caché del sistema
sync && echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

# Verificar memoria liberada
free -h | awk '/^Mem:/{printf "RAM libre: %s de %s\n", $7, $2}'

# Bajar modo energético
pwr-15w
```

---

## 22.10 Verificación Final del Capítulo

```bash
# Verificación
echo "╔════════════════════════════════════════════════════════╗"
echo "║   VERIFICACIÓN CAPÍTULO 20 — TRANSCRIPTION BOT        ║"
echo "╚════════════════════════════════════════════════════════╝"

source ~/venvs/dev/bin/activate

echo ""
echo "── Python dependencies ──"
python -c "
import importlib
for mod, pkg in [('openai','openai'),('requests','requests'),('smtplib',None),('email',None)]:
    try:
        importlib.import_module(mod)
        print(f'  [OK] {mod}')
    except ImportError:
        print(f'  ○  {mod} → pip install {pkg}' if pkg else f'  ○  {mod} (builtin missing)')
"

echo ""
echo "── Servicios ──"
curl -sf http://localhost:8000/v1/models > /dev/null 2>&1 \
  && echo "  [OK] faster-whisper activo (port 8000)" \
  || echo "  ○  faster-whisper offline (ver §20.1)"
curl -sf http://localhost:11434/api/version > /dev/null \
  && echo "  [OK] Ollama activo (port 11434)" \
  || echo "  ○  Ollama offline"

echo ""
echo "── Configuración SMTP ──"
[ -f ~/projects/transcription-bot/config/settings.json ] \
  && echo "  [OK] settings.json existe" \
  || echo "  ○  Crear ~/projects/transcription-bot/config/settings.json (ver §20.3)"

echo ""
echo "════════════════════════════════════════════════════════"
```

---

## 22.11 Escalabilidad — Workflow de Transcripción vía Telegram

El bot de transcripción puede integrarse con Telegram para operar de forma completamente autónoma: el usuario envía la grabación de una reunión o clase y recibe la transcripción detallada o el resumen en su chat, en el formato que prefiera.

### 22.11.1 Flujo Telegram → Jetson → Resumen

```bash
Usuario → envía audio .mp3/.wav/.ogg por Telegram
          ↓
N8N / OpenClaw recibe el archivo
          ↓
Guarda en ~/projects/transcription-bot/input/
          ↓
Ejecuta pipeline: faster-whisper → Ollama análisis
          ↓
Genera resumen en Markdown / DOCX / PDF
          ↓
Envía documento de vuelta al chat de Telegram
```

**Implementación con N8N** (ver Capítulo 14):

```yaml
Nodo 1 — Telegram Trigger:
  tipo: telegram_trigger
  evento: message_received
  filtro: audio, voice, document (.mp3 .wav .ogg .m4a)

Nodo 2 — Save File:
  tipo: write_binary_file
  ruta: /home/jetson/projects/transcription-bot/input/{{filename}}

Nodo 3 — Execute Command:
  tipo: execute_command
  comando: |
    python3 /home/jetson/projects/transcription-bot/scripts/01_transcribe.py \
      /home/jetson/projects/transcription-bot/input/{{filename}} \
      --output-format markdown
  timeout: 900   # 15 min — reuniones largas

Nodo 4 — Send Document:
  tipo: telegram_send_document
  chat_id: {{chat_id}}
  archivo: /home/jetson/projects/transcription-bot/output/{{filename}}.md
  caption: "Transcripción y resumen listos"
```

**Implementación con OpenClaw:**

```json
"hooks": {
  "on_audio_receive": {
    "filter": ["*.mp3", "*.wav", "*.ogg", "*.m4a"],
    "action": "shell",
    "command": "python3 ~/projects/transcription-bot/scripts/01_transcribe.py {{file_path}} --output-format markdown",
    "reply_with_file": "{{output_dir}}/{{basename}}.md"
  }
}
```

### 22.11.2 Formatos de Salida

El script de análisis (§20.5) puede generar la salida en múltiples formatos según el tipo de reunión:

```bash
# Transcripción plana con marcas de tiempo (Markdown)
python3 01_transcribe.py reunion.mp3 --output-format markdown

# Resumen ejecutivo con bullets (Markdown → Word con python-docx)
python3 02_analyze.py reunion_transcript.txt --format docx --style executive

# Reporte estructurado con secciones (ideal para actas)
python3 02_analyze.py reunion_transcript.txt --format pdf --style minutes
```

**Prompt sugerido para el LLM (añadir en `02_analyze.py`):**

```python
PROMPT_RESUMEN = """
Analiza esta transcripción de reunión/clase y genera:

1. **Resumen ejecutivo** (3-5 oraciones)
2. **Puntos clave** (bullets, máximo 10)
3. **Tareas y compromisos** identificados (con responsable si se menciona)
4. **Próximos pasos** acordados

Transcripción:
{transcripcion}
"""
```

### 22.11.3 Modo Mixto con OpenRouter

Para reuniones con vocabulario técnico complejo o cuando el modelo local no genere suficiente calidad de resumen, integre OpenRouter como fallback:

```python
import os
from openai import OpenAI

USE_LOCAL = os.getenv("USE_LOCAL_LLM", "true").lower() == "true"

if USE_LOCAL:
    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    MODEL  = "qwen2.5:14b"
else:
    client = OpenAI(
        base_url=os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1"),
        api_key=os.getenv("OPENROUTER_API_KEY", ""),
    )
    MODEL = "meta-llama/llama-3.3-70b-instruct:free"
```

```bash
# Aliases en ~/.bash_aliases (ver Capítulo 6)
alias transcribe-local="USE_LOCAL_LLM=true  python3 ~/projects/transcription-bot/scripts/02_analyze.py"
alias transcribe-cloud="USE_LOCAL_LLM=false python3 ~/projects/transcription-bot/scripts/02_analyze.py"
```

> **NOTA:** El modo cloud envía el texto de la transcripción a servidores externos. Para reuniones confidenciales use siempre el modo local. La transcripción con faster-whisper siempre ocurre en el Jetson independientemente del modo elegido para el análisis.

---

> **Próximo paso:** El Capítulo 21 construye la Agencia de Turismo IA — un sistema multi-agente que asesora a viajeros con información actualizada y genera itinerarios personalizados.
