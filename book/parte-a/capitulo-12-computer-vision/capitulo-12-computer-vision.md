# Capítulo 12 — Computer Vision y OCR: Visión Artificial con GPU

## Introducción

El Jetson AGX Orin 64GB tiene una GPU Ampere (sm_87) con 2048 CUDA cores diseñada específicamente para inferencia de visión artificial. A diferencia de un servidor con GPU dedicada, la memoria unificada del Jetson permite procesar imágenes directamente en la misma memoria que usa el LLM, eliminando la latencia de transferencia CPU↔GPU.

Este capítulo cubre cuatro categorías de visión artificial:

1. **OCR (Reconocimiento Óptico de Caracteres):** pytesseract y EasyOCR para extracción de texto de imágenes y documentos
2. **Modelos de visión-lenguaje:** Gemma 4 E4B para image captioning y VQA (Visual Question Answering)
3. **Detección de objetos:** nanoowl para detección zero-shot en tiempo real con cámara USB/CSI
4. **Procesamiento de video:** OpenCV para captura, preprocesamiento y análisis fotograma por fotograma

**Presupuesto de memoria:**

| Escenario | RAM estimada |
|----------|-------------|
| OS base | ~12 GB |
| + EasyOCR (GPU) | +2 GB = ~14 GB |
| + Gemma 4 E4B via llama.cpp (GGUF Q4_K_M) | +3 GB = ~17 GB |
| + Gemma 4 E4B llama.cpp + EasyOCR simultáneos | ~17 GB total |
| + nanoowl (detección en tiempo real) | +1.5 GB = ~13.5 GB solo |

**Modos energéticos:**
- OCR puro (pytesseract, EasyOCR texto): **30W**
- Modelos de visión-lenguaje (Gemma 4 E4B): **MAXN**
- Detección en tiempo real con nanoowl: **30W** (modelo CLIP optimizado con TensorRT)

> **Prerrequisito:** Docker activo (`docker-on`). Los modelos de visión más grandes requieren `pwr-maxn` y `check-ready` con al menos 40 GB libres.

---

## 28.1 OCR Clásico: Extracción de Texto de Imágenes

### 28.1.1 Pytesseract (CPU, Mínima RAM)

Pytesseract es una interfaz Python para el motor OCR de Google Tesseract. Es el método más rápido para texto en imágenes simples (documentos escaneados, capturas de pantalla con texto claro).

```bash
# Instalar Tesseract y pytesseract
sudo apt install -y tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng

# Verificar instalación
tesseract --version
# Salida esperada: tesseract 5.x.x

# Instalar paquetes de idioma adicionales
sudo apt install -y tesseract-ocr-fra tesseract-ocr-por tesseract-ocr-deu

# Listar idiomas disponibles
tesseract --list-langs
```

```bash
# Instalar pytesseract en el venv LLM
source ~/venvs/llm/bin/activate
pip install pytesseract Pillow opencv-python-headless
```

```python
#!/usr/bin/env python3
"""
ocr_tesseract.py — OCR de imágenes y PDFs con Tesseract
"""
import pytesseract
from PIL import Image, ImageFilter, ImageEnhance
import sys
from pathlib import Path

def mejorar_imagen_para_ocr(ruta: str) -> Image.Image:
    """Preprocesamiento que mejora el reconocimiento de texto."""
    img = Image.open(ruta).convert('L')          # escala de grises
    img = img.filter(ImageFilter.SHARPEN)         # nitidez
    img = ImageEnhance.Contrast(img).enhance(2.0) # aumentar contraste
    return img

def extraer_texto(ruta: str, idioma: str = "spa+eng") -> dict:
    """Extrae texto de una imagen con pytesseract."""
    img = mejorar_imagen_para_ocr(ruta)
    config = "--oem 3 --psm 6"  # OCR Engine 3 (mejor), Page Segmentation 6 (bloque uniforme)
    texto = pytesseract.image_to_string(img, lang=idioma, config=config)
    datos = pytesseract.image_to_data(img, lang=idioma, output_type=pytesseract.Output.DICT)
    confianza_promedio = sum(c for c in datos['conf'] if c > 0) / max(1, sum(1 for c in datos['conf'] if c > 0))
    return {
        "texto": texto.strip(),
        "confianza_promedio": round(confianza_promedio, 1),
        "palabras_detectadas": sum(1 for c in datos['conf'] if c > 0),
        "idioma": idioma
    }

if __name__ == "__main__":
    ruta = sys.argv[1] if len(sys.argv) > 1 else "imagen_test.png"
    resultado = extraer_texto(ruta)
    print(f"Confianza: {resultado['confianza_promedio']}% | Palabras: {resultado['palabras_detectadas']}")
    print("─" * 50)
    print(resultado["texto"])
```

```bash
# Prueba rápida con una imagen de ejemplo
source ~/venvs/llm/bin/activate

# Crear imagen de prueba con texto
python3 -c "
from PIL import Image, ImageDraw, ImageFont
img = Image.new('RGB', (800, 200), color='white')
draw = ImageDraw.Draw(img)
draw.text((50, 50), 'Jetson AGX Orin 64GB — JetPack 7.2\nPrueba de OCR con Tesseract 5.x', fill='black')
img.save('/tmp/test_ocr.png')
print('Imagen de prueba creada')
"

python3 ~/scripts/ocr_tesseract.py /tmp/test_ocr.png
```

```
# Salida esperada:
Confianza: 94.2% | Palabras: 8
──────────────────────────────────────
Jetson AGX Orin 64GB — JetPack 7.2
Prueba de OCR con Tesseract 5.x
```

### 28.1.2 EasyOCR (GPU Acelerada, Mejor para Texto en Imágenes Complejas)

EasyOCR usa redes neuronales con aceleración GPU — más lento en la primera imagen (carga el modelo) pero significativamente mejor para texto rotado, con fondos complejos o en múltiples idiomas simultáneos.

```bash
# Instalar EasyOCR con soporte GPU
source ~/venvs/llm/bin/activate
pip install easyocr

# Primera ejecución descarga los modelos (~500 MB)
# Tarda 3-5 minutos
python3 -c "
import easyocr
reader = easyocr.Reader(['es', 'en'], gpu=True)
print('[OK] EasyOCR inicializado con GPU')
print('Modelos guardados en ~/.EasyOCR/')
"
```

```python
#!/usr/bin/env python3
"""
ocr_easyocr.py — OCR con aceleración GPU
"""
import easyocr
import cv2
import sys
import json
from pathlib import Path

# Inicializar lector (carga modelos en GPU — ~2 GB VRAM primera vez)
reader = easyocr.Reader(['es', 'en', 'fr'], gpu=True)

def ocr_imagen(ruta: str, umbral_confianza: float = 0.5) -> dict:
    """Extrae texto de imagen con EasyOCR GPU."""
    resultados = reader.readtext(ruta, detail=1, paragraph=False)
    textos = []
    for (bbox, texto, confianza) in resultados:
        if confianza >= umbral_confianza:
            textos.append({
                "texto": texto,
                "confianza": round(confianza, 3),
                "bbox": [[int(p[0]), int(p[1])] for p in bbox]
            })
    texto_completo = " ".join(t["texto"] for t in textos)
    return {
        "texto_completo": texto_completo,
        "detecciones": textos,
        "total_detecciones": len(textos)
    }

def visualizar_ocr(ruta_entrada: str, ruta_salida: str = None) -> None:
    """Dibuja bounding boxes sobre la imagen con el texto detectado."""
    import numpy as np
    img = cv2.imread(ruta_entrada)
    resultados = reader.readtext(ruta_entrada)
    for (bbox, texto, confianza) in resultados:
        puntos = np.array(bbox, dtype=np.int32)
        cv2.polylines(img, [puntos], True, (0, 255, 0), 2)
        x, y = int(bbox[0][0]), int(bbox[0][1]) - 10
        cv2.putText(img, f"{texto} ({confianza:.2f})", (x, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    out_path = ruta_salida or ruta_entrada.replace(".", "_ocr.")
    cv2.imwrite(out_path, img)
    print(f"[OK] Imagen con anotaciones: {out_path}")

if __name__ == "__main__":
    ruta = sys.argv[1] if len(sys.argv) > 1 else "/tmp/test_ocr.png"
    resultado = ocr_imagen(ruta)
    print(f"Detecciones: {resultado['total_detecciones']}")
    print(f"Texto: {resultado['texto_completo']}")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
```

```bash
# Ejecutar OCR con GPU
source ~/venvs/llm/bin/activate
python3 ~/scripts/ocr_easyocr.py /tmp/test_ocr.png
```

---

## 28.2 Pipeline OCR → LLM (Extracción Estructurada)

Combine OCR con el LLM local para extraer información estructurada de documentos:

```python
#!/usr/bin/env python3
"""
ocr_llm_pipeline.py — OCR de factura/documento → extracción JSON via LLM
Modo energético: 30W para EasyOCR, MAXN si se activa modelo LLM grande
"""
import easyocr
import requests
import json
import sys

reader = easyocr.Reader(['es', 'en'], gpu=True)

def extraer_texto_imagen(ruta: str) -> str:
    resultados = reader.readtext(ruta, detail=0, paragraph=True)
    return "\n".join(resultados)

def extraer_campos_con_llm(texto: str, tipo_documento: str = "factura") -> dict:
    """Envía el texto OCR al LLM y pide extracción de campos en JSON."""
    prompts = {
        "factura": "Extrae los siguientes campos de esta factura en JSON: numero_factura, fecha, proveedor, cliente, subtotal, iva, total_a_pagar. Si un campo no está presente, usa null.",
        "contrato": "Extrae en JSON: partes_involucradas[], fecha_inicio, fecha_fin, objeto_contrato, monto_total, clausulas_clave[]",
        "formulario": "Extrae todos los campos del formulario en JSON como pares clave-valor. Infiere el tipo de dato (string, number, date)."
    }
    instruccion = prompts.get(tipo_documento, "Extrae la información principal en JSON estructurado.")

    payload = {
        "model": "qwen35",
        "messages": [
            {"role": "system", "content": f"Eres un extractor de información de documentos. {instruccion} Responde SOLO con el JSON, sin explicación adicional."},
            {"role": "user", "content": f"Texto del documento:\n\n{texto}"}
        ],
        "max_tokens": 800,
        "temperature": 0.1  # temperatura baja para extracción precisa
    }

    try:
        resp = requests.post("http://localhost:8000/v1/chat/completions",
                           json=payload, timeout=60)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        # Intentar parsear el JSON de la respuesta
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
        return {"raw_response": content}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 ocr_llm_pipeline.py <imagen> [tipo: factura|contrato|formulario]")
        sys.exit(1)

    ruta = sys.argv[1]
    tipo = sys.argv[2] if len(sys.argv) > 2 else "factura"

    print(f"Procesando {ruta} como '{tipo}'...")
    texto = extraer_texto_imagen(ruta)
    print(f"Texto OCR extraído ({len(texto)} caracteres):\n{texto[:500]}...\n")

    print("Enviando al LLM para extracción estructurada...")
    campos = extraer_campos_con_llm(texto, tipo)
    print("Campos extraídos:")
    print(json.dumps(campos, indent=2, ensure_ascii=False))
```

```bash
# Guardar y ejecutar el pipeline
# Prerrequisito: vLLM activo (start-qwen4b o start-qwen35)
source ~/venvs/llm/bin/activate
python3 ~/scripts/ocr_llm_pipeline.py /ruta/a/factura.jpg factura
```

---

## 28.3 Modelos de Visión-Lenguaje (VLM)

### 28.3.1 Gemma 4 E4B via llama.cpp (Image Captioning Offline, Solo 3 GB)

La opción más eficiente para image captioning y VQA (Visual Question Answering) en el Jetson:

```bash
# Iniciar Gemma 4 E4B via llama.cpp
pwr-30w
docker-on

docker run --runtime nvidia -d \
  --name gemma4-e4b-llama \
  --restart no \
  --network host \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/llama_cpp:latest-jetson-orin \
  llama-server \
    -hf unsloth/gemma-4-E4B:Q4_K_M \
    --ctx-size 32768 \
    --n-gpu-layers 999 \
    --port 8080 \
    --alias gemma4-e4b \
    --host 0.0.0.0

echo -n "Esperando Gemma 4 E4B"
until curl -sf http://localhost:8080/v1/models > /dev/null; do echo -n "."; sleep 15; done
echo " [OK] (~3GB, listo para image captioning)"

# Ver logs de arranque
docker logs gemma4-e4b-llama --follow &
```

```python
#!/usr/bin/env python3
"""
image_captioning.py — Image captioning y VQA con Gemma 4 E4B via llama.cpp
Usar con: source ~/venvs/llm/bin/activate
"""
import base64
import requests
import sys
from pathlib import Path

def imagen_a_base64(ruta: str) -> tuple[str, str]:
    """Convierte imagen a base64 con tipo MIME."""
    ext = Path(ruta).suffix.lower().lstrip('.')
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
            "webp": "image/webp", "gif": "image/gif"}.get(ext, "image/jpeg")
    with open(ruta, "rb") as f:
        return base64.b64encode(f.read()).decode(), mime

def analizar_imagen(ruta: str, pregunta: str, port: int = 8080) -> str:
    """Analiza imagen usando el VLM activo en llama.cpp."""
    img_b64, mime = imagen_a_base64(ruta)
    payload = {
        "model": "gemma4-e4b",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}},
                {"type": "text", "text": pregunta}
            ]
        }],
        "max_tokens": 500,
        "temperature": 0.3
    }
    resp = requests.post(f"http://localhost:{port}/v1/chat/completions",
                        json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

# Casos de uso típicos
def describir_imagen(ruta: str) -> str:
    return analizar_imagen(ruta, "Describe esta imagen en detalle en español.")

def extraer_texto_imagen(ruta: str) -> str:
    return analizar_imagen(ruta, "Extrae todo el texto visible en esta imagen, preservando el formato original.")

def detectar_anomalias(ruta: str) -> str:
    return analizar_imagen(ruta,
        "¿Hay anomalías, defectos o elementos inusuales en esta imagen? "
        "Responde con: 'Sí/No', qué detectaste y dónde está ubicado en la imagen.")

def analizar_documento(ruta: str) -> str:
    return analizar_imagen(ruta,
        "Analiza este documento. Extrae: (1) tipo de documento, (2) información principal, "
        "(3) campos clave con sus valores. Responde en JSON.")

if __name__ == "__main__":
    ruta = sys.argv[1] if len(sys.argv) > 1 else None
    if not ruta:
        print("Uso: python3 image_captioning.py <imagen.jpg>")
        sys.exit(1)
    print("Descripción:", describir_imagen(ruta))
```

---

> **NOTA:** VILA (Visual Language Model) de NVIDIA no está verificado en el Jetson AGX Orin 64GB con JetPack 7.2. La imagen `dustynv/vila:r39.2.0` no estaba disponible en Docker Hub al momento de escritura. Para comprensión visual avanzada en JP 7.2, use Gemma 4 E4B (§28.3.1) — es más eficiente y completamente verificada. Consulte los releases futuros de NVIDIA para soporte oficial de VILA en JetPack 7.x.

## 28.4 Detección de Objetos con nanoowl

nanoowl es un detector de objetos zero-shot basado en CLIP, optimizado con TensorRT para el Jetson. "Zero-shot" significa que puede detectar cualquier objeto simplemente describiendo en texto lo que busca — sin reentrenamiento.

```bash
# Verificar que TensorRT está disponible
python3 -c "import tensorrt as trt; print('TensorRT:', trt.__version__)"
# Esperado: TensorRT: 10.x.x (JetPack 7.2 incluye TRT 10)
```

```bash
# Instalar nanoowl
source ~/venvs/llm/bin/activate
pip install nanoowl

# Primera vez: compilar el motor TensorRT (tarda 3-5 minutos)
python3 -c "
from nanoowl.owl_predictor import OwlPredictor
# Compilar y cachear el motor TensorRT la primera vez
predictor = OwlPredictor('google/owlvit-base-patch32', image_encoder_engine='/tmp/owl_image_encoder.engine')
print('[OK] Motor TensorRT compilado y guardado en /tmp/owl_image_encoder.engine')
"
```

```python
#!/usr/bin/env python3
"""
object_detection_nanoowl.py — Detección zero-shot de objetos con nanoowl
"""
import sys
import cv2
import numpy as np
from PIL import Image
from nanoowl.owl_predictor import OwlPredictor
from nanoowl.owl_drawing import draw_owl_output

ENGINE_PATH = "/tmp/owl_image_encoder.engine"

def detectar_objetos(ruta: str, objetos_a_detectar: list, umbral: float = 0.1) -> dict:
    """
    Detecta objetos en una imagen usando descripción en lenguaje natural.
    objetos_a_detectar: ["una persona", "un automóvil rojo", "un semáforo"]
    """
    predictor = OwlPredictor('google/owlvit-base-patch32', image_encoder_engine=ENGINE_PATH)
    imagen = Image.open(ruta).convert("RGB")
    output = predictor.predict(imagen, texts=objetos_a_detectar, threshold=umbral)

    detecciones = []
    for i, label_idx in enumerate(output.labels.tolist()):
        score = output.scores[i].item()
        box = output.boxes[i].tolist()
        detecciones.append({
            "objeto": objetos_a_detectar[label_idx],
            "confianza": round(score, 3),
            "bbox": [round(b, 1) for b in box]
        })
    return {"total": len(detecciones), "detecciones": detecciones}

def detectar_en_camara(objetos: list, max_frames: int = 100):
    """Detección en tiempo real desde cámara USB/CSI."""
    predictor = OwlPredictor('google/owlvit-base-patch32', image_encoder_engine=ENGINE_PATH)
    cap = cv2.VideoCapture(0)  # /dev/video0 — USB camera

    if not cap.isOpened():
        print("[ERROR] No se pudo abrir la cámara. Verificar con: v4l2-ctl --list-devices")
        return

    print(f"Detectando: {objetos}")
    print("Presione 'q' para salir")

    for frame_num in range(max_frames):
        ret, frame = cap.read()
        if not ret:
            break
        imagen_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        output = predictor.predict(imagen_pil, texts=objetos, threshold=0.1)

        # Anotar el frame
        frame_anotado = draw_owl_output(frame, output, texto=objetos)
        cv2.imshow("nanoowl - Detección Zero-Shot", frame_anotado)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    ruta = sys.argv[1] if len(sys.argv) > 1 else None
    objetos = sys.argv[2:] if len(sys.argv) > 2 else ["una persona", "un automóvil", "un teléfono"]

    if ruta and ruta != "camara":
        resultado = detectar_objetos(ruta, objetos)
        print(f"Detectados {resultado['total']} objetos:")
        for d in resultado['detecciones']:
            print(f"  • {d['objeto']} ({d['confianza']:.1%}) en bbox {d['bbox']}")
    else:
        detectar_en_camara(objetos if objetos else ["una persona", "un automóvil"])
```

```bash
# Detectar objetos en una imagen
source ~/venvs/llm/bin/activate
python3 ~/scripts/object_detection_nanoowl.py /tmp/test_ocr.png "texto" "imagen" "rectangulo"

# Detección en tiempo real con cámara USB
python3 ~/scripts/object_detection_nanoowl.py camara "una persona" "una silla" "un vaso"
```

---

## 28.5 Procesamiento de Video con OpenCV

### 28.5.1 Configuración de Cámara USB/CSI

```bash
# Listar dispositivos de video conectados
v4l2-ctl --list-devices
```

```
# Salida ejemplo:
USB 2.0 Camera (usb-3610000.usb-1):
        /dev/video0
        /dev/video1
```

```bash
# Ver capacidades de la cámara
v4l2-ctl --device=/dev/video0 --list-formats-ext | head -30

# Probar captura básica (sin pantalla — guarda frame en archivo)
source ~/venvs/llm/bin/activate
python3 -c "
import cv2
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print('[ERROR] No se puede abrir /dev/video0')
else:
    ret, frame = cap.read()
    if ret:
        cv2.imwrite('/tmp/captura_test.jpg', frame)
        print(f'[OK] Frame capturado: {frame.shape[1]}x{frame.shape[0]}px → /tmp/captura_test.jpg')
    cap.release()
"
```

### 28.5.2 Pipeline de Análisis de Video Frame por Frame

```python
#!/usr/bin/env python3
"""
video_analysis_pipeline.py — Análisis de video con VLM cada N frames
Extrae frames, los analiza con el modelo de visión y registra anomalías.
"""
import cv2
import base64
import requests
import json
import time
from datetime import datetime
from pathlib import Path

LOG_DIR = Path.home() / "jetson-ai-data" / "video-analysis"
LOG_DIR.mkdir(parents=True, exist_ok=True)

def frame_a_base64(frame) -> str:
    """Convierte frame OpenCV a base64 JPEG."""
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buffer).decode()

def analizar_frame(frame, pregunta: str = "¿Hay algo inusual o de interés en esta imagen?",
                   port: int = 8080) -> str:
    """Analiza un frame usando el VLM activo."""
    img_b64 = frame_a_base64(frame)
    try:
        resp = requests.post(
            f"http://localhost:{port}/v1/chat/completions",
            json={
                "model": "gemma4-e4b",
                "messages": [{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    {"type": "text", "text": pregunta}
                ]}],
                "max_tokens": 200, "temperature": 0.1
            }, timeout=30
        )
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error: {e}"

def monitorear_video(fuente=0, analizar_cada_n_frames: int = 30,
                     guardar_con_anomalia: bool = True,
                     duracion_segundos: int = 300):
    """
    Monitorea una fuente de video y analiza frames seleccionados con el VLM.
    fuente: 0 para cámara USB, o ruta a un archivo de video
    analizar_cada_n_frames: cuántos frames saltar entre análisis (30 fps → cada 1 segundo con n=30)
    """
    cap = cv2.VideoCapture(fuente)
    if not cap.isOpened():
        print(f"[ERROR] No se puede abrir la fuente: {fuente}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    print(f"[OK] Cámara abierta: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))} @ {fps:.0f}fps")
    print(f"Analizando 1 de cada {analizar_cada_n_frames} frames")

    frame_count = 0
    log_path = LOG_DIR / f"video_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    inicio = time.time()

    while (time.time() - inicio) < duracion_segundos:
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1

        if frame_count % analizar_cada_n_frames == 0:
            timestamp = datetime.now().isoformat()
            analisis = analizar_frame(frame)
            entrada_log = {"timestamp": timestamp, "frame": frame_count, "analisis": analisis}

            with open(log_path, "a") as f:
                f.write(json.dumps(entrada_log, ensure_ascii=False) + "\n")

            print(f"[{timestamp}] Frame {frame_count}: {analisis[:100]}...")

            # Guardar frame si contiene anomalía
            if guardar_con_anomalia and any(w in analisis.lower() for w in ["inusual", "anomalía", "peligro", "unusual", "danger"]):
                frame_path = LOG_DIR / f"anomalia_frame_{frame_count}.jpg"
                cv2.imwrite(str(frame_path), frame)
                print(f"  [WARN]  Frame guardado: {frame_path}")

    cap.release()
    print(f"[OK] Análisis completado. Log: {log_path}")

if __name__ == "__main__":
    # Gemma 4 E4B debe estar activo en :8080
    monitorear_video(fuente=0, analizar_cada_n_frames=60, duracion_segundos=120)
```

```bash
# Ejecutar el pipeline de monitoreo de video
# Prerrequisito: Gemma 4 E4B activo en :8080 (ver §28.3.1)

source ~/venvs/llm/bin/activate
python3 ~/scripts/video_analysis_pipeline.py
```

```bash
# Monitoreo mientras el pipeline corre (en una segunda terminal)
# Ver uso de GPU y RAM en tiempo real
jtop

# O estadisticas rapidas de Docker
docker stats gemma4-e4b-llama --no-stream
docker logs gemma4-e4b-llama --follow
```

---

## 28.6 Integración: OCR → RAG → LLM

El pipeline más potente para procesamiento de documentos combina OCR, almacenamiento en vector store y consulta via LLM:

```python
#!/usr/bin/env python3
"""
doc_rag_pipeline.py — OCR de documento → indexar en ChromaDB → consultar con LLM
"""
import easyocr
import chromadb
import requests
import json
import sys
from pathlib import Path

# Inicializar
reader = easyocr.Reader(['es', 'en'], gpu=True)
chroma = chromadb.PersistentClient(path=str(Path.home() / "jetson-ai-data" / "chroma-ocr"))
collection = chroma.get_or_create_collection("documentos_ocr")

def indexar_documento(ruta: str, doc_id: str = None) -> str:
    """Procesa imagen con OCR e indexa el texto en ChromaDB."""
    doc_id = doc_id or Path(ruta).stem
    texto_completo = " ".join(reader.readtext(ruta, detail=0, paragraph=True))

    # Dividir en chunks de ~500 caracteres
    chunks = [texto_completo[i:i+500] for i in range(0, len(texto_completo), 450)]

    collection.add(
        documents=chunks,
        ids=[f"{doc_id}_chunk_{i}" for i in range(len(chunks))],
        metadatas=[{"fuente": ruta, "chunk": i} for i in range(len(chunks))]
    )
    print(f"[OK] '{doc_id}' indexado ({len(chunks)} chunks, {len(texto_completo)} chars)")
    return texto_completo

def consultar_documentos(pregunta: str, n_resultados: int = 3) -> str:
    """Busca contexto relevante y responde con el LLM."""
    resultados = collection.query(query_texts=[pregunta], n_results=n_resultados)
    contexto = "\n---\n".join(resultados["documents"][0])
    payload = {
        "model": "qwen35",
        "messages": [
            {"role": "system", "content": "Responde la pregunta basándote SOLO en el contexto proporcionado. Si la información no está en el contexto, dilo explícitamente."},
            {"role": "user", "content": f"Contexto extraído de documentos:\n{contexto}\n\nPregunta: {pregunta}"}
        ],
        "max_tokens": 600
    }
    resp = requests.post("http://localhost:8000/v1/chat/completions", json=payload, timeout=60)
    return resp.json()["choices"][0]["message"]["content"]

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "indexar":
        indexar_documento(sys.argv[2])
    elif len(sys.argv) == 3 and sys.argv[1] == "consultar":
        print(consultar_documentos(sys.argv[2]))
    else:
        print("Uso:")
        print("  Indexar: python3 doc_rag_pipeline.py indexar <imagen.jpg>")
        print("  Consultar: python3 doc_rag_pipeline.py consultar 'pregunta sobre los documentos'")
```

---

## 28.7 Aliases y Scripts del Capítulo

> **CONSEJO:** Los scripts de este capítulo se editan cómodamente desde Windows con VSCode Remote SSH (Capítulo 7). Abra `~/scripts/` en VSCode, edite, guarde — los cambios se aplican de inmediato en el Jetson.

```bash
# Agregar a ~/.bash_aliases
cat >> ~/.bash_aliases << 'EOF'

# ── Computer Vision ──────────────────────────────────────────────────────
alias start-vision='pwr-30w && docker-on && echo "Entorno de vision listo. Inicie Gemma4 con: docker run gemma4-e4b-llama"'
alias ocr-imagen='source ~/venvs/llm/bin/activate && python3 ~/scripts/ocr_easyocr.py'
alias ocr-llm='source ~/venvs/llm/bin/activate && python3 ~/scripts/ocr_llm_pipeline.py'
alias vision-describe='source ~/venvs/llm/bin/activate && python3 ~/scripts/image_captioning.py'
alias nanoowl-detect='source ~/venvs/llm/bin/activate && python3 ~/scripts/object_detection_nanoowl.py'
alias video-monitor='source ~/venvs/llm/bin/activate && python3 ~/scripts/video_analysis_pipeline.py'
alias doc-indexar='source ~/venvs/llm/bin/activate && python3 ~/scripts/doc_rag_pipeline.py indexar'
alias doc-consultar='source ~/venvs/llm/bin/activate && python3 ~/scripts/doc_rag_pipeline.py consultar'
# Monitoreo de contenedores de vision
alias vision-logs='docker logs gemma4-e4b-llama --follow'
alias vision-stats='docker stats gemma4-e4b-llama --no-stream && jtop --once 2>/dev/null || true'
EOF

source ~/.bash_aliases || source ~/.bashrc
```

---

## 28.8 Solución de Problemas

### EasyOCR falla con `CUDA out of memory`

```bash
# Síntoma: OOM al cargar EasyOCR con gpu=True
# Solución: ejecutar EasyOCR en CPU si hay poca RAM disponible
check-ready
free -h | awk '/Mem/{print $7}'
# Si quedan <20 GB libres, ejecutar jetson-clean primero

# O inicializar EasyOCR en CPU (más lento pero sin OOM)
python3 -c "
import easyocr
reader = easyocr.Reader(['es', 'en'], gpu=False)  # forzar CPU
result = reader.readtext('/tmp/test_ocr.png', detail=0)
print(result)
"
```

### OpenCV: `cannot open camera /dev/video0`

```bash
# Verificar permisos de la cámara
ls -la /dev/video0
# El usuario debe pertenecer al grupo 'video'
sudo usermod -aG video $USER
# Cerrar sesión y volver a conectar por SSH

# Verificar que la cámara funciona con v4l2
v4l2-ctl --device=/dev/video0 --stream-mmap --stream-count=1

# Si es una cámara CSI (Raspberry Pi Camera Module v2):
# El dispositivo puede ser /dev/video1 o /dev/video2 en el Jetson
v4l2-ctl --list-devices
```

### nanoowl: `TensorRT engine not found`

```bash
# Regenerar el motor TensorRT si se perdió el archivo
source ~/venvs/llm/bin/activate
python3 -c "
from nanoowl.owl_predictor import OwlPredictor
predictor = OwlPredictor('google/owlvit-base-patch32',
                         image_encoder_engine='/tmp/owl_image_encoder.engine')
print('[OK] Motor TensorRT regenerado')
"
# Tarda 3-5 minutos en compilar
```

---

## Casos de Uso Reales

Las herramientas de este capítulo se combinan para resolver problemas concretos en entornos empresariales:

### Caso 1: Lectura automática de facturas en bodega

Una bodega recibe facturas en papel. El operario las fotografía con su teléfono y las envía por WhatsApp. El Jetson (via OpenClaw) usa EasyOCR para extraer el texto y vLLM para parsear el JSON estructurado:

```bash
# Pipeline completo: imagen → EasyOCR → vLLM → JSON de factura
python3 ~/scripts/ocr_easyocr.py /tmp/factura.jpg \
  | python3 ~/scripts/llm_structure_ocr.py \
      --schema '{"proveedor": "", "total": 0.0, "items": [], "fecha": ""}'
```

```
# Salida esperada:
{
  "proveedor": "Distribuidora XYZ S.A.S.",
  "total": 1250000.0,
  "items": [
    {"desc": "Tornillos M6x20mm", "cant": 500, "precio": 450},
    {"desc": "Tuercas M6", "cant": 500, "precio": 400}
  ],
  "fecha": "2026-06-28"
}
```

### Caso 2: Vigilancia perimetral con nanoowl

Sistema de seguridad que detecta personas o vehículos en cámara de parking y envía alerta por Telegram:

```bash
# Detectar personas Y vehículos en stream de cámara USB
source ~/venvs/llm/bin/activate
python3 ~/scripts/nanoowl_detect.py \
  --input /dev/video0 \
  --labels "a person, a car, a truck, a motorcycle" \
  --threshold 0.3 \
  --on-detect "~/scripts/send-telegram-alert.sh 'Detección: {label} ({confidence:.0%})'"
```

```
# Salida esperada en consola:
[11:42:03] Detección: a person (87%) — guardado /tmp/detections/20260628_114203.jpg
[11:42:15] Detección: a car (91%) — guardado /tmp/detections/20260628_114215.jpg
```

### Caso 3: Catalogación automática de productos con VLM

Sistema para e-commerce que genera descripciones automáticas de productos a partir de fotos:

```bash
# Fotos de productos → descripciones en español con Gemma 4 E4B
for foto in ~/productos/*.jpg; do
  echo "=== $(basename "$foto") ==="
  python3 ~/scripts/gemma_vision.py "$foto" \
    "Describe este producto para una tienda online: nombre, características, materiales visibles, colores."
  echo ""
done
```

```
# Salida esperada (por imagen):
=== silla_ergonomica_01.jpg ===
Silla ergonómica de oficina con respaldo en malla negra transpirable,
asiento tapizado en tela gris, apoyabrazos ajustables en altura,
base de 5 ruedas en nylon, mecanismo de inclinación lumbar regulable.
Ideal para trabajo prolongado frente a computador.
```

---

## Resumen del Capítulo

El Jetson AGX Orin 64GB procesa visión artificial directamente en GPU con tres capas complementarias:

- **OCR clásico** (Tesseract/EasyOCR): extracción de texto rápida; Tesseract sin GPU, EasyOCR con GPU
- **VLM local** (Gemma 4 E4B via llama.cpp: ~3 GB): image captioning y VQA sin conexión a internet
- **Detección zero-shot** (nanoowl + TensorRT): detecta cualquier objeto descrito en texto en tiempo real
- **OCR → LLM pipeline**: combina EasyOCR para extracción y vLLM para análisis estructurado (JSON)
- **Modo energético**: 30W para OCR y nanoowl; MAXN para modelos de visión grandes

El siguiente capítulo (Capítulo 29) cubre el stack TTS+STT unificado: transcripción de voz en español con faster-whisper y síntesis de voz con kokoro-tts y piper, incluyendo diarización de hablantes y timestamps a nivel de palabra.
