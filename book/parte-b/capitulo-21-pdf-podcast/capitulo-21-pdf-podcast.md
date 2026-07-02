# Capítulo 21 — Pipeline PDF a Pódcast: Conversión Offline de Documentos a Audio

## Introducción

Imagine convertir cualquier artículo científico, informe empresarial o libro técnico en un episodio de pódcast de 30–40 minutos — con dos voces distintas que debaten y explican el contenido — completamente offline, sin enviar el documento a ningún servicio en la nube.

Este capítulo construye ese pipeline completo en el Jetson AGX Orin 64GB. El proceso toma un PDF como entrada y produce un archivo MP3 como salida, pasando por extracción de texto, generación de guión con LLM y síntesis de voz con kokoro-tts.

**Prerrequisitos:**
- Capítulo 18 completado (jetson-containers, kokoro-tts disponible)
- Ollama activo con `qwen3:7b` instalado (Capítulo 12)
- `ffmpeg` instalado (`sudo apt install -y ffmpeg`)

**Tiempo de procesamiento estimado por PDF (30 páginas):**
- Extracción de texto: ~5 segundos
- Generación de guión (LLM): ~8–12 minutos
- Síntesis de voz: ~10–15 minutos
- Ensamblaje de audio: ~30 segundos
- **Total: ~20–30 minutos**

**Modo de energía:** MAXN durante todo el pipeline (LLM + TTS — velocidad crítica)

**Al final de este capítulo tendrá:**
- 5 scripts Python que componen el pipeline completo
- Un orquestador bash que los conecta
- Un archivo MP3 listo para reproducir

---

## 19.1 Prerrequisito — Verificación del Sistema

```bash
# Verificar recursos antes de iniciar
check-ready 25 "PDF-to-podcast"

# Activar modo MAXN
pwr-maxn

# Iniciar Ollama si no está activo
sudo systemctl start ollama
ollama list | grep qwen3 || echo "[WARN]  Instale qwen3:7b con: ollama pull qwen3:7b"

# Iniciar kokoro-tts
docker run -d \
  --name kokoro-tts \
  --runtime nvidia \
  --restart no \
  --network host \
  dustynv/kokoro-tts:r39.2.0

# Esperar que inicie
echo "Esperando que kokoro-tts cargue el modelo..."
until curl -sf http://localhost:8880/v1/voices > /dev/null 2>&1; do
  sleep 5
  echo "  ..."
done
echo "[OK] kokoro-tts listo en puerto 8880"
```

---

## 19.2 Estructura del Proyecto

```bash
# Crear la estructura del proyecto
mkdir -p ~/projects/pdf2podcast/{scripts,input,output,tmp}
cd ~/projects/pdf2podcast
```

```
pdf2podcast/
├── scripts/
│   ├── 01_extract_text.py       # Extracción de texto del PDF
│   ├── 02_generate_script.py    # Generación de guión con LLM
│   ├── 03_synthesize_voices.py  # Síntesis de voz con kokoro-tts
│   ├── 04_assemble_podcast.py   # Ensamblaje con ffmpeg
│   └── utils.py                 # Utilidades comunes
├── input/                       # PDFs a convertir
├── output/                      # MP3 finales
└── tmp/                         # Archivos temporales (WAV por segmento)
```

---

## 19.3 Script 1 — Extracción de Texto del PDF

```bash
# Instalar dependencias en el venv de desarrollo
source ~/venvs/dev/bin/activate
pip install pymupdf  # PyMuPDF — librería rápida para extracción de PDF
```

```python
# scripts/01_extract_text.py
"""
Extrae texto de un PDF y lo divide en chunks manejables para el LLM.
Cada chunk es ~1500 palabras (~2000 tokens) con superposición de 150 palabras.
"""
import fitz  # PyMuPDF
import json
import sys
import re
from pathlib import Path


def limpiar_texto(texto: str) -> str:
    """Limpia artefactos comunes de PDFs: headers, footers, columnas mal separadas."""
    # Eliminar números de página sueltos
    texto = re.sub(r'\n\d+\n', '\n', texto)
    # Normalizar espacios múltiples
    texto = re.sub(r' {2,}', ' ', texto)
    # Normalizar saltos de línea múltiples
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    # Eliminar guiones de separación de sílabas al final de línea
    texto = re.sub(r'-\n(\w)', r'\1', texto)
    return texto.strip()


def extraer_pdf(ruta_pdf: str, palabras_por_chunk: int = 1500, superposicion: int = 150) -> dict:
    """
    Extrae texto de un PDF y lo divide en chunks.
    
    Returns:
        dict con 'titulo', 'paginas', 'texto_completo', 'chunks'
    """
    ruta = Path(ruta_pdf)
    if not ruta.exists():
        raise FileNotFoundError(f"PDF no encontrado: {ruta_pdf}")
    
    print(f"[PDF] Extrayendo texto de: {ruta.name}")
    
    doc = fitz.open(ruta_pdf)
    paginas = []
    
    for i, pagina in enumerate(doc, 1):
        texto_pagina = pagina.get_text("text")
        texto_limpio = limpiar_texto(texto_pagina)
        if texto_limpio:
            paginas.append({
                "numero": i,
                "texto": texto_limpio
            })
        
        if i % 10 == 0:
            print(f"  Procesadas {i}/{len(doc)} páginas...")
    
    doc.close()
    
    # Concatenar todo el texto
    texto_completo = "\n\n".join(p["texto"] for p in paginas)
    palabras_totales = len(texto_completo.split())
    
    print(f"  Total: {len(paginas)} páginas, {palabras_totales:,} palabras")
    
    # Dividir en chunks
    palabras = texto_completo.split()
    chunks = []
    inicio = 0
    
    while inicio < len(palabras):
        fin = min(inicio + palabras_por_chunk, len(palabras))
        chunk_texto = " ".join(palabras[inicio:fin])
        chunks.append({
            "indice": len(chunks) + 1,
            "palabras": fin - inicio,
            "texto": chunk_texto
        })
        inicio = fin - superposicion  # superposición para contexto
        if inicio < 0:
            inicio = 0
    
    print(f"  Dividido en {len(chunks)} chunks de ~{palabras_por_chunk} palabras")
    
    return {
        "titulo": ruta.stem,
        "ruta_original": str(ruta),
        "paginas_totales": len(paginas),
        "palabras_totales": palabras_totales,
        "chunks": chunks
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python 01_extract_text.py <archivo.pdf> [archivo_salida.json]")
        sys.exit(1)
    
    ruta_pdf = sys.argv[1]
    salida = sys.argv[2] if len(sys.argv) > 2 else "tmp/extracted.json"
    
    resultado = extraer_pdf(ruta_pdf)
    
    Path(salida).parent.mkdir(parents=True, exist_ok=True)
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    
    print(f"\n[OK] Extracción guardada en: {salida}")
```

```bash
# Probar la extracción con un PDF de muestra
python scripts/01_extract_text.py input/mi_articulo.pdf tmp/extracted.json
```

```
# Salida esperada
[PDF] Extrayendo texto de: mi_articulo.pdf
  Procesadas 10/32 páginas...
  Procesadas 20/32 páginas...
  Procesadas 30/32 páginas...
  Total: 32 páginas, 8,421 palabras
  Dividido en 6 chunks de ~1500 palabras

[OK] Extracción guardada en: tmp/extracted.json
```

---

## 19.4 Script 2 — Generación del Guión con LLM

```python
# scripts/02_generate_script.py
"""
Usa Ollama + qwen3:7b para convertir los chunks de texto
en un guión de pódcast con dos hosts que conversan.
"""
import json
import sys
import time
from pathlib import Path
from openai import OpenAI


SYSTEM_PROMPT = """Eres un productor de pódcast experto. Tu tarea es convertir
texto académico o técnico en un diálogo natural y entretenido entre dos presentadores:

- HOST1 (Ana): Analítica, hace preguntas profundas, explica conceptos técnicos
- HOST2 (Carlos): Pragmático, da ejemplos concretos, conecta con aplicaciones reales

Reglas del guión:
1. El diálogo debe ser NATURAL — no robótico ni académico
2. Máximo 3-4 intercambios por chunk (cada intercambio = 1 HOST1 + 1 HOST2)
3. Cada intervención: 40-80 palabras. No más.
4. Incluir reacciones naturales ("Exactamente", "¡Interesante!", "Claro, y además...")
5. NO incluir indicaciones de escena, [RISAS], [PAUSA], etc.
6. El idioma debe ser el mismo que el texto original

Formato EXACTO de salida (JSON):
[
  {"speaker": "HOST1", "texto": "..."},
  {"speaker": "HOST2", "texto": "..."},
  ...
]
Solo devuelve el JSON. Sin texto adicional."""


def generar_segmento(cliente: OpenAI, texto: str, num_chunk: int, total: int) -> list[dict]:
    """Genera un segmento de guión para un chunk de texto."""
    print(f"  Generando segmento {num_chunk}/{total}...")
    
    user_prompt = f"""Convierte este texto en un diálogo de pódcast:

---
{texto[:2000]}  
---

Recuerda: devuelve SOLO el JSON con el diálogo. Sin explicaciones."""
    
    for intento in range(3):
        try:
            respuesta = cliente.chat.completions.create(
                model="qwen3:7b",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1200,
                temperature=0.7
            )
            
            contenido = respuesta.choices[0].message.content.strip()
            
            # Extraer JSON del contenido
            if "```json" in contenido:
                contenido = contenido.split("```json")[1].split("```")[0].strip()
            elif "```" in contenido:
                contenido = contenido.split("```")[1].split("```")[0].strip()
            
            segmento = json.loads(contenido)
            
            # Validar estructura
            if isinstance(segmento, list) and all(
                isinstance(s, dict) and "speaker" in s and "texto" in s
                for s in segmento
            ):
                return segmento
            
        except (json.JSONDecodeError, Exception) as e:
            print(f"    [WARN]  Intento {intento+1}/3 falló: {str(e)[:50]}")
            time.sleep(2)
    
    # Fallback: si el LLM no genera JSON válido, crear diálogo simple
    print(f"    [ALT] Usando fallback para chunk {num_chunk}")
    return [
        {"speaker": "HOST1", "texto": texto[:200] + "..."},
        {"speaker": "HOST2", "texto": "Muy interesante lo que acabas de comentar. Sigamos con el siguiente punto."}
    ]


def generar_intro(cliente: OpenAI, titulo: str, palabras_totales: int) -> list[dict]:
    """Genera la introducción del pódcast."""
    duracion_estimada = max(10, palabras_totales // 150)  # ~150 palabras/min
    
    prompt = f"""Genera una introducción corta de pódcast (2 intercambios = 4 líneas) para:
Título del documento: "{titulo}"
Duración estimada del episodio: {duracion_estimada} minutos

Formato JSON igual que antes. Los hosts se presentan y anuncian el tema."""
    
    return generar_segmento(cliente, prompt, 0, 1)


def generar_cierre(cliente: OpenAI, titulo: str) -> list[dict]:
    """Genera el cierre del pódcast."""
    prompt = f"""Genera un cierre corto de pódcast (2 intercambios) para el episodio sobre "{titulo}".
Los hosts resumen en 1-2 oraciones lo más importante y se despiden."""
    
    return generar_segmento(cliente, prompt, -1, 1)


def generar_guion(extracted_json: str, salida_json: str):
    """Pipeline completo de generación de guión."""
    
    with open(extracted_json, "r", encoding="utf-8") as f:
        datos = json.load(f)
    
    titulo = datos["titulo"]
    chunks = datos["chunks"]
    
    print(f"[LLM] Generando guión de pódcast para: {titulo}")
    print(f"   {len(chunks)} chunks → ~{len(chunks) * 4} intercambios de diálogo")
    
    cliente = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    
    guion_completo = []
    inicio_total = time.time()
    
    # Intro
    print("\n[Intro]")
    guion_completo.extend(generar_intro(cliente, titulo, datos["palabras_totales"]))
    
    # Cuerpo del episodio
    print("\n[Cuerpo]")
    for i, chunk in enumerate(chunks, 1):
        segmento = generar_segmento(cliente, chunk["texto"], i, len(chunks))
        guion_completo.extend(segmento)
        
        elapsed = time.time() - inicio_total
        restante_est = (elapsed / i) * (len(chunks) - i)
        print(f"    Tiempo: {elapsed:.0f}s transcurrido, ~{restante_est:.0f}s restantes")
    
    # Cierre
    print("\n[Cierre]")
    guion_completo.extend(generar_cierre(cliente, titulo))
    
    tiempo_total = time.time() - inicio_total
    
    # Estadísticas
    total_palabras = sum(len(s["texto"].split()) for s in guion_completo)
    duracion_est = total_palabras / 150  # ~150 palabras/minuto
    
    resultado = {
        "titulo": titulo,
        "total_segmentos": len(guion_completo),
        "palabras_totales": total_palabras,
        "duracion_estimada_min": round(duracion_est, 1),
        "tiempo_generacion_seg": round(tiempo_total, 1),
        "guion": guion_completo
    }
    
    Path(salida_json).parent.mkdir(parents=True, exist_ok=True)
    with open(salida_json, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    
    print(f"\n[OK] Guión generado:")
    print(f"   {len(guion_completo)} segmentos de diálogo")
    print(f"   {total_palabras:,} palabras totales")
    print(f"   Duración estimada: {duracion_est:.1f} minutos")
    print(f"   Tiempo de generación: {tiempo_total:.1f} segundos")
    print(f"   Guardado en: {salida_json}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python 02_generate_script.py tmp/extracted.json [tmp/script.json]")
        sys.exit(1)
    
    extracted = sys.argv[1]
    salida = sys.argv[2] if len(sys.argv) > 2 else "tmp/script.json"
    generar_guion(extracted, salida)
```

```bash
# Ejecutar generación de guión (tarda 8-12 min para un PDF de 30 páginas)
python scripts/02_generate_script.py tmp/extracted.json tmp/script.json
```

```
# Salida esperada
[LLM] Generando guión de pódcast para: mi_articulo
   6 chunks → ~24 intercambios de diálogo

[Intro]
  Generando segmento 0/1...

[Cuerpo]
  Generando segmento 1/6...
    Tiempo: 95s transcurrido, ~475s restantes
  Generando segmento 2/6...
    Tiempo: 187s transcurrido, ~374s restantes
  ...

[OK] Guión generado:
   28 segmentos de diálogo
   4,215 palabras totales
   Duración estimada: 28.1 minutos
   Tiempo de generación: 587.3 segundos
   Guardado en: tmp/script.json
```

---

## 19.5 Script 3 — Síntesis de Voz con kokoro-tts

```python
# scripts/03_synthesize_voices.py
"""
Convierte cada segmento del guión a audio WAV usando kokoro-tts.
HOST1 → voz af_bella (femenina americana)
HOST2 → voz bm_george (masculina británica)
"""
import json
import sys
import time
import requests
from pathlib import Path


VOCES = {
    "HOST1": "af_bella",   # Ana — analítica
    "HOST2": "bm_george",  # Carlos — pragmático
}

TTS_BASE_URL = "http://localhost:8880"


def verificar_kokoro() -> bool:
    """Verifica que el servidor kokoro-tts está activo."""
    try:
        resp = requests.get(f"{TTS_BASE_URL}/v1/voices", timeout=5)
        return resp.status_code == 200
    except:
        return False


def sintetizar_segmento(texto: str, voz: str, ruta_salida: Path) -> bool:
    """
    Sintetiza un segmento de texto a WAV.
    Returns True si fue exitoso.
    """
    payload = {
        "model": "kokoro",
        "input": texto,
        "voice": voz,
        "response_format": "wav",
        "speed": 1.0
    }
    
    for intento in range(3):
        try:
            resp = requests.post(
                f"{TTS_BASE_URL}/v1/audio/speech",
                json=payload,
                timeout=120
            )
            
            if resp.status_code == 200:
                ruta_salida.parent.mkdir(parents=True, exist_ok=True)
                ruta_salida.write_bytes(resp.content)
                return True
            else:
                print(f"    [WARN]  HTTP {resp.status_code}: {resp.text[:100]}")
                
        except requests.Timeout:
            print(f"    [WARN]  Timeout en intento {intento+1}/3")
        except Exception as e:
            print(f"    [WARN]  Error en intento {intento+1}/3: {str(e)[:60]}")
        
        time.sleep(3)
    
    return False


def sintetizar_guion(script_json: str, dir_tmp: str = "tmp") -> list[Path]:
    """
    Sintetiza todos los segmentos del guión.
    Returns: lista de rutas a archivos WAV en orden.
    """
    with open(script_json, "r", encoding="utf-8") as f:
        datos = json.load(f)
    
    guion = datos["guion"]
    titulo = datos["titulo"]
    
    print(f"[MIC] Sintetizando {len(guion)} segmentos de voz para: {titulo}")
    
    if not verificar_kokoro():
        print("[ERROR] kokoro-tts no está disponible en el puerto 8880")
        print("   Ejecute: docker run -d --name kokoro-tts --runtime nvidia")
        print("           --restart no --network host dustynv/kokoro-tts:r39.2.0")
        sys.exit(1)
    
    print("[OK] kokoro-tts activo")
    print(f"   Voces: HOST1={VOCES['HOST1']}, HOST2={VOCES['HOST2']}")
    
    archivos_wav = []
    inicio_total = time.time()
    errores = 0
    
    for i, segmento in enumerate(guion, 1):
        speaker = segmento.get("speaker", "HOST1")
        texto = segmento.get("texto", "").strip()
        voz = VOCES.get(speaker, "af_bella")
        
        if not texto:
            continue
        
        ruta_wav = Path(dir_tmp) / f"seg_{i:04d}_{speaker.lower()}.wav"
        
        print(f"  [{i:3d}/{len(guion)}] {speaker} ({voz}): {texto[:50]}...")
        
        if sintetizar_segmento(texto, voz, ruta_wav):
            archivos_wav.append(ruta_wav)
        else:
            print(f"  [ERROR] Falló segmento {i} — saltando")
            errores += 1
    
    tiempo_total = time.time() - inicio_total
    
    print(f"\n[OK] Síntesis completada:")
    print(f"   {len(archivos_wav)} archivos WAV generados ({errores} errores)")
    print(f"   Tiempo total: {tiempo_total:.1f} segundos")
    
    # Guardar lista de archivos
    lista_path = Path(dir_tmp) / "wav_list.txt"
    with open(lista_path, "w") as f:
        for wav in archivos_wav:
            f.write(f"{wav.absolute()}\n")
    
    print(f"   Lista guardada en: {lista_path}")
    return archivos_wav


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python 03_synthesize_voices.py tmp/script.json [tmp/]")
        sys.exit(1)
    
    script_json = sys.argv[1]
    dir_tmp = sys.argv[2] if len(sys.argv) > 2 else "tmp"
    sintetizar_guion(script_json, dir_tmp)
```

---

## 19.6 Script 4 — Ensamblaje Final con ffmpeg

```python
# scripts/04_assemble_podcast.py
"""
Ensambla todos los archivos WAV en un solo MP3 con pausas naturales entre intervenciones.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def obtener_duracion_wav(ruta_wav: Path) -> float:
    """Obtiene la duración en segundos de un archivo WAV usando ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(ruta_wav)],
            capture_output=True, text=True, timeout=10
        )
        return float(result.stdout.strip())
    except:
        return 0.0


def generar_silencio(duracion_seg: float, ruta_salida: Path):
    """Genera un archivo WAV de silencio de la duración indicada."""
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=22050:cl=mono",
        "-t", str(duracion_seg), "-ar", "22050", "-ac", "1",
        str(ruta_salida)
    ], capture_output=True)


def ensamblar_podcast(dir_tmp: str, ruta_salida: str, titulo: str = "podcast"):
    """
    Ensambla los WAV en un MP3 final.
    
    Pausa entre HOST1→HOST2: 0.4 segundos
    Pausa entre HOST2→HOST1: 0.6 segundos (cambio de tema)
    """
    dir_tmp_path = Path(dir_tmp)
    lista_path = dir_tmp_path / "wav_list.txt"
    
    if not lista_path.exists():
        print(f"[ERROR] No se encontró: {lista_path}")
        print("   Ejecute primero: python 03_synthesize_voices.py")
        sys.exit(1)
    
    with open(lista_path) as f:
        archivos_wav = [Path(l.strip()) for l in f if l.strip()]
    
    archivos_wav = [p for p in archivos_wav if p.exists()]
    
    if not archivos_wav:
        print("[ERROR] No se encontraron archivos WAV")
        sys.exit(1)
    
    print(f"[TTS] Ensamblando {len(archivos_wav)} segmentos de audio...")
    
    # Construir lista de concatenación con silencios
    segmentos_con_pausas = []
    anterior_speaker = None
    
    for i, wav_path in enumerate(archivos_wav):
        # Determinar el speaker por el nombre del archivo
        nombre = wav_path.stem
        speaker_actual = "HOST1" if "host1" in nombre else "HOST2"
        
        # Agregar pausa antes de cada segmento (excepto el primero)
        if anterior_speaker is not None:
            if anterior_speaker != speaker_actual:
                pausa = 0.6  # pausa más larga en cambio de hablante
            else:
                pausa = 0.3  # pausa corta (no debería ocurrir, pero por si acaso)
            
            silencio_path = dir_tmp_path / f"silencio_{i:04d}.wav"
            generar_silencio(pausa, silencio_path)
            segmentos_con_pausas.append(silencio_path)
        
        segmentos_con_pausas.append(wav_path)
        anterior_speaker = speaker_actual
    
    # Crear archivo de lista para ffmpeg
    lista_ffmpeg = dir_tmp_path / "ffmpeg_concat.txt"
    with open(lista_ffmpeg, "w") as f:
        for seg in segmentos_con_pausas:
            f.write(f"file '{seg.absolute()}'\n")
    
    # Concatenar con ffmpeg
    ruta_wav_final = dir_tmp_path / "podcast_combined.wav"
    
    print("  Concatenando segmentos...")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(lista_ffmpeg),
        "-ar", "22050", "-ac", "1",
        str(ruta_wav_final)
    ], capture_output=True, check=True)
    
    # Convertir a MP3 con metadatos
    print("  Convirtiendo a MP3...")
    Path(ruta_salida).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(ruta_wav_final),
        "-codec:a", "libmp3lame", "-b:a", "128k",
        "-metadata", f"title={titulo}",
        "-metadata", "artist=Jetson PDF Podcast",
        "-metadata", "album=AI Generated Podcast",
        ruta_salida
    ], capture_output=True, check=True)
    
    # Obtener duración final
    duracion = obtener_duracion_wav(ruta_wav_final)
    min_dur = int(duracion // 60)
    seg_dur = int(duracion % 60)
    tamanio_mb = Path(ruta_salida).stat().st_size / 1024 / 1024
    
    print(f"\n[OK] Pódcast ensamblado:")
    print(f"   Duración: {min_dur} minutos, {seg_dur} segundos")
    print(f"   Tamaño: {tamanio_mb:.1f} MB")
    print(f"   Guardado en: {ruta_salida}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python 04_assemble_podcast.py tmp/ output/podcast.mp3 [Título]")
        sys.exit(1)
    
    dir_tmp = sys.argv[1]
    salida = sys.argv[2]
    titulo = sys.argv[3] if len(sys.argv) > 3 else "Podcast"
    ensamblar_podcast(dir_tmp, salida, titulo)
```

---

## 19.7 Orquestador Completo

```bash
# pdf2podcast.sh — ejecuta el pipeline completo
#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT_PDF="${1:-}"
OUTPUT_DIR="${2:-$SCRIPT_DIR/output}"

# ── Validaciones ──────────────────────────────────────────
if [ -z "$INPUT_PDF" ]; then
  echo "Uso: $0 <archivo.pdf> [directorio_salida]"
  echo "Ejemplo: $0 input/articulo.pdf output/"
  exit 1
fi

if [ ! -f "$INPUT_PDF" ]; then
  echo "[ERROR] PDF no encontrado: $INPUT_PDF"
  exit 1
fi

TITULO=$(basename "$INPUT_PDF" .pdf)
TMP_DIR="$SCRIPT_DIR/tmp/${TITULO}_$(date +%Y%m%d_%H%M%S)"
SALIDA_MP3="$OUTPUT_DIR/${TITULO}_podcast.mp3"

mkdir -p "$TMP_DIR" "$OUTPUT_DIR"

# ── Verificar prerrequisitos ───────────────────────────────
echo "══════════════════════════════════════════════════"
echo "  PDF → PODCAST PIPELINE"
echo "  PDF: $TITULO"
echo "  Salida: $SALIDA_MP3"
echo "══════════════════════════════════════════════════"
echo ""

# Modo energético
pwr-maxn

# Verificar Ollama
if ! curl -sf http://localhost:11434/api/version > /dev/null; then
  echo "[WARN]  Ollama no activo — iniciando..."
  sudo systemctl start ollama
  sleep 5
fi

# Verificar kokoro-tts
if ! curl -sf http://localhost:8880/v1/voices > /dev/null 2>&1; then
  echo "[WARN]  kokoro-tts no activo — iniciando..."
  docker run -d \
    --name kokoro-tts \
    --runtime nvidia \
    --restart no \
    --network host \
    dustynv/kokoro-tts:r39.2.0
  
  echo "  Esperando que cargue..."
  until curl -sf http://localhost:8880/v1/voices > /dev/null 2>&1; do
    sleep 5
    echo "  ..."
  done
  echo "  [OK] kokoro-tts listo"
fi

# Activar entorno virtual
source ~/venvs/dev/bin/activate

# ── Paso 1: Extracción ────────────────────────────────────
echo ""
echo "PASO 1/4 — Extrayendo texto del PDF..."
TIEMPO_INICIO=$(date +%s)
python "$SCRIPT_DIR/scripts/01_extract_text.py" \
  "$INPUT_PDF" \
  "$TMP_DIR/extracted.json"
TIEMPO_1=$(( $(date +%s) - TIEMPO_INICIO ))
echo "  [TIEMPO]  Completado en ${TIEMPO_1}s"

# ── Paso 2: Generación de guión ───────────────────────────
echo ""
echo "PASO 2/4 — Generando guión con LLM..."
TIEMPO_INICIO=$(date +%s)
python "$SCRIPT_DIR/scripts/02_generate_script.py" \
  "$TMP_DIR/extracted.json" \
  "$TMP_DIR/script.json"
TIEMPO_2=$(( $(date +%s) - TIEMPO_INICIO ))
echo "  [TIEMPO]  Completado en ${TIEMPO_2}s ($((TIEMPO_2/60)) min)"

# ── Paso 3: Síntesis de voz ───────────────────────────────
echo ""
echo "PASO 3/4 — Sintetizando voces..."
TIEMPO_INICIO=$(date +%s)
python "$SCRIPT_DIR/scripts/03_synthesize_voices.py" \
  "$TMP_DIR/script.json" \
  "$TMP_DIR"
TIEMPO_3=$(( $(date +%s) - TIEMPO_INICIO ))
echo "  [TIEMPO]  Completado en ${TIEMPO_3}s ($((TIEMPO_3/60)) min)"

# ── Paso 4: Ensamblaje ────────────────────────────────────
echo ""
echo "PASO 4/4 — Ensamblando MP3 final..."
TIEMPO_INICIO=$(date +%s)
python "$SCRIPT_DIR/scripts/04_assemble_podcast.py" \
  "$TMP_DIR" \
  "$SALIDA_MP3" \
  "$TITULO"
TIEMPO_4=$(( $(date +%s) - TIEMPO_INICIO ))
echo "  [TIEMPO]  Completado en ${TIEMPO_4}s"

# ── Resumen ───────────────────────────────────────────────
TIEMPO_TOTAL=$(( TIEMPO_1 + TIEMPO_2 + TIEMPO_3 + TIEMPO_4 ))
echo ""
echo "══════════════════════════════════════════════════"
echo "  [OK] PODCAST GENERADO"
echo "  [FILE] Archivo: $SALIDA_MP3"
echo "  [TIEMPO]  Tiempo total: $((TIEMPO_TOTAL/60)) min $((TIEMPO_TOTAL%60)) seg"
echo "══════════════════════════════════════════════════"

# Limpiar temporales del sistema
sync
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

# Bajar modo energético
pwr-30w
```

```bash
# Instalar y hacer ejecutable
chmod +x pdf2podcast.sh

# Ejecutar con un PDF
./pdf2podcast.sh input/mi_articulo.pdf
```

```bash
# Monitoreo mientras el pipeline corre (en una segunda terminal SSH)
jtop
docker logs kokoro-tts --follow
docker stats kokoro-tts --no-stream
```

---

## 19.8 Limpieza Post-Pipeline

```bash
# Limpieza después de generar el podcast

# 1. Detener kokoro-tts (libera ~2 GB RAM)
docker stop kokoro-tts && docker rm kokoro-tts

# 2. Si Ollama ya no se necesita
sudo systemctl stop ollama

# 3. Limpiar archivos temporales del pipeline
# rm -rf ~/projects/pdf2podcast/tmp/

# 4. Verificar que la memoria quedó libre
free -h | awk '/^Mem:/{printf "RAM libre: %s de %s\n", $7, $2}'

# 5. Bajar modo energético
pwr-15w

echo "[OK] Limpieza completada"
```

---

## 19.9 Verificación Final del Capítulo

```bash
# Verificación de instalación del pipeline
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║       VERIFICACIÓN CAPÍTULO 19 — PDF-TO-PODCAST           ║"
echo "╚═══════════════════════════════════════════════════════════╝"

source ~/venvs/dev/bin/activate

echo ""
echo "── Dependencias Python ──"
python -c "
import importlib
libs = [('fitz', 'pymupdf'), ('openai', 'openai'), ('requests', 'requests'), ('json', None)]
for mod, pkg in libs:
    try:
        importlib.import_module(mod)
        print(f'  [OK] {mod}')
    except ImportError:
        install = f'pip install {pkg}' if pkg else 'builtin'
        print(f'  ○  {mod} → {install}')
"

echo ""
echo "── ffmpeg ──"
ffmpeg -version 2>/dev/null | head -1 | awk '{printf "  [OK] %s\n", $0}' \
  || echo "  ○  ffmpeg no instalado — sudo apt install -y ffmpeg"

echo ""
echo "── Servicios de inferencia ──"
curl -sf http://localhost:11434/api/version > /dev/null \
  && echo "  [OK] Ollama activo" || echo "  ○  Ollama offline (sudo systemctl start ollama)"
curl -sf http://localhost:8880/v1/voices > /dev/null 2>&1 \
  && echo "  [OK] kokoro-tts activo" || echo "  ○  kokoro-tts offline (ver §19.1)"

echo ""
echo "── Scripts del pipeline ──"
for s in 01_extract_text.py 02_generate_script.py 03_synthesize_voices.py 04_assemble_podcast.py; do
  [ -f ~/projects/pdf2podcast/scripts/$s ] \
    && echo "  [OK] $s" \
    || echo "  ○  $s → copiar de este capítulo"
done

echo ""
echo "═════════════════════════════════════════════════════════════"
```

---

## 19.10 Escalabilidad y Extensiones

El pipeline PDF-to-Podcast puede integrarse con plataformas de mensajería y APIs externas para operar de forma completamente autónoma.

### 19.10.1 Bot de Telegram para PDF-to-Podcast

Con **N8N** (ver Capítulo 14) u **OpenClaw** (ver Capítulo 11A), cualquier usuario puede enviar un PDF a un bot de Telegram y recibir el episodio de audio sin tocar el Jetson.

**Flujo de integración:**

```
Usuario → envía PDF por Telegram
         ↓
N8N / OpenClaw recibe el archivo
         ↓
Guarda en ~/projects/pdf2podcast/input/
         ↓
Ejecuta pdf2podcast.sh (3–8 min según tamaño)
         ↓
Envía MP3 resultante de vuelta al chat de Telegram
```

**Implementación con N8N:**

```yaml
# Flujo N8N: Telegram → Jetson → Audio
Nodo 1 — Telegram Trigger:
  tipo: telegram_trigger
  evento: message_received
  filtro: documentos (.pdf)

Nodo 2 — Save File:
  tipo: write_binary_file
  ruta: /home/jetson/projects/pdf2podcast/input/{{filename}}

Nodo 3 — Execute Command:
  tipo: execute_command
  comando: /home/jetson/projects/pdf2podcast/pdf2podcast.sh \
           /home/jetson/projects/pdf2podcast/input/{{filename}}
  timeout: 600   # segundos — PDFs largos pueden tardar

Nodo 4 — Send Audio:
  tipo: telegram_send_audio
  chat_id: {{chat_id}}
  archivo: /home/jetson/projects/pdf2podcast/output/{{titulo}}.mp3
  caption: "Podcast generado con IA en el Jetson"
```

**Implementación con OpenClaw:**

Añada este bloque de hooks en su `openclaw.json` (ver §11A.4.2 para la estructura completa):

```json
"hooks": {
  "on_file_receive": {
    "filter": "*.pdf",
    "action": "shell",
    "command": "/home/jetson/projects/pdf2podcast/pdf2podcast.sh {{file_path}}",
    "reply_with_file": "{{output_dir}}/{{titulo}}.mp3"
  }
}
```

> **NOTA:** El tiempo de procesamiento depende del tamaño del PDF y del modelo elegido. Para PDFs de 10–20 páginas espere entre 3 y 8 minutos. Configure el timeout del bot en consecuencia para evitar que el usuario reciba un error por tiempo de espera antes de que el audio esté listo.

### 19.10.2 Modo Mixto Offline + Online con OpenRouter

Para PDFs extensos o cuando se requiera mayor calidad narrativa en el guión, puede alternar entre el LLM local (Ollama o vLLM en el Jetson) y modelos externos gratuitos vía **OpenRouter**.

**Configurar las credenciales de OpenRouter:**

```bash
# Registrarse en https://openrouter.ai y generar una API key
# Añadir al ~/.bash_aliases (ver Capítulo 6):
export OPENROUTER_API_KEY="sk-or-v1-xxxxxxxxxxxxxxxx"
export OPENROUTER_URL="https://openrouter.ai/api/v1"

# Aliases para alternar el backend del pipeline
alias pdf2podcast-local="USE_LOCAL_LLM=true  ~/projects/pdf2podcast/pdf2podcast.sh"
alias pdf2podcast-cloud="USE_LOCAL_LLM=false ~/projects/pdf2podcast/pdf2podcast.sh"
```

**Modificar `02_generate_script.py` para soportar ambos backends:**

```python
import os
from openai import OpenAI

USE_LOCAL = os.getenv("USE_LOCAL_LLM", "true").lower() == "true"

if USE_LOCAL:
    # Backend: Ollama en el Jetson (sin costo, sin red)
    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    MODEL  = "qwen2.5:14b"
else:
    # Backend: OpenRouter — modelos de alta calidad con cuota gratuita
    client = OpenAI(
        base_url=os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1"),
        api_key=os.getenv("OPENROUTER_API_KEY", ""),
    )
    MODEL = "meta-llama/llama-3.3-70b-instruct:free"  # gratuito en OpenRouter
```

> **CONSEJO:** Use el modo local para PDFs técnicos de menos de 30 páginas. Cambie al modo cloud para documentos extensos o cuando necesite mayor coherencia narrativa. La lista de modelos con cuota gratuita vigente está en `https://openrouter.ai/models?order=top-weekly&max_price=0`.

**Comparativa de configuraciones:**

| Configuración | Calidad de guión | Velocidad (20 pág.) | Costo |
|---|---|---|---|
| Ollama local — qwen2.5:14b | Alta | 3–5 min | Gratis |
| vLLM local — mistral-7b | Media-Alta | 1–2 min | Gratis |
| OpenRouter — llama-3.3-70b | Muy Alta | 30–60 seg | Cuota gratuita |

> **ADVERTENCIA:** El modo cloud requiere conexión a Internet y que el PDF no contenga información confidencial, ya que el texto extraído se envía a servidores externos.

---

> **Próximo paso:** El Capítulo 20 extiende el uso de faster-whisper para construir un bot de transcripción y análisis automático de reuniones, entregando el resultado por email.
