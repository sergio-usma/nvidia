# Capítulo 25 — Sistema RAG para Documentos Empresariales

## Introducción

RAG (Retrieval Augmented Generation) es la técnica más poderosa para conectar un LLM con su propia base de conocimiento. En lugar de enviar documentos confidenciales a la nube, este sistema indexa localmente todos sus PDFs, documentos Word, contratos y manuales, y luego responde preguntas sobre ellos con citas exactas de las fuentes.

El Jetson AGX Orin 64GB es ideal para RAG empresarial: tiene suficiente RAM para cargar el modelo de embeddings y el LLM simultáneamente, el NVMe hace que las búsquedas en ChromaDB sean rápidas, y nada sale del hardware.

**Caso de uso típico:**
- "¿Qué dice el contrato con el proveedor X sobre las penalizaciones?"
- "Según el manual de operaciones, ¿cuál es el procedimiento para Y?"
- "Resume las cláusulas de confidencialidad en todos los acuerdos del 2024"

**Prerrequisitos:**
- Ollama con `qwen3:7b` y `nomic-embed-text` (Capítulo 12)
- NVMe recomendado para la base de datos vectorial (Capítulo 4)
- Python + venv de desarrollo (Capítulo 7)

**Tiempo de indexación:** ~30 seg por 100 páginas de PDF
**Tiempo de respuesta por consulta:** 3–8 segundos
**Modo de energía:** 30W (embeddings + 7B LLM)

---

## 25.1 Prerrequisito — Instalar nomic-embed-text

```bash
# Descargar el modelo de embeddings
# nomic-embed-text: 137M parámetros, optimizado para embeddings de texto
sudo systemctl start ollama
ollama pull nomic-embed-text

# Verificar instalación
ollama list | grep nomic
```

```
# Salida esperada
nomic-embed-text    latest    0a109f422b47    16 hours ago    274 MB
```

```bash
# Instalar dependencias Python
source ~/venvs/dev/bin/activate
pip install chromadb pymupdf python-docx langchain langchain-community langchain-ollama fastapi uvicorn
```

---

## 25.2 Estructura del Proyecto

```bash
mkdir -p ~/projects/rag-empresarial/{data,documents,scripts,api}
mkdir -p /data/rag-db  # base de datos vectorial en NVMe
cd ~/projects/rag-empresarial
```

```
rag-empresarial/
├── documents/              # Documentos a indexar (PDF, DOCX, TXT)
├── data/                   # Metadatos y configuración
├── scripts/
│   ├── indexer.py          # Indexa documentos en ChromaDB
│   ├── retriever.py        # Búsqueda y generación de respuestas
│   └── utils.py            # Utilidades de procesamiento
└── api/
    └── rag_api.py          # FastAPI server (port 9000)
```

---

## 25.3 Script 1 — Indexador de Documentos

```python
# scripts/indexer.py
"""
Extrae texto de documentos, genera embeddings y los almacena en ChromaDB.
Soporta: PDF, DOCX, TXT.
"""
import json
import hashlib
import time
from pathlib import Path
from typing import Generator

import chromadb
import fitz  # PyMuPDF para PDF
import requests


# ── Configuración ─────────────────────────────────────────
CHROMA_PATH = "/data/rag-db"
COLLECTION_NAME = "documentos_empresa"
OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
CHUNK_SIZE = 600        # palabras por chunk
CHUNK_OVERLAP = 100     # palabras de superposición entre chunks


def obtener_embedding(texto: str) -> list[float]:
    """Genera embeddings usando nomic-embed-text via Ollama."""
    resp = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": texto},
        timeout=30
    )
    if resp.status_code == 200:
        return resp.json().get("embedding", [])
    raise RuntimeError(f"Error de embedding: {resp.status_code} — {resp.text[:100]}")


def hash_documento(ruta: Path) -> str:
    """Hash SHA256 del contenido para detectar documentos ya indexados."""
    h = hashlib.sha256()
    h.update(ruta.read_bytes())
    return h.hexdigest()[:16]


def extraer_texto_pdf(ruta: Path) -> str:
    """Extrae texto de un PDF."""
    doc = fitz.open(str(ruta))
    partes = []
    for pagina in doc:
        texto = pagina.get_text("text").strip()
        if texto:
            partes.append(texto)
    doc.close()
    return "\n\n".join(partes)


def extraer_texto_docx(ruta: Path) -> str:
    """Extrae texto de un archivo Word."""
    from docx import Document
    doc = Document(str(ruta))
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extraer_texto_txt(ruta: Path) -> str:
    """Lee texto plano."""
    return ruta.read_text(encoding="utf-8", errors="replace")


def extraer_texto(ruta: Path) -> str:
    """Extrae texto según la extensión del archivo."""
    ext = ruta.suffix.lower()
    if ext == ".pdf":
        return extraer_texto_pdf(ruta)
    elif ext in (".docx", ".doc"):
        return extraer_texto_docx(ruta)
    elif ext == ".txt":
        return extraer_texto_txt(ruta)
    else:
        raise ValueError(f"Formato no soportado: {ext}")


def dividir_en_chunks(texto: str, nombre_archivo: str) -> list[dict]:
    """
    Divide el texto en chunks con metadatos.
    Intenta respetar los límites de párrafo.
    """
    palabras = texto.split()
    chunks = []
    inicio = 0
    
    while inicio < len(palabras):
        fin = min(inicio + CHUNK_SIZE, len(palabras))
        
        # Buscar un corte natural (punto o salto de línea)
        if fin < len(palabras):
            # Buscar el último punto en la ventana
            chunk_texto = " ".join(palabras[inicio:fin])
            ultimo_punto = max(
                chunk_texto.rfind(". "),
                chunk_texto.rfind(".\n"),
                chunk_texto.rfind("! "),
                chunk_texto.rfind("? ")
            )
            if ultimo_punto > len(chunk_texto) * 0.7:  # si el punto está en el 70% final
                # Recalcular el fin basado en el punto
                palabras_hasta_punto = len(chunk_texto[:ultimo_punto+2].split())
                fin = inicio + palabras_hasta_punto
        
        chunk_texto = " ".join(palabras[inicio:fin])
        
        if chunk_texto.strip():
            chunks.append({
                "texto": chunk_texto,
                "archivo": nombre_archivo,
                "chunk_num": len(chunks),
                "palabras": fin - inicio
            })
        
        inicio = fin - CHUNK_OVERLAP
        if inicio <= 0:
            break
    
    return chunks


def indexar_documento(ruta: Path, coleccion: chromadb.Collection) -> int:
    """
    Indexa un documento en ChromaDB.
    Returns: número de chunks añadidos (0 si ya estaba indexado).
    """
    doc_hash = hash_documento(ruta)
    
    # Verificar si ya está indexado
    existentes = coleccion.get(
        where={"doc_hash": doc_hash},
        limit=1
    )
    if existentes["ids"]:
        print(f"  [SKIP] Ya indexado: {ruta.name}")
        return 0
    
    print(f"  Procesando: {ruta.name}...", end="", flush=True)
    
    # Extraer texto
    try:
        texto = extraer_texto(ruta)
    except Exception as e:
        print(f" [ERROR] Error extrayendo texto: {str(e)[:50]}")
        return 0
    
    if not texto.strip():
        print(f" [WARN]  Sin texto extraído")
        return 0
    
    # Dividir en chunks
    chunks = dividir_en_chunks(texto, ruta.name)
    print(f" {len(chunks)} chunks", end="")
    
    # Generar embeddings e insertar en ChromaDB
    ids = []
    embeddings = []
    documentos = []
    metadatos = []
    
    for chunk in chunks:
        chunk_id = f"{doc_hash}_{chunk['chunk_num']}"
        try:
            emb = obtener_embedding(chunk["texto"][:2000])  # límite para evitar timeout
        except Exception as e:
            print(f"\n  [WARN]  Error en embedding chunk {chunk['chunk_num']}: {str(e)[:40]}")
            continue
        
        ids.append(chunk_id)
        embeddings.append(emb)
        documentos.append(chunk["texto"])
        metadatos.append({
            "archivo": chunk["archivo"],
            "chunk_num": chunk["chunk_num"],
            "doc_hash": doc_hash,
            "palabras": chunk["palabras"],
            "ruta_completa": str(ruta)
        })
    
    if ids:
        coleccion.add(
            ids=ids,
            embeddings=embeddings,
            documents=documentos,
            metadatas=metadatos
        )
    
    print(f" [OK]")
    return len(ids)


def indexar_directorio(directorio: str = "documents") -> dict:
    """
    Indexa todos los documentos de un directorio.
    """
    dir_path = Path(directorio)
    extensiones_soportadas = {".pdf", ".docx", ".txt", ".doc"}
    
    # Inicializar ChromaDB
    print(f"Conectando a ChromaDB en: {CHROMA_PATH}")
    cliente = chromadb.PersistentClient(path=CHROMA_PATH)
    
    coleccion = cliente.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}  # distancia coseno para texto
    )
    
    archivos = [
        f for f in dir_path.rglob("*")
        if f.is_file() and f.suffix.lower() in extensiones_soportadas
    ]
    
    if not archivos:
        print(f"No se encontraron documentos en: {dir_path}")
        return {"indexados": 0, "total_chunks": 0}
    
    print(f"\n Indexando {len(archivos)} documentos...\n")
    inicio_total = time.time()
    
    total_chunks = 0
    documentos_nuevos = 0
    
    for archivo in archivos:
        chunks = indexar_documento(archivo, coleccion)
        total_chunks += chunks
        if chunks > 0:
            documentos_nuevos += 1
    
    tiempo = time.time() - inicio_total
    total_en_db = coleccion.count()
    
    print(f"\n═══════════════════════════════════════")
    print(f"Indexación completada:")
    print(f"  Documentos procesados: {len(archivos)}")
    print(f"  Documentos nuevos: {documentos_nuevos}")
    print(f"  Chunks añadidos: {total_chunks}")
    print(f"  Total en base de datos: {total_en_db} chunks")
    print(f"  Tiempo: {tiempo:.1f} segundos")
    
    return {
        "indexados": documentos_nuevos,
        "total_chunks": total_en_db,
        "tiempo_seg": tiempo
    }


if __name__ == "__main__":
    import sys
    directorio = sys.argv[1] if len(sys.argv) > 1 else "documents"
    indexar_directorio(directorio)
```

```bash
# Copiar documentos a indexar
cp /ruta/a/mis/documentos/*.pdf ~/projects/rag-empresarial/documents/

# Iniciar indexación
python scripts/indexer.py
```

```
# Salida esperada
Conectando a ChromaDB en: /data/rag-db
 Indexando 5 documentos...

  Procesando: contrato_proveedor_2024.pdf... 23 chunks [OK]
  Procesando: manual_operaciones_v3.pdf... 47 chunks [OK]
  Procesando: politicas_rrhh.docx... 31 chunks [OK]
  [SKIP] Ya indexado: contrato_anterior.pdf
  Procesando: informe_anual_2023.pdf... 89 chunks [OK]

═══════════════════════════════════════
Indexación completada:
  Documentos procesados: 5
  Documentos nuevos: 4
  Chunks añadidos: 190
  Total en base de datos: 190 chunks
  Tiempo: 47.3 segundos
```

---

## 25.4 Script 2 — Motor de Consultas RAG

```python
# scripts/retriever.py
"""
Motor de recuperación y generación con citas de fuentes.
"""
import time
import requests
import chromadb
from openai import OpenAI


CHROMA_PATH = "/data/rag-db"
COLLECTION_NAME = "documentos_empresa"
OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "qwen3:7b"
TOP_K = 4  # chunks a recuperar por consulta


def obtener_embedding(texto: str) -> list[float]:
    resp = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": texto},
        timeout=30
    )
    return resp.json().get("embedding", [])


def recuperar_contexto(pregunta: str, n_resultados: int = TOP_K) -> list[dict]:
    """
    Recupera los chunks más relevantes para la pregunta.
    """
    cliente = chromadb.PersistentClient(path=CHROMA_PATH)
    coleccion = cliente.get_collection(COLLECTION_NAME)
    
    # Generar embedding de la pregunta
    embedding_pregunta = obtener_embedding(pregunta)
    
    # Buscar chunks similares
    resultados = coleccion.query(
        query_embeddings=[embedding_pregunta],
        n_results=min(n_resultados, coleccion.count()),
        include=["documents", "metadatas", "distances"]
    )
    
    chunks_relevantes = []
    for i in range(len(resultados["ids"][0])):
        chunks_relevantes.append({
            "texto": resultados["documents"][0][i],
            "archivo": resultados["metadatas"][0][i]["archivo"],
            "chunk_num": resultados["metadatas"][0][i]["chunk_num"],
            "similitud": 1 - resultados["distances"][0][i]  # coseno: 1=idéntico
        })
    
    # Ordenar por similitud descendente
    chunks_relevantes.sort(key=lambda x: x["similitud"], reverse=True)
    return chunks_relevantes


def generar_respuesta_rag(pregunta: str) -> dict:
    """
    Genera una respuesta con citas usando el contexto recuperado.
    
    Returns:
        dict con 'respuesta', 'fuentes', 'contexto_usado', 'metricas'
    """
    t_inicio = time.time()
    
    # 1. Recuperar contexto
    contexto_chunks = recuperar_contexto(pregunta)
    t_retrieval = time.time() - t_inicio
    
    if not contexto_chunks:
        return {
            "respuesta": "No se encontraron documentos relevantes para responder esta pregunta.",
            "fuentes": [],
            "metricas": {"retrieval_seg": t_retrieval}
        }
    
    # Filtrar chunks con similitud muy baja (< 0.3 = probablemente irrelevantes)
    chunks_filtrados = [c for c in contexto_chunks if c["similitud"] > 0.3]
    
    if not chunks_filtrados:
        return {
            "respuesta": "Los documentos disponibles no contienen información suficientemente relevante para esta consulta.",
            "fuentes": [],
            "metricas": {"retrieval_seg": t_retrieval}
        }
    
    # 2. Construir prompt con contexto
    contexto_texto = ""
    for i, chunk in enumerate(chunks_filtrados[:TOP_K], 1):
        contexto_texto += f"""
[FUENTE {i}: {chunk['archivo']} (relevancia: {chunk['similitud']:.2f})]
{chunk['texto'][:600]}
---"""
    
    prompt = f"""Responde la siguiente pregunta basándote ÚNICAMENTE en los documentos proporcionados.

DOCUMENTOS:
{contexto_texto}

PREGUNTA: {pregunta}

Instrucciones:
- Responde de forma clara y directa
- Cita explícitamente las fuentes usando [FUENTE N] al final de cada afirmación relevante
- Si la información no está en los documentos, indica claramente que no se encuentra en la base documental
- No inventes información que no esté en los documentos
- Al final, lista las fuentes citadas

RESPUESTA:"""
    
    # 3. Generar respuesta con LLM
    t_llm_inicio = time.time()
    
    cliente = OpenAI(base_url=f"{OLLAMA_URL}/v1", api_key="ollama")
    resp = cliente.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1200,
        temperature=0.3  # baja temperatura para respuestas más fieles al contexto
    )
    
    t_llm = time.time() - t_llm_inicio
    
    respuesta_texto = resp.choices[0].message.content.strip()
    
    # 4. Extraer fuentes únicas citadas
    fuentes_unicas = list(set(c["archivo"] for c in chunks_filtrados[:TOP_K]))
    
    return {
        "respuesta": respuesta_texto,
        "fuentes": fuentes_unicas,
        "contexto_chunks": len(chunks_filtrados),
        "metricas": {
            "retrieval_seg": round(t_retrieval, 2),
            "llm_seg": round(t_llm, 2),
            "total_seg": round(time.time() - t_inicio, 2),
            "tokens_respuesta": resp.usage.completion_tokens
        }
    }


def consulta_interactiva():
    """Interfaz de consulta por terminal."""
    print("""
╔══════════════════════════════════════════════════════════╗
║    SISTEMA RAG EMPRESARIAL — JETSON AGX ORIN            ║
╠══════════════════════════════════════════════════════════╣
║  Consulte sus documentos empresariales en lenguaje      ║
║  natural. Escriba 'salir' para terminar.                 ║
╚══════════════════════════════════════════════════════════╝
""")
    
    # Verificar base de datos
    try:
        cliente = chromadb.PersistentClient(path=CHROMA_PATH)
        coleccion = cliente.get_collection(COLLECTION_NAME)
        n_docs = coleccion.count()
        print(f"Base de datos: {n_docs} chunks indexados")
        if n_docs == 0:
            print("[WARN]  Base de datos vacía — ejecute primero: python scripts/indexer.py")
            return
    except Exception as e:
        print(f"[ERROR] Error conectando a ChromaDB: {e}")
        print("   Ejecute primero: python scripts/indexer.py")
        return
    
    print("\nEjemplos de consultas:")
    print('  "¿Cuáles son las condiciones de pago del contrato con [proveedor]?"')
    print('  "Resume las políticas de vacaciones del manual de RRHH"')
    print('  "¿Qué dice el informe anual sobre los objetivos de 2024?"\n')
    
    while True:
        try:
            pregunta = input("Consulta: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        
        if not pregunta:
            continue
        
        if pregunta.lower() in ("salir", "exit", "quit"):
            break
        
        print("\nBuscando en documentos...", end="", flush=True)
        resultado = generar_respuesta_rag(pregunta)
        
        print(f"\r{'─' * 55}")
        print(resultado["respuesta"])
        print(f"{'─' * 55}")
        print(f"Fuentes: {', '.join(resultado['fuentes']) if resultado['fuentes'] else 'ninguna'}")
        metricas = resultado.get("metricas", {})
        print(f"Tiempo: {metricas.get('total_seg', 0):.1f}s (búsqueda: {metricas.get('retrieval_seg', 0):.2f}s + LLM: {metricas.get('llm_seg', 0):.2f}s)")
        print()


if __name__ == "__main__":
    consulta_interactiva()
```

---

## 25.5 API REST (FastAPI)

```python
# api/rag_api.py
"""
API REST para el sistema RAG — permite integración con otras aplicaciones.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from scripts.retriever import generar_respuesta_rag, recuperar_contexto
from scripts.indexer import indexar_directorio
import chromadb

app = FastAPI(title="RAG Empresarial API", version="1.0.0")


class Consulta(BaseModel):
    pregunta: str
    n_fuentes: int = 4


class RespuestaRAG(BaseModel):
    respuesta: str
    fuentes: list[str]
    metricas: dict


@app.get("/health")
def health():
    return {"status": "ok", "servicio": "RAG Empresarial"}


@app.get("/stats")
def estadisticas():
    """Estadísticas de la base de datos vectorial."""
    try:
        cliente = chromadb.PersistentClient(path="/data/rag-db")
        coleccion = cliente.get_collection("documentos_empresa")
        return {
            "chunks_indexados": coleccion.count(),
            "estado": "activo"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=RespuestaRAG)
def consultar(consulta: Consulta):
    """Consulta el sistema RAG."""
    if not consulta.pregunta.strip():
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía")
    
    resultado = generar_respuesta_rag(consulta.pregunta)
    return RespuestaRAG(
        respuesta=resultado["respuesta"],
        fuentes=resultado["fuentes"],
        metricas=resultado.get("metricas", {})
    )


@app.post("/index")
def indexar(directorio: str = "documents"):
    """Indexa o re-indexa documentos de un directorio."""
    return indexar_directorio(directorio)
```

```bash
# Iniciar la API en segundo plano
source ~/venvs/dev/bin/activate
uvicorn api.rag_api:app --host 0.0.0.0 --port 9000 &

# Probar
curl -X POST http://localhost:9000/query \
  -H "Content-Type: application/json" \
  -d '{"pregunta": "¿Cuáles son las condiciones de pago del contrato con el proveedor principal?"}'
```

---

## 25.6 Flujo de Uso Completo

```bash
# 1. Indexar documentos
source ~/venvs/dev/bin/activate
sudo systemctl start ollama
ollama run nomic-embed-text --keepalive 30m &  # mantener modelo cargado
sleep 5

# Copiar documentos y ejecutar indexación
cp ~/Documentos/empresa/*.pdf ~/projects/rag-empresarial/documents/
python scripts/indexer.py

# 2. Consulta interactiva por terminal
python scripts/retriever.py

# 3. O iniciar API y usar desde otra aplicación
uvicorn api.rag_api:app --host 0.0.0.0 --port 9000
```

---

## 25.7 Limpieza Post-Pipeline

```bash
# Detener la API y Ollama
pkill -f "uvicorn api.rag_api" 2>/dev/null || true
sudo systemctl stop ollama

sync && echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
pwr-15w

# La base de datos ChromaDB persiste en /data/rag-db — no se elimina
echo "[OK] Sistema RAG detenido (base de datos conservada en /data/rag-db)"
```

---

## 25.8 Verificación Final del Capítulo

```bash
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   VERIFICACIÓN CAPÍTULO 25 — RAG EMPRESARIAL         ║"
echo "╚═══════════════════════════════════════════════════════╝"

source ~/venvs/dev/bin/activate

echo ""
echo "── Dependencias Python ──"
python -c "
for mod, pkg in [('chromadb','chromadb'),('fitz','pymupdf'),('docx','python-docx'),('fastapi','fastapi')]:
    try:
        __import__(mod)
        print(f'  [OK] {mod}')
    except ImportError:
        print(f'  ○  {mod} → pip install {pkg}')
"

echo ""
echo "── Modelos Ollama ──"
ollama list 2>/dev/null | grep -q "qwen3:7b" && echo "  [OK] qwen3:7b" || echo "  ○  ollama pull qwen3:7b"
ollama list 2>/dev/null | grep -q "nomic-embed" && echo "  [OK] nomic-embed-text" || echo "  ○  ollama pull nomic-embed-text"

echo ""
echo "── Base de datos vectorial ──"
[ -d "/data/rag-db" ] && echo "  [OK] /data/rag-db existe" || echo "  ○  Crear: mkdir -p /data/rag-db"
python -c "
import chromadb
try:
    c = chromadb.PersistentClient('/data/rag-db')
    col = c.get_collection('documentos_empresa')
    print(f'  [OK] Colección activa: {col.count()} chunks indexados')
except Exception as e:
    print(f'  ○  Base de datos vacía — ejecute: python scripts/indexer.py')
" 2>/dev/null

echo ""
echo "── API REST ──"
curl -sf http://localhost:9000/health > /dev/null 2>&1 \
  && echo "  [OK] API activa en puerto 9000" \
  || echo "  ○  Iniciar: uvicorn api.rag_api:app --host 0.0.0.0 --port 9000"

echo ""
echo "═════════════════════════════════════════════════════════"
```

---

## 25.9 Escalabilidad y Extensiones

### 25.9.1 Consulta de Documentos vía Telegram

El sistema RAG puede integrarse con Telegram para que cualquier miembro del equipo consulte documentos empresariales desde su teléfono, sin acceso directo al Jetson.

**Flujo con N8N** (ver Capítulo 14):

```yaml
Nodo 1 — Telegram Trigger:
  tipo: telegram_trigger
  evento: message_received
  filtro: texto (pregunta sobre documentos)

Nodo 2 — HTTP Request (API RAG):
  tipo: http_request
  metodo: POST
  url: http://localhost:9000/query
  body:
    query: "{{message_text}}"
    top_k: 5
  timeout: 30

Nodo 3 — Send Message:
  tipo: telegram_send_message
  chat_id: {{chat_id}}
  texto: "{{response.answer}}\n\n_Fuentes: {{response.sources}}_"
  parse_mode: Markdown
```

**Flujo con OpenClaw** (ver Capítulo 11A):

```json
"agents": {
  "rag": {
    "description": "Consulta documentos empresariales con RAG",
    "endpoint": "http://localhost:9000/query",
    "method": "POST",
    "input_field": "query",
    "channels": ["telegram"]
  }
}
```

> **NOTA:** La API REST del sistema RAG (§25.5) ya está diseñada para recibir consultas HTTP, lo que simplifica la integración con N8N y OpenClaw — no se requiere modificar el código del RAG.

### 25.9.2 Modo Mixto con OpenRouter

Para preguntas que requieran síntesis de información dispersa en múltiples documentos o razonamiento complejo, use OpenRouter como alternativa al modelo local:

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

> **NOTA:** Los embeddings (`nomic-embed-text`) siempre se generan localmente en el Jetson, independientemente del backend elegido para el chat. Esto garantiza que los documentos privados no salgan de la red local.

```bash
alias rag-local="USE_LOCAL_LLM=true  python3 ~/projects/rag-empresarial/scripts/query.py"
alias rag-cloud="USE_LOCAL_LLM=false python3 ~/projects/rag-empresarial/scripts/query.py"
```

### 25.9.3 Evaluación de Backend para Alta Concurrencia

El sistema RAG vía API REST puede recibir múltiples consultas simultáneas de distintos usuarios. El backend de inferencia impacta directamente en la capacidad de atenderlas:

| Backend | Concurrencia | VRAM total (chat + embed) | Latencia primera respuesta | Recomendación |
|---|---|---|---|---|
| **Ollama** (qwen3:7b + nomic) | 1 concurrent | ~6.5 GB | ~1–2 seg | Adecuado para equipo pequeño (<5 usuarios) |
| **vLLM** (qwen3:7b) + Ollama (nomic) | 8–16 concurrent | ~8 GB | ~800 ms | **Recomendado** para equipo mediano (5–20 usuarios) |
| **llama.cpp** (qwen3:7b Q4_K_M) + Ollama (nomic) | 2–4 concurrent | ~5 GB | ~1 seg | Buena opción si VRAM es limitada por otros servicios |

> **CONSEJO:** Si el Jetson sirve el RAG a más de 5 usuarios simultáneos, configure vLLM como servidor de chat y mantenga Ollama exclusivamente para los embeddings de `nomic-embed-text`. Esta separación optimiza el throughput sin sacrificar la calidad de los embeddings.

```bash
# Iniciar vLLM para RAG multi-usuario (ver Capítulo 12 — sección vLLM)
docker run -d --rm --runtime nvidia \
  --name vllm-rag \
  -p 8001:8000 \
  -v ~/data/models:/models \
  dustynv/vllm:r39.2.0 \
  --model /models/qwen3-7b \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.45

# En rag_api.py: cambiar OLLAMA_URL a "http://localhost:8001/v1"
```

---

> **Proyectos de IA completados.** Tiene un ecosistema completo de proyectos de IA ejecutándose completamente offline en el Jetson AGX Orin 64GB. El **Apéndice** provee la referencia rápida de todos los comandos, puertos y aliases utilizados en el libro.
