# Capstone Project 01 — Agencia de IA con Presencia Web

## Introducción

Este es el capítulo final del libro. Todo lo aprendido en los 30 capítulos anteriores confluye aquí en un sistema funcional completo: una **agencia de inteligencia artificial** operando desde el Jetson AGX Orin 64GB como un servicio de negocio real.

Un cliente visita la web de la agencia, describe su necesidad, el sistema lo procesa con múltiples agentes de IA especializados, produce los entregables, y el cliente los recibe — todo sin intervención humana y completamente offline.

**Arquitectura del sistema completo:**

<!-- INFOGRAFÍA: Arquitectura Capstone — Agencia de IA completa sobre Jetson AGX Orin: flujo desde cliente web (Cloudflare Tunnel → Nginx → Flask) hasta orquestador OpenClaw y modelos de inferencia (vLLM Qwen3.5-35B, Ollama Qwen3.5-4B), con automatización N8N y pipeline de voz opcional — presupuesto de RAM por componente incluido — pendiente de diseño gráfico (paleta NVIDIA #0F3D3D / #1D9CB8, texto mínimo 10pt, optimizado para KDP Kindle dark/light) -->

```
Internet
    ↓ HTTPS (Cloudflare Tunnel — Capítulo 30)
Nginx :8088 (reverse proxy — Capítulo 30)
    ↓
Flask Web Frontend :5000
    ├─ Formulario intake de cliente (descripción del proyecto)
    ├─ Panel de estado del proyecto (SSE streaming)
    └─ Descarga de entregables (ZIP con archivos generados)
         ↓ HTTP interno
OpenClaw :18789 (orquestador de agentes — Capítulos 13A + 13B)
    ├─ Agente Analista — comprende el brief del cliente
    ├─ Agente Redactor — produce el contenido
    └─ Agente Revisor — valida y refina el output
         ↓ modelo de inferencia
vLLM Qwen3.5-35B-A3B :8000 (razonamiento complejo — Capítulo 14)
    ↑ o, para tareas cortas:
Ollama Qwen3.5-4B :11434 (respuestas rápidas — Capítulo 12)
         ↓ automatización
N8N :5678 (workflows — Capítulo 27)
    ├─ Intake webhook → notificación al cliente (email)
    ├─ Proyecto completado → entrega por email
    └─ Facturación conceptual (registro en PostgreSQL)
         ↓ voz (opcional)
STT faster-whisper :8000 (Capítulo 17)
TTS kokoro-tts :8880 (Capítulo 17)
```

**Presupuesto de memoria para el stack completo:**

| Componente | RAM |
|-----------|-----|
| OS base | ~12 GB |
| Flask frontend | ~0.2 GB |
| OpenClaw + NemoClaw | ~1 GB |
| N8N + PostgreSQL | ~2 GB |
| vLLM Qwen3.5-35B (activo durante generación) | ~26 GB |
| Ollama Qwen3.5-4B (agentes persistentes) | ~5 GB |
| Nginx + JWT + cloudflared | ~0.3 GB |
| **Total durante generación activa** | **~46.5 GB / 64 GB** |
| **Total en espera (sin vLLM)** | **~20.5 GB / 64 GB** |

**Modo energético:**
- En espera (agentes listos, sin generar): 30W
- Durante generación con vLLM 35B: MAXN (50W) — se activa automáticamente

---

## 31.1 Estructura del Proyecto

```bash
# Crear la estructura de directorios del capstone
mkdir -p ~/agencia/{web/{templates,static/{css,js}},scripts,entregables,logs}

ls ~/agencia/
```

```
web/          ← Flask app: templates, static
scripts/      ← scripts de gestión del stack
entregables/  ← proyectos completados (ZIP para descarga)
logs/         ← logs del sistema
```

---

## 31.2 Frontend Web con Flask

El frontend recibe el brief del cliente, muestra el estado de procesamiento en tiempo real, y entrega los archivos generados.

### 31.2.1 Instalar Flask y Dependencias

```bash
#
source ~/venvs/llm/bin/activate
pip install flask flask-login flask-wtf werkzeug requests zipfile36

echo "[OK] Flask y dependencias instaladas"
```

### 31.2.2 Aplicación Flask Principal

```python
#!/usr/bin/env python3
"""
app.py — Frontend web de la Agencia de IA
Puerto: 5000 (Nginx lo expone en /agency/ via reverse proxy)
"""
import os
import uuid
import json
import time
import zipfile
import threading
from pathlib import Path
from datetime import datetime
from flask import (Flask, render_template, request, jsonify,
                   send_file, redirect, url_for, Response, stream_with_context)
from werkzeug.security import check_password_hash, generate_password_hash
import requests

# ── Configuración ──────────────────────────────────────────────────────────
BASE_DIR = Path.home() / "agencia"
ENTREGABLES_DIR = BASE_DIR / "entregables"
LOGS_DIR = BASE_DIR / "logs"
ENTREGABLES_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

OPENCLAW_URL = "http://localhost:18789"
OLLAMA_URL = "http://localhost:11434"
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/intake")

# Estado en memoria de proyectos activos (en producción usar Redis o BD)
proyectos: dict = {}

app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
app.secret_key = os.getenv("FLASK_SECRET", "cambiar_por_openssl_rand_hex_32")

# ── Tipos de servicio de la agencia ───────────────────────────────────────
SERVICIOS = {
    "contenido-blog": {
        "nombre": "Artículo de Blog",
        "descripcion": "Artículo optimizado SEO de 1.500–2.500 palabras con estructura profesional",
        "tiempo_estimado": "8–12 minutos",
        "precio": "$45",
        "agentes": ["analista", "redactor", "revisor"]
    },
    "estrategia-redes": {
        "nombre": "Estrategia de Redes Sociales",
        "descripcion": "Plan mensual con 20 publicaciones para LinkedIn, Facebook e Instagram",
        "tiempo_estimado": "12–18 minutos",
        "precio": "$89",
        "agentes": ["analista", "estratega", "redactor"]
    },
    "propuesta-comercial": {
        "nombre": "Propuesta Comercial",
        "descripcion": "Documento formal de propuesta adaptado al cliente y sector",
        "tiempo_estimado": "10–15 minutos",
        "precio": "$120",
        "agentes": ["analista", "redactor", "revisor"]
    },
    "informe-ejecutivo": {
        "nombre": "Informe Ejecutivo",
        "descripcion": "Resumen ejecutivo de datos o situación con conclusiones y recomendaciones",
        "tiempo_estimado": "6–10 minutos",
        "precio": "$65",
        "agentes": ["analista", "redactor"]
    },
}

# ── Rutas principales ─────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", servicios=SERVICIOS)

@app.route("/solicitar", methods=["GET", "POST"])
def solicitar():
    if request.method == "GET":
        servicio_id = request.args.get("servicio", "contenido-blog")
        servicio = SERVICIOS.get(servicio_id, SERVICIOS["contenido-blog"])
        return render_template("solicitar.html", servicio=servicio, servicio_id=servicio_id)

    # POST — recibir el formulario de intake
    datos = {
        "proyecto_id": str(uuid.uuid4())[:8].upper(),
        "servicio": request.form.get("servicio"),
        "empresa": request.form.get("empresa", "").strip(),
        "sector": request.form.get("sector", "").strip(),
        "brief": request.form.get("brief", "").strip(),
        "tono": request.form.get("tono", "profesional"),
        "email": request.form.get("email", "").strip(),
        "estado": "recibido",
        "inicio": datetime.now().isoformat(),
        "progreso": 0,
        "mensajes": [],
        "archivos": []
    }

    if not datos["brief"] or len(datos["brief"]) < 20:
        return jsonify({"error": "Brief demasiado corto — describa el proyecto con más detalle"}), 400

    proyectos[datos["proyecto_id"]] = datos

    # Notificar a N8N (asíncrono — no bloquear la respuesta)
    threading.Thread(target=notificar_n8n, args=(datos,), daemon=True).start()

    # Lanzar procesamiento en background
    threading.Thread(target=procesar_proyecto, args=(datos["proyecto_id"],), daemon=True).start()

    return redirect(url_for("estado_proyecto", proyecto_id=datos["proyecto_id"]))

@app.route("/proyecto/<proyecto_id>")
def estado_proyecto(proyecto_id: str):
    proyecto = proyectos.get(proyecto_id)
    if not proyecto:
        return render_template("error.html", mensaje="Proyecto no encontrado"), 404
    return render_template("estado.html", proyecto=proyecto)

@app.route("/proyecto/<proyecto_id>/stream")
def stream_estado(proyecto_id: str):
    """Server-Sent Events (SSE) — actualiza el estado en tiempo real sin polling."""
    def generar():
        ultima_pos = 0
        while True:
            proyecto = proyectos.get(proyecto_id)
            if not proyecto:
                yield f"data: {json.dumps({'error': 'Proyecto no encontrado'})}\n\n"
                break

            mensajes = proyecto.get("mensajes", [])
            if len(mensajes) > ultima_pos:
                for msg in mensajes[ultima_pos:]:
                    yield f"data: {json.dumps(msg)}\n\n"
                ultima_pos = len(mensajes)

            if proyecto.get("estado") in ("completado", "error"):
                yield f"data: {json.dumps({'tipo': 'fin', 'estado': proyecto['estado']})}\n\n"
                break

            time.sleep(1)

    return Response(
        stream_with_context(generar()),
        content_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )

@app.route("/proyecto/<proyecto_id>/descargar")
def descargar_entregables(proyecto_id: str):
    """Genera y entrega el ZIP con los archivos del proyecto."""
    proyecto = proyectos.get(proyecto_id)
    if not proyecto or proyecto.get("estado") != "completado":
        return jsonify({"error": "Proyecto no disponible para descarga"}), 404

    zip_path = ENTREGABLES_DIR / f"proyecto_{proyecto_id}.zip"
    if not zip_path.exists():
        return jsonify({"error": "Archivos no encontrados"}), 404

    return send_file(
        zip_path,
        as_attachment=True,
        download_name=f"entregables_{proyecto_id}.zip",
        mimetype="application/zip"
    )

@app.route("/health")
def health():
    return jsonify({"status": "ok", "proyectos_activos": len(proyectos)})

# ── Motor de procesamiento ────────────────────────────────────────────────

def agregar_mensaje(proyecto_id: str, tipo: str, texto: str, progreso: int = None):
    """Agrega un mensaje de estado al proyecto (visible via SSE)."""
    proyecto = proyectos.get(proyecto_id)
    if not proyecto:
        return
    msg = {"tipo": tipo, "texto": texto, "timestamp": datetime.now().strftime("%H:%M:%S")}
    proyecto["mensajes"].append(msg)
    if progreso is not None:
        proyecto["progreso"] = progreso

def procesar_proyecto(proyecto_id: str):
    """Pipeline completo de procesamiento con agentes. Se ejecuta en un thread separado."""
    proyecto = proyectos[proyecto_id]
    servicio_id = proyecto["servicio"]
    servicio = SERVICIOS.get(servicio_id, {})

    try:
        proyecto["estado"] = "procesando"
        agregar_mensaje(proyecto_id, "inicio",
                       f"Proyecto {proyecto_id} recibido. Servicio: {servicio.get('nombre', servicio_id)}", 5)

        # ── Fase 1: Análisis del brief ────────────────────────────────
        agregar_mensaje(proyecto_id, "agente", "Agente Analista activo — comprendiendo el brief...", 15)
        analisis = llamar_agente_analista(proyecto)
        if not analisis:
            raise RuntimeError("El agente analista no pudo procesar el brief")
        agregar_mensaje(proyecto_id, "progreso", f"Análisis completado: {analisis[:150]}...", 30)

        # ── Fase 2: Generación del contenido ─────────────────────────
        agregar_mensaje(proyecto_id, "agente", "Agente Redactor activo — generando el contenido...", 40)
        contenido = llamar_agente_redactor(proyecto, analisis)
        if not contenido:
            raise RuntimeError("El agente redactor no produjo contenido")
        agregar_mensaje(proyecto_id, "progreso",
                       f"Contenido generado: {len(contenido.split())} palabras", 65)

        # ── Fase 3: Revisión y refinamiento ──────────────────────────
        if "revisor" in servicio.get("agentes", []):
            agregar_mensaje(proyecto_id, "agente", "Agente Revisor activo — refinando el output...", 75)
            contenido = llamar_agente_revisor(proyecto, contenido)
            agregar_mensaje(proyecto_id, "progreso", "Revisión completada", 85)

        # ── Fase 4: Empaquetar entregables ───────────────────────────
        agregar_mensaje(proyecto_id, "sistema", "Empaquetando entregables...", 90)
        archivos = empaquetar_entregables(proyecto_id, proyecto, analisis, contenido)
        proyecto["archivos"] = archivos

        # ── Completado ────────────────────────────────────────────────
        proyecto["estado"] = "completado"
        proyecto["fin"] = datetime.now().isoformat()
        agregar_mensaje(proyecto_id, "completado",
                       f"[OK] Proyecto completado. {len(archivos)} archivos disponibles para descarga.", 100)

        # Notificar entrega a N8N
        threading.Thread(target=notificar_n8n_entrega, args=(proyecto,), daemon=True).start()

    except Exception as e:
        proyecto["estado"] = "error"
        agregar_mensaje(proyecto_id, "error", f"Error en el procesamiento: {str(e)}")
        log_error(proyecto_id, str(e))

def llamar_agente_analista(proyecto: dict) -> str:
    """Llama al Agente Analista via Ollama (modelo ligero para comprensión inicial)."""
    prompt = f"""Eres un analista de contenido especializado. Analiza este brief de cliente y extrae:
1. Objetivo principal del proyecto
2. Audiencia objetivo
3. Tono y estilo requerido
4. Puntos clave a cubrir
5. Restricciones o requisitos especiales

Empresa: {proyecto['empresa']}
Sector: {proyecto['sector']}
Tono solicitado: {proyecto['tono']}
Brief del cliente:
{proyecto['brief']}

Responde en formato estructurado y conciso."""

    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": "qwen3.5:4b", "prompt": prompt, "stream": False},
            timeout=120
        )
        return resp.json().get("response", "")
    except Exception as e:
        # Fallback: usar vLLM si Ollama no está disponible
        return llamar_vllm(prompt, max_tokens=800)

def llamar_agente_redactor(proyecto: dict, analisis: str) -> str:
    """Llama al Agente Redactor via vLLM (modelo poderoso para generación)."""
    servicio = SERVICIOS.get(proyecto["servicio"], {})
    prompt = f"""Eres un redactor profesional especializado en {proyecto['sector']}.
Basándote en el siguiente análisis, genera el {servicio.get('nombre', 'contenido')} solicitado.

ANÁLISIS DEL BRIEF:
{analisis}

EMPRESA: {proyecto['empresa']}
TONO: {proyecto['tono']}
BRIEF ORIGINAL: {proyecto['brief']}

Genera el contenido completo, profesional y listo para usar. Sin explicaciones adicionales."""

    return llamar_vllm(prompt, max_tokens=3000)

def llamar_agente_revisor(proyecto: dict, contenido: str) -> str:
    """Llama al Agente Revisor para refinar el contenido."""
    prompt = f"""Eres un editor profesional. Revisa y mejora este contenido:
- Corrige errores gramaticales o de coherencia
- Mejora la estructura si es necesario
- Asegura que el tono sea {proyecto['tono']}
- NO alteres el contenido fundamental, solo mejora la forma

CONTENIDO A REVISAR:
{contenido}

Devuelve el contenido revisado y mejorado, listo para entregar al cliente. Sin comentarios ni explicaciones."""

    return llamar_vllm(prompt, max_tokens=3500)

def llamar_vllm(prompt: str, max_tokens: int = 2000) -> str:
    """Llama a vLLM con el modelo Qwen3.5-35B para generación de alta calidad."""
    try:
        resp = requests.post(
            "http://localhost:8000/v1/chat/completions",
            json={
                "model": "qwen35",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.7
            },
            timeout=300
        )
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        # Fallback a Ollama si vLLM no está disponible
        try:
            resp = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": "qwen3.5:7b", "prompt": prompt, "stream": False},
                timeout=300
            )
            return resp.json().get("response", "")
        except:
            raise RuntimeError(f"Ni vLLM ni Ollama disponibles: {str(e)}")

def empaquetar_entregables(proyecto_id: str, proyecto: dict, analisis: str, contenido: str) -> list:
    """Empaqueta todos los archivos del proyecto en un ZIP."""
    zip_path = ENTREGABLES_DIR / f"proyecto_{proyecto_id}.zip"
    archivos = []

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Análisis del brief
        zf.writestr("01_analisis_brief.txt", analisis)
        archivos.append("01_analisis_brief.txt")

        # Contenido principal
        zf.writestr("02_contenido_principal.md", contenido)
        archivos.append("02_contenido_principal.md")

        # Metadatos del proyecto
        meta = {
            "proyecto_id": proyecto_id,
            "servicio": proyecto["servicio"],
            "empresa": proyecto["empresa"],
            "fecha_inicio": proyecto["inicio"],
            "fecha_fin": proyecto.get("fin", ""),
            "palabras_generadas": len(contenido.split()),
        }
        zf.writestr("00_metadatos.json", json.dumps(meta, indent=2, ensure_ascii=False))
        archivos.append("00_metadatos.json")

    return archivos

def notificar_n8n(datos: dict):
    """Notifica a N8N cuando llega un nuevo proyecto."""
    try:
        requests.post(N8N_WEBHOOK_URL, json={
            "evento": "nuevo_proyecto",
            "proyecto_id": datos["proyecto_id"],
            "servicio": datos["servicio"],
            "empresa": datos["empresa"],
            "email": datos["email"],
            "timestamp": datos["inicio"]
        }, timeout=10)
    except:
        pass  # N8N es opcional — no bloquear el flujo principal

def notificar_n8n_entrega(proyecto: dict):
    """Notifica a N8N cuando un proyecto está listo para entrega."""
    try:
        requests.post(f"{N8N_WEBHOOK_URL}-entrega", json={
            "evento": "proyecto_completado",
            "proyecto_id": proyecto["proyecto_id"],
            "empresa": proyecto["empresa"],
            "email": proyecto["email"],
            "archivos": proyecto.get("archivos", []),
            "url_descarga": f"/proyecto/{proyecto['proyecto_id']}/descargar",
            "timestamp": proyecto.get("fin", "")
        }, timeout=10)
    except:
        pass

def log_error(proyecto_id: str, error: str):
    log_file = LOGS_DIR / "errores.log"
    with open(log_file, "a") as f:
        f.write(f"{datetime.now().isoformat()} | {proyecto_id} | {error}\n")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
```

```bash
# Guardar la aplicación Flask
mkdir -p ~/agencia/web/templates ~/agencia/web/static/{css,js}
cp /dev/stdin ~/agencia/app.py << 'HEREDOC'
# (pegar el contenido del script anterior)
HEREDOC

echo "[OK] app.py guardado en ~/agencia/"
```

### 31.2.3 Templates HTML

```bash
# Template base
cat > ~/agencia/web/templates/base.html << 'EOF'
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}Agencia IA — Jetson{% endblock %}</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0f1117; color: #e2e8f0; min-height: 100vh; }
    .container { max-width: 900px; margin: 0 auto; padding: 2rem 1rem; }
    header { background: #1a2233; border-bottom: 2px solid #1d9cb8; padding: 1rem 2rem; display: flex; align-items: center; gap: 1rem; }
    header h1 { color: #1d9cb8; font-size: 1.4rem; }
    header span { color: #64748b; font-size: 0.85rem; }
    .card { background: #1a2233; border: 1px solid #2d3748; border-radius: 8px; padding: 1.5rem; margin: 1rem 0; }
    .btn { display: inline-block; background: #1d9cb8; color: white; padding: 0.75rem 1.5rem; border-radius: 6px; border: none; cursor: pointer; font-size: 1rem; text-decoration: none; transition: background 0.2s; }
    .btn:hover { background: #0f8fa8; }
    .btn-outline { background: transparent; border: 1px solid #1d9cb8; color: #1d9cb8; }
    .badge { display: inline-block; padding: 0.25rem 0.6rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
    .badge-ok { background: #064e3b; color: #34d399; }
    .badge-warn { background: #78350f; color: #fbbf24; }
    .badge-err { background: #7f1d1d; color: #f87171; }
    label { display: block; margin-bottom: 0.4rem; color: #94a3b8; font-size: 0.9rem; }
    input, textarea, select { width: 100%; background: #0f1117; border: 1px solid #2d3748; color: #e2e8f0; padding: 0.6rem 0.8rem; border-radius: 6px; font-size: 0.95rem; margin-bottom: 1rem; }
    textarea { min-height: 120px; resize: vertical; }
    input:focus, textarea:focus, select:focus { outline: none; border-color: #1d9cb8; }
    .progress-bar { background: #2d3748; border-radius: 4px; height: 8px; overflow: hidden; margin: 0.5rem 0; }
    .progress-fill { background: #1d9cb8; height: 100%; transition: width 0.5s ease; }
    .log-entry { padding: 0.4rem 0.6rem; border-radius: 4px; margin: 0.3rem 0; font-size: 0.85rem; font-family: monospace; }
    .log-inicio { background: #1e3a5f; color: #93c5fd; }
    .log-agente { background: #1a3a2a; color: #6ee7b7; }
    .log-progreso { background: #2d1b69; color: #c4b5fd; }
    .log-sistema { background: #1a2233; color: #94a3b8; }
    .log-completado { background: #064e3b; color: #34d399; font-weight: 600; }
    .log-error { background: #7f1d1d; color: #f87171; }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Agencia IA</h1>
      <span>Powered by NVIDIA Jetson AGX Orin 64GB · Offline</span>
    </div>
  </header>
  <div class="container">
    {% block content %}{% endblock %}
  </div>
</body>
</html>
EOF
```

```bash
# Template de página principal
cat > ~/agencia/web/templates/index.html << 'EOF'
{% extends "base.html" %}
{% block title %}Servicios — Agencia IA{% endblock %}
{% block content %}
<h2 style="margin: 1.5rem 0 0.5rem; color: #1d9cb8;">Nuestros Servicios de IA</h2>
<p style="color: #64748b; margin-bottom: 1.5rem;">Contenido profesional generado por inteligencia artificial especializada. Entrega en minutos, no en días.</p>

{% for id, s in servicios.items() %}
<div class="card" style="display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem;">
  <div style="flex: 1;">
    <h3 style="color: #e2e8f0; margin-bottom: 0.3rem;">{{ s.nombre }}</h3>
    <p style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 0.5rem;">{{ s.descripcion }}</p>
    <span style="color: #64748b; font-size: 0.8rem;">[TIEMPO] {{ s.tiempo_estimado }}</span>
  </div>
  <div style="text-align: right; flex-shrink: 0;">
    <div style="color: #1d9cb8; font-size: 1.3rem; font-weight: 700; margin-bottom: 0.5rem;">{{ s.precio }}</div>
    <a href="{{ url_for('solicitar', servicio=id) }}" class="btn" style="font-size: 0.85rem; padding: 0.5rem 1rem;">Solicitar →</a>
  </div>
</div>
{% endfor %}

<div class="card" style="margin-top: 2rem; text-align: center; border-color: #1d9cb8;">
  <p style="color: #94a3b8; font-size: 0.85rem;">[SEGURO] Procesamiento 100% offline · Sus datos no salen del servidor · Sin suscripción ni límites de uso</p>
</div>
{% endblock %}
EOF
```

```bash
# Template de estado del proyecto con SSE
cat > ~/agencia/web/templates/estado.html << 'EOF'
{% extends "base.html" %}
{% block title %}Proyecto {{ proyecto.proyecto_id }} — Estado{% endblock %}
{% block content %}
<div style="margin: 1rem 0;">
  <h2 style="color: #1d9cb8;">Proyecto <code>{{ proyecto.proyecto_id }}</code></h2>
  <p style="color: #64748b; margin-top: 0.3rem;">{{ proyecto.empresa }} · {{ proyecto.servicio }}</p>
</div>

<div class="card">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem;">
    <span id="estado-label" class="badge badge-warn">Procesando...</span>
    <span id="progreso-pct" style="color: #64748b; font-size: 0.85rem;">0%</span>
  </div>
  <div class="progress-bar">
    <div class="progress-fill" id="progress-fill" style="width: 0%"></div>
  </div>
</div>

<div class="card">
  <h4 style="color: #94a3b8; margin-bottom: 0.8rem; font-size: 0.85rem;">REGISTRO DE ACTIVIDAD</h4>
  <div id="log-container" style="max-height: 300px; overflow-y: auto;">
    {% for msg in proyecto.mensajes %}
    <div class="log-entry log-{{ msg.tipo }}">
      <span style="opacity: 0.6;">{{ msg.timestamp }}</span> · {{ msg.texto }}
    </div>
    {% endfor %}
  </div>
</div>

<div id="descarga-section" style="display: none;" class="card">
  <h3 style="color: #34d399; margin-bottom: 1rem;">[OK] Entregables listos</h3>
  <p style="color: #94a3b8; margin-bottom: 1rem;">Su proyecto ha sido procesado. Descargue los archivos a continuación.</p>
  <a href="{{ url_for('descargar_entregables', proyecto_id=proyecto.proyecto_id) }}" class="btn">
    ⬇ Descargar entregables (ZIP)
  </a>
</div>

<div id="error-section" style="display: none;" class="card" style="border-color: #f87171;">
  <h3 style="color: #f87171;">[ERROR] Error en el procesamiento</h3>
  <p style="color: #94a3b8;">Ha ocurrido un error. Revise el registro de actividad para más detalles.</p>
</div>

<script>
const logContainer = document.getElementById("log-container");
const progressFill = document.getElementById("progress-fill");
const progressPct = document.getElementById("progreso-pct");
const estadoLabel = document.getElementById("estado-label");

const evtSource = new EventSource("{{ url_for('stream_estado', proyecto_id=proyecto.proyecto_id) }}");

evtSource.onmessage = function(event) {
  const data = JSON.parse(event.data);

  if (data.tipo === "fin") {
    evtSource.close();
    if (data.estado === "completado") {
      estadoLabel.textContent = "Completado";
      estadoLabel.className = "badge badge-ok";
      document.getElementById("descarga-section").style.display = "block";
    } else {
      estadoLabel.textContent = "Error";
      estadoLabel.className = "badge badge-err";
      document.getElementById("error-section").style.display = "block";
    }
    return;
  }

  // Nuevo mensaje de log
  const div = document.createElement("div");
  div.className = "log-entry log-" + (data.tipo || "sistema");
  div.innerHTML = `<span style="opacity:0.6">${data.timestamp || ""}</span> · ${data.texto}`;
  logContainer.appendChild(div);
  logContainer.scrollTop = logContainer.scrollHeight;
};

// Polling de progreso separado (cada 3 segundos)
const pollProgress = setInterval(async () => {
  try {
    const resp = await fetch("/health");
    // En una implementación real, hacer GET /proyecto/<id>/progreso
  } catch(e) {}
}, 3000);
</script>
{% endblock %}
EOF
```

---

## 31.3 Workflow de N8N para la Agencia

N8N automatiza las notificaciones y el registro de proyectos. Al recibir un proyecto nuevo, envía email de confirmación al cliente; al completarse, envía los entregables.

### 31.3.1 Configurar los Webhooks en N8N

```bash
# Verificar que N8N está activo (Capítulo 27)
curl -s http://localhost:5678/healthz && echo "[OK] N8N activo"

# La variable N8N_WEBHOOK_URL en app.py debe apuntar al webhook correcto
# Ejemplo: http://localhost:5678/webhook/intake
```

El workflow de N8N se importa desde el panel web (`http://localhost:5678`):

**Workflow 1 — Intake Confirmation:**
```json
{
  "name": "Agencia — Intake Confirmation",
  "nodes": [
    {
      "name": "Webhook Intake",
      "type": "n8n-nodes-base.webhook",
      "parameters": {
        "path": "intake",
        "responseMode": "responseNode",
        "httpMethod": "POST"
      }
    },
    {
      "name": "Registrar en PostgreSQL",
      "type": "n8n-nodes-base.postgres",
      "parameters": {
        "operation": "insert",
        "table": "proyectos",
        "columns": "proyecto_id, empresa, servicio, email, estado, fecha_inicio",
        "values": "={{ $json.proyecto_id }}, {{ $json.empresa }}, {{ $json.servicio }}, {{ $json.email }}, 'recibido', {{ $json.timestamp }}"
      }
    },
    {
      "name": "Email Confirmación",
      "type": "n8n-nodes-base.emailSend",
      "parameters": {
        "toEmail": "={{ $json.email }}",
        "subject": "Proyecto {{ $json.proyecto_id }} recibido — Agencia IA",
        "text": "Hemos recibido su solicitud. Su proyecto {{ $json.proyecto_id }} está siendo procesado y recibirá los entregables en breve."
      }
    }
  ]
}
```

```bash
# Crear la tabla de proyectos en PostgreSQL (desde el container N8N)
# Obtener la IP del gateway del bridge de N8N
N8N_GATEWAY=$(docker exec n8n ip route | grep default | awk '{print $3}')
echo "Gateway N8N: $N8N_GATEWAY"

# Crear la tabla directamente en el container de postgres
docker exec -it postgres psql -U n8n -d n8n << 'SQL'
CREATE TABLE IF NOT EXISTS proyectos (
    id SERIAL PRIMARY KEY,
    proyecto_id VARCHAR(20) UNIQUE NOT NULL,
    empresa VARCHAR(255),
    servicio VARCHAR(100),
    email VARCHAR(255),
    estado VARCHAR(50) DEFAULT 'recibido',
    fecha_inicio TIMESTAMP,
    fecha_fin TIMESTAMP,
    palabras_generadas INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_proyectos_email ON proyectos(email);
CREATE INDEX IF NOT EXISTS idx_proyectos_estado ON proyectos(estado);
SQL
echo "[OK] Tabla proyectos creada"
```

---

## 31.4 Integración con OpenClaw para Agentes Especializados

Para casos de uso más complejos, los agentes de OpenClaw reemplazan las llamadas directas al LLM con agentes con memoria, herramientas y contexto persistente.

```bash
# Verificar que OpenClaw está activo (Capítulo 13)
curl -s http://localhost:18789/health && echo "[OK] OpenClaw activo"

# Configurar los perfiles de agente para la agencia
cat > ~/.openclaw/agents/analista-agencia.json << 'EOF'
{
  "id": "analista-agencia",
  "name": "Analista de Proyectos",
  "description": "Analiza briefs de clientes y extrae requerimientos estructurados",
  "model": {
    "primary": "vllm/qwen35",
    "fallback": "ollama/qwen3.5:7b"
  },
  "system_prompt": "Eres un analista de proyectos de contenido experto. Tu trabajo es comprender exactamente qué necesita el cliente, identificar los entregables esperados, y estructurar los requerimientos de forma clara para el equipo de redacción.",
  "tools": {
    "profile": "full"
  },
  "memory": {
    "enabled": true,
    "context_window": 8192
  }
}
EOF

cat > ~/.openclaw/agents/redactor-agencia.json << 'EOF'
{
  "id": "redactor-agencia",
  "name": "Redactor Especializado",
  "description": "Genera contenido profesional de alta calidad",
  "model": {
    "primary": "vllm/qwen35",
    "fallback": "ollama/qwen3.5:7b"
  },
  "system_prompt": "Eres un redactor profesional con experiencia en marketing de contenidos, comunicación corporativa y escritura persuasiva. Produces contenido original, bien estructurado y adaptado al tono y audiencia de cada cliente.",
  "tools": {
    "profile": "full"
  }
}
EOF
```

```python
# Función alternativa que usa OpenClaw en lugar de llamadas directas al LLM
def llamar_openclaw_agente(agente_id: str, mensaje: str, contexto: dict = None) -> str:
    """Llama a un agente de OpenClaw con contexto del proyecto."""
    payload = {
        "agent_id": agente_id,
        "message": mensaje,
        "context": contexto or {},
        "session_id": f"agencia-{agente_id}"
    }
    try:
        resp = requests.post(
            f"{OPENCLAW_URL}/v1/agents/{agente_id}/chat",
            json=payload,
            timeout=300
        )
        resp.raise_for_status()
        return resp.json().get("content", "")
    except Exception as e:
        raise RuntimeError(f"OpenClaw no disponible: {str(e)}")
```

---

## 31.5 Iniciar el Stack Completo

### 31.5.1 Script de Arranque de la Agencia

```bash
cat > ~/scripts/agency-start.sh << 'EOF'
#!/bin/bash
# agency-start.sh — Inicia el stack completo de la Agencia IA
# Tiempo estimado: 8-12 minutos (descarga de modelos en primer arranque)
set -euo pipefail

echo "╔══════════════════════════════════════════════════════╗"
echo "║         Agencia IA — Arranque del Stack Completo     ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── 0. Modo energético ────────────────────────────────────────────────
echo "[0/7] Configurando modo energético..."
pwr-30w   # Empezar en 30W; se activará MAXN automáticamente al procesar
sudo jetson_clocks
echo "  [OK] 30W activo (MAXN se activará al procesar)"

# ── 1. Docker ─────────────────────────────────────────────────────────
echo "[1/7] Iniciando Docker..."
sudo systemctl start docker.socket && sudo systemctl start docker
sleep 2
echo "  [OK] Docker activo"

# ── 2. Ollama (agente rápido — modelo 4B) ────────────────────────────
echo "[2/7] Iniciando Ollama (qwen3.5:4b para agentes)..."
ollama serve &> ~/logs/ollama.log &
sleep 5
if ! ollama list | grep -q "qwen3.5"; then
    echo "  Descargando modelo qwen3.5:4b (primera vez — ~3 GB)..."
    ollama pull qwen3.5:4b
fi
echo "  [OK] Ollama activo en :11434"

# ── 3. vLLM (modelo 35B — para generación de alta calidad) ───────────
echo "[3/7] Iniciando vLLM Qwen3.5-35B-A3B..."
pwr-maxn  # Activar MAXN para el arranque del modelo grande
docker run --runtime nvidia -d \
  --name qwen35-35b --restart no \
  --network host --ipc host --shm-size 8g \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16 \
      --gpu-memory-utilization 0.70 \
      --enable-prefix-caching \
      --served-model-name qwen35 \
      --host 0.0.0.0 --port 8000 \
      --max-model-len 8192"

echo -n "  Esperando vLLM Qwen3.5-35B (puede tardar 5-8 min en primer arranque)"
until curl -sf http://localhost:8000/v1/models > /dev/null 2>&1; do
    echo -n "."; sleep 15
done
echo " [OK] vLLM activo en :8000"

# ── 4. N8N ────────────────────────────────────────────────────────────
echo "[4/7] Iniciando N8N + PostgreSQL..."
cd ~/stacks/n8n && docker compose up -d
sleep 5
echo "  [OK] N8N activo en :5678"

# ── 5. OpenClaw ───────────────────────────────────────────────────────
echo "[5/7] Iniciando OpenClaw..."
openclaw-start 2>/dev/null || true
sleep 3
curl -sf http://localhost:18789/health > /dev/null && echo "  [OK] OpenClaw activo en :18789" \
  || echo "  [WARN]  OpenClaw no responde — verificar instalación (Capítulo 13)"

# ── 6. Flask Web Frontend ─────────────────────────────────────────────
echo "[6/7] Iniciando Flask frontend..."
source ~/venvs/llm/bin/activate
cd ~/agencia
nohup python3 app.py > ~/logs/flask_agencia.log 2>&1 &
echo $! > ~/scripts/flask_agencia.pid
sleep 3
curl -sf http://localhost:5000/health > /dev/null && echo "  [OK] Flask activo en :5000" \
  || echo "  [WARN]  Flask no responde — ver ~/logs/flask_agencia.log"

# ── 7. Nginx + Gateway ────────────────────────────────────────────────
echo "[7/7] Iniciando gateway de infraestructura..."
~/scripts/gateway/gateway-manage.sh start 2>/dev/null || true

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║           Stack de Agencia IA — ACTIVO               ║"
echo "╚══════════════════════════════════════════════════════╝"
JETSON_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "   Web local:     http://$JETSON_IP:5000"
echo "   Via gateway:   http://$JETSON_IP:8088/agency/"
echo "  🤖 vLLM:          http://$JETSON_IP:8000/v1/models"
echo "  ⚙️  N8N:           http://$JETSON_IP:5678"
echo "  🧠 OpenClaw:      http://$JETSON_IP:18789"
echo ""
echo "  jtop   para monitorear el sistema"
echo "  agency-stop   para detener todo"
echo ""
EOF

chmod +x ~/scripts/agency-start.sh
```

```bash
cat > ~/scripts/agency-stop.sh << 'EOF'
#!/bin/bash
# agency-stop.sh — Detiene el stack completo de la Agencia IA
echo "Deteniendo stack de la Agencia IA..."

# Flask
[ -f ~/scripts/flask_agencia.pid ] && kill "$(cat ~/scripts/flask_agencia.pid)" 2>/dev/null || true
pkill -f "app.py" 2>/dev/null || true
echo "  [OK] Flask detenido"

# vLLM
docker stop qwen35-35b 2>/dev/null && docker rm qwen35-35b 2>/dev/null || true
echo "  [OK] vLLM detenido"

# N8N
cd ~/stacks/n8n && docker compose down
echo "  [OK] N8N detenido"

# OpenClaw
openclaw-stop 2>/dev/null || true
echo "  [OK] OpenClaw detenido"

# Ollama
pkill -f "ollama serve" 2>/dev/null || true
echo "  [OK] Ollama detenido"

# Limpieza de caché y swap
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
sudo swapoff -a && sudo swapon -a

# Modo economía
pwr-15w
echo ""
echo "[OK] Stack de la Agencia IA detenido. Sistema en modo 15W."
EOF

chmod +x ~/scripts/agency-stop.sh
```

### 31.5.2 Aliases Finales

```bash
# Agregar al ~/.bash_aliases
cat >> ~/.bash_aliases << 'EOF'

# ── Agencia IA — Capstone ────────────────────────────────────────────
alias agency-start='~/scripts/agency-start.sh'
alias agency-stop='~/scripts/agency-stop.sh'
alias agency-status='curl -s http://localhost:5000/health | python3 -m json.tool; curl -s http://localhost:8000/v1/models | python3 -m json.tool'
alias agency-logs='tail -f ~/logs/flask_agencia.log'
alias agency-vllm-logs='docker logs qwen35-35b --follow'
alias agency-n8n-logs='cd ~/stacks/n8n && docker compose logs --tail=50 -f'
EOF

source ~/.bash_aliases
```

---

## 31.6 Monitoreo del Stack

```bash
# Verificar estado completo del sistema durante operación
jtop   # Monitor de GPU, RAM, temperatura, potencia

# Monitoreo de contenedores activos
docker stats qwen35-35b n8n postgres --no-stream

# Logs en tiempo real de todos los componentes
tail -f ~/logs/flask_agencia.log ~/logs/ollama.log ~/logs/gateway/access.log
```

---

## 31.7 Solución de Problemas

### vLLM OOM al procesar proyecto largo

```bash
# Reducir gpu-memory-utilization al reiniciar
docker stop qwen35-35b && docker rm qwen35-35b
sudo sync && sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
sudo swapoff -a && sudo swapon -a

docker run --runtime nvidia -d \
  --name qwen35-35b --restart no \
  --network host --ipc host --shm-size 8g \
  ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16 \
      --gpu-memory-utilization 0.65 \
      --served-model-name qwen35 \
      --host 0.0.0.0 --port 8000 --max-model-len 8192"
```

### Flask no inicia: `Address already in use`

```bash
# Ver qué usa el puerto 5000
sudo lsof -i :5000
# Matar el proceso anterior
pkill -f "app.py" && sleep 2
source ~/venvs/llm/bin/activate
cd ~/agencia && python3 app.py &
```

### N8N no recibe los webhooks de Flask

```bash
# El webhook URL debe usar la IP real del Jetson, no localhost
# Flask llama a N8N que está en Docker bridge (no puede usar localhost del host)
JETSON_IP=$(hostname -I | awk '{print $1}')
echo "URL correcta para N8N_WEBHOOK_URL: http://$JETSON_IP:5678/webhook/intake"

# Actualizar la variable en app.py o en el entorno
export N8N_WEBHOOK_URL="http://$JETSON_IP:5678/webhook/intake"
```

---

## 31.8 Escalabilidad — Modo Mixto y Gestión de Memoria

### 31.8.1 Presupuesto de Memoria — Qué Cargar y Cuándo

El Jetson AGX Orin 64GB tiene **~59 GB disponibles** para aplicaciones (el OS base consume ~12 GB del sistema de archivos unificado CPU/GPU). La agencia completa en modo activo consume ~46.5 GB, dejando **~17.5 GB de margen** — suficiente para un servicio adicional, pero no para dos modelos grandes simultáneos.

**Guía de gestión de memoria:**

| Estado de la agencia | Qué cargar | Qué detener | RAM libre aprox. |
|---|---|---|---|
| En espera (sin clientes activos) | Ollama 4B + OpenClaw + N8N + Flask | vLLM 35B detenido | ~43 GB |
| Procesando proyecto pequeño | Ollama 4B (activo) | vLLM 35B | ~38 GB |
| Procesando proyecto complejo | vLLM 35B (activo) + Ollama 4B | — | ~17 GB |
| Máxima capacidad | vLLM 35B + Ollama 4B + STT + TTS | Uptime Kuma, logs | ~10 GB |

> **ADVERTENCIA:** Cargar vLLM 35B + Ollama 7B + faster-whisper + kokoro-tts simultáneamente supera los 59 GB disponibles y generará errores OOM. Si necesita inferencia de alta calidad más voz, use Ollama con el modelo 4B durante la síntesis de voz y cambie a vLLM solo durante la generación de contenido.

**Script de gestión dinámica de memoria:**

```bash
# agency-mem.sh — libera vLLM cuando no hay proyectos activos
# Añadir al crontab: */5 * * * * ~/scripts/agency-mem.sh

#!/bin/bash
PROYECTOS_ACTIVOS=$(curl -s http://localhost:5000/api/status | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(len([p for p in d.get('projects',[]) if p['status']=='processing']))" 2>/dev/null || echo "0")

if [ "$PROYECTOS_ACTIVOS" -eq 0 ]; then
    # Sin proyectos activos — detener vLLM para liberar ~26 GB
    docker stop vllm-agency 2>/dev/null && echo "[$(date)] vLLM detenido — sin proyectos activos"
fi
```

### 31.8.2 Modo Mixto — Integración con OpenRouter

Para proyectos de cliente que requieran capacidades que superen los modelos locales (análisis de documentos muy largos, traducción a idiomas poco representados, procesamiento multilingüe avanzado), integre OpenRouter como backend alternativo:

```python
import os
from openai import OpenAI

USE_LOCAL = os.getenv("USE_LOCAL_LLM", "true").lower() == "true"

if USE_LOCAL:
    # vLLM local — máxima privacidad de datos del cliente
    client = OpenAI(base_url="http://localhost:8000/v1", api_key=os.getenv("VLLM_API_KEY", ""))
    MODEL  = "qwen3.5-35b"
else:
    # OpenRouter — modelos de mayor capacidad cuando se requieran
    client = OpenAI(
        base_url=os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1"),
        api_key=os.getenv("OPENROUTER_API_KEY", ""),
    )
    MODEL = "meta-llama/llama-3.3-70b-instruct:free"
```

```bash
# Aliases en ~/.bash_aliases (ver Capítulo 6)
alias agency-local="USE_LOCAL_LLM=true"
alias agency-cloud="USE_LOCAL_LLM=false"
```

> **NOTA:** El modo cloud envía los briefs de los clientes a servidores externos. Informe a sus clientes si sus datos serán procesados fuera de la red local. Para clientes con requerimientos de confidencialidad estrictos, use siempre el modo local.

### 31.8.3 Evaluación de Capacidad de Clientes Simultáneos

La arquitectura actual soporta **un proyecto activo a la vez** con el LLM de 35B. Para servir múltiples clientes simultáneamente, configure vLLM con continuous batching:

```bash
# vLLM con batching para múltiples requests simultáneos
docker run -d --rm --runtime nvidia \
  --name vllm-agency \
  -p 8000:8000 \
  -v ~/data/models:/models \
  dustynv/vllm:r39.2.0 \
  --model /models/qwen3.5-35b \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.60 \
  --max-num-seqs 4   # hasta 4 requests simultáneos

# Monitorear throughput
curl -s http://localhost:8000/metrics | grep vllm_requests
```

---

## Resumen Final del Libro

> El resumen completo del libro se encuentra en el **Capítulo 33 — Conclusiones**. Continúe allí para el balance integral de todo lo construido y los próximos pasos recomendados.
