# Capítulo 23 — Agencia de Turismo Virtual con OpenClaw/NemoClaw

## Introducción

Este capítulo construye un sistema multi-agente que simula una agencia de turismo operada por inteligencia artificial. El cliente interactúa en lenguaje natural y tres agentes especializados colaboran para responder: uno provee información sobre destinos, otro diseña itinerarios detallados y el tercero estima presupuestos.

El sistema usa OpenClaw como orquestador (ya instalado en el Capítulo 13) y Ollama como motor de inferencia, con modelos de 7B para respuestas rápidas y 14B para itinerarios complejos.

**Prerrequisitos:**
- Capítulo 13 completado (OpenClaw/NemoClaw activo en puerto 18789)
- Ollama con `qwen3:7b` instalado
- Python 3.12 + venv de desarrollo (Capítulo 7)

**Tiempo de respuesta estimado:**
- Consulta simple (info de destino): 3–6 segundos
- Itinerario completo (7 días): 25–40 segundos
- Estimación de presupuesto: 5–10 segundos

**Modo de energía:** 30W (modelos ≤7B para consultas normales); MAXN al generar itinerarios con modelo 14B

---

## 21.1 Prerrequisito — Verificación del Sistema

```bash
# Verificar que OpenClaw está activo
check-ready 15 "tourism-agency"

# Verificar OpenClaw
curl -sf http://localhost:18789/api/health | python3 -m json.tool \
  || echo "[WARN]  OpenClaw no activo — ver Capítulo 13"

# Verificar modelos Ollama disponibles
ollama list

# Si no tiene qwen3:7b, descargarlo
ollama list | grep -q "qwen3:7b" || ollama pull qwen3:7b

pwr-30w
```

---

## 21.2 Arquitectura del Sistema

<!-- INFOGRAFÍA: Arquitectura del Sistema de Agencia de Turismo Virtual — pendiente de diseño gráfico (paleta NVIDIA #0F3D3D / accent #1D9CB8, texto mínimo 10pt, optimizado para KDP Kindle dark/light) -->


```bash
┌─────────────────────────────────────────────────────────────┐
│           AGENCIA DE TURISMO VIRTUAL — ARQUITECTURA          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Cliente (terminal / WhatsApp)                             │
│      │                                                      │
│      ▼                                                      │
│  NemoClaw (Orquestador — puerto 18789)                     │
│      │                                                      │
│      ├─► Agente Consultor  (qwen3:7b)                      │
│      │    • Información sobre destinos                      │
│      │    • Mejores épocas para viajar                      │
│      │    • Requisitos de visa/documentos                   │
│      │                                                      │
│      ├─► Agente Itinerario (qwen3:7b o 14b si disponible)  │
│      │    • Itinerarios día a día                           │
│      │    • Actividades recomendadas                        │
│      │    • Hoteles y restaurantes                          │
│      │                                                      │
│      └─► Agente Presupuesto (qwen3:7b)                     │
│           • Estimación de costos por categoría              │
│           • Comparación económica vs premium                │
│           • Alerta de temporada alta/baja                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 21.3 Configurar los Agentes en OpenClaw

```bash
# Crear el directorio del proyecto
mkdir -p ~/projects/tourism-agency
cd ~/projects/tourism-agency
```

### 21.3.1 Definición de Agentes via API de OpenClaw

```python
# setup_agents.py
"""
Configura los tres agentes de la agencia de turismo en OpenClaw.
"""
import requests
import json

OPENCLAW_URL = "http://localhost:18789"

def crear_agente(nombre: str, sistema: str, modelo: str = "qwen3:7b") -> dict:
    """Crea o actualiza un agente en OpenClaw."""
    payload = {
        "name": nombre,
        "model": modelo,
        "system_prompt": sistema,
        "tool_profile": "full",  # herramientas completas
        "temperature": 0.7,
        "max_tokens": 1200
    }
    
    resp = requests.post(
        f"{OPENCLAW_URL}/api/agents",
        json=payload,
        timeout=30
    )
    
    if resp.status_code in (200, 201):
        print(f"  [OK] Agente '{nombre}' configurado")
        return resp.json()
    else:
        print(f"  [WARN]  Error creando agente '{nombre}': {resp.status_code} — {resp.text[:100]}")
        return {}


# ── Agente Consultor ──────────────────────────────────────
crear_agente(
    nombre="consultor-turismo",
    modelo="qwen3:7b",
    sistema="""Eres Ana, una consultora de viajes experta con 15 años de experiencia.
    
Tu especialidad:
- Información actualizada sobre destinos turísticos mundiales
- Mejores épocas para viajar, clima y temporadas
- Requisitos de visa, vacunas y documentación necesaria
- Atracciones principales y experiencias únicas por destino
- Diferencias culturales importantes a tener en cuenta

Responde siempre de forma amable, profesional y concisa.
Si no tienes información actualizada sobre algo específico, indícalo claramente.
Idioma: responde en el mismo idioma en que te pregunten."""
)

# ── Agente Itinerario ─────────────────────────────────────
crear_agente(
    nombre="agente-itinerario",
    modelo="qwen3:7b",
    sistema="""Eres Carlos, un planificador de itinerarios de viaje experto.

Tu especialidad:
- Diseñar itinerarios detallados día a día
- Organizar visitas de forma lógica (minimizando desplazamientos)
- Recomendar actividades para diferentes tipos de viajero (familia, aventura, cultura, romance)
- Sugerir restaurantes locales y opciones de hospedaje por categoría
- Incluir tiempos estimados y consejos logísticos

Formato de itinerario:
- Día 1: [Ciudad] — [Actividades]
  - Mañana: [detalle]
  - Tarde: [detalle]
  - Noche: [restaurante sugerido]
  - Alojamiento: [sugerencia con precio estimado en rango]

Adapta el nivel de detalle según la duración del viaje solicitado."""
)

# ── Agente Presupuesto ────────────────────────────────────
crear_agente(
    nombre="agente-presupuesto",
    modelo="qwen3:7b",
    sistema="""Eres María, especialista en presupuestos de viaje.

Tu especialidad:
- Estimar costos realistas por categoría: vuelos, hospedaje, alimentación, actividades, transporte local
- Distinguir entre viaje económico, estándar y premium
- Identificar temporada alta/baja y su impacto en precios
- Sugerir estrategias de ahorro sin sacrificar experiencia
- Proporcionar rangos de precios (no cifras exactas — los precios varían)

Siempre aclara: "Los precios son estimados y pueden variar según fecha de reserva y disponibilidad."
Usa la moneda más apropiada para el destino, con conversión a USD si es relevante."""
)

print("\n[OK] Todos los agentes configurados")
print("   Verifique en: http://localhost:18789/api/agents")
```

```bash
source ~/venvs/dev/bin/activate
python setup_agents.py
```

---

## 21.4 Interfaz de Conversación por Terminal

```python
# tourism_chat.py
"""
Interfaz de conversación con la agencia de turismo.
Enruta automáticamente las preguntas al agente más apropiado.
"""
import requests
import json
import re

OPENCLAW_URL = "http://localhost:18789"

# Palabras clave para clasificar la consulta
RUTAS = {
    "consultor-turismo": [
        "información", "info", "conocer", "visitar", "clima", "temporada",
        "visa", "vacuna", "documentos", "cuándo", "cuando", "mejor época",
        "cultura", "idioma", "moneda", "seguridad"
    ],
    "agente-itinerario": [
        "itinerario", "plan", "días", "semana", "agenda", "actividades",
        "qué hacer", "que hacer", "recorrido", "ruta", "viaje de",
        "hotel", "restaurante", "hospedaje", "alojamiento"
    ],
    "agente-presupuesto": [
        "presupuesto", "costo", "precio", "cuánto", "cuanto", "económico",
        "barato", "caro", "gastar", "dinero", "euro", "dólar", "estimación"
    ]
}


def clasificar_consulta(texto: str) -> str:
    """Determina qué agente debe responder a la consulta."""
    texto_lower = texto.lower()
    puntajes = {agente: 0 for agente in RUTAS}
    
    for agente, palabras in RUTAS.items():
        for palabra in palabras:
            if palabra in texto_lower:
                puntajes[agente] += 1
    
    # Si hay empate o sin coincidencias, usar el consultor como default
    max_score = max(puntajes.values())
    if max_score == 0:
        return "consultor-turismo"
    
    return max(puntajes, key=puntajes.get)


def consultar_agente(agente: str, mensaje: str, historial: list) -> str:
    """Envía un mensaje al agente específico de OpenClaw."""
    
    # Agregar el mensaje al historial
    historial.append({"role": "user", "content": mensaje})
    
    payload = {
        "agent": agente,
        "messages": historial[-6:],  # últimos 6 turnos para contexto
        "stream": False
    }
    
    try:
        resp = requests.post(
            f"{OPENCLAW_URL}/api/chat",
            json=payload,
            timeout=120
        )
        
        if resp.status_code == 200:
            data = resp.json()
            respuesta = data.get("message", {}).get("content", "Sin respuesta")
            historial.append({"role": "assistant", "content": respuesta})
            return respuesta
        else:
            return f"[Error HTTP {resp.status_code}: {resp.text[:100]}]"
            
    except requests.Timeout:
        return "[Timeout — el agente tardó demasiado. Intente de nuevo.]"
    except Exception as e:
        return f"[Error de conexión: {str(e)}]"


def mostrar_bienvenida():
    print("""
╔══════════════════════════════════════════════════════════╗
║       AGENCIA DE TURISMO VIRTUAL — JETSON AI             ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  Su equipo de expertos:                                  ║
║  • Ana (Consultora) — información y destinos             ║
║  • Carlos (Planificador) — itinerarios detallados        ║
║  • María (Presupuestos) — costos y estimaciones          ║
║                                                          ║
║  Comandos especiales:                                    ║
║  /consultor — hablar con Ana                             ║
║  /itinerario — hablar con Carlos                         ║
║  /presupuesto — hablar con María                         ║
║  /salir — terminar la conversación                       ║
╚══════════════════════════════════════════════════════════╝
""")


def main():
    mostrar_bienvenida()
    historial = []
    agente_forzado = None
    
    while True:
        try:
            entrada = input("Usted: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n¡Hasta luego! Fue un placer asistirle.")
            break
        
        if not entrada:
            continue
        
        if entrada.lower() in ("/salir", "/exit", "salir", "exit"):
            print("\n¡Hasta luego! Fue un placer asistirle.")
            break
        
        # Comandos de agente forzado
        if entrada.lower() == "/consultor":
            agente_forzado = "consultor-turismo"
            print("OK Conectando con Ana (Consultora)...")
            continue
        elif entrada.lower() == "/itinerario":
            agente_forzado = "agente-itinerario"
            print("OK Conectando con Carlos (Planificador)...")
            continue
        elif entrada.lower() == "/presupuesto":
            agente_forzado = "agente-presupuesto"
            print("OK Conectando con María (Presupuestos)...")
            continue
        elif entrada.lower() == "/auto":
            agente_forzado = None
            print("OK Modo automático — el sistema elige el agente más adecuado")
            continue
        
        # Clasificar y enviar
        agente = agente_forzado or clasificar_consulta(entrada)
        nombres = {
            "consultor-turismo": "Ana",
            "agente-itinerario": "Carlos",
            "agente-presupuesto": "María"
        }
        
        print(f"\n{nombres.get(agente, agente)}: ", end="", flush=True)
        respuesta = consultar_agente(agente, entrada, historial)
        print(respuesta)
        print()


if __name__ == "__main__":
    main()
```

```bash
# Iniciar el chat de la agencia
python tourism_chat.py
```

```bash
# Ejemplo de sesión
╔══════════════════════════════════════════════════════════╗
║       AGENCIA DE TURISMO VIRTUAL — JETSON AI             ║
╠══════════════════════════════════════════════════════════╣
...

Usted: Quiero visitar Japón en primavera. ¿Cuándo es la mejor época?

Ana: La primavera en Japón es una época espectacular para visitar el país.
La temporada de cerezos en flor (sakura) ocurre generalmente entre finales
de marzo y mediados de abril, comenzando en el sur de Kioto y avanzando hacia
el norte hasta Tokio. Para maximizar la experiencia, le recomendaría planificar
su viaje para el período del 25 de marzo al 15 de abril...

Usted: ¿Puedes hacer un itinerario de 7 días en Tokio y Kioto?

Carlos: Aquí tiene un itinerario de 7 días para Tokio y Kioto durante la
temporada de sakura:

**Días 1-3: Tokio**
Día 1: Llegada y Shinjuku
  - Mañana: Ajuste del jet lag, paseo por Shinjuku Gyoen para ver los cerezos
  - Tarde: Shibuya Crossing, Harajuku, Meiji Shrine
  ...
```

---

## 21.5 Modo Canal Externo (Telegram / WhatsApp via NemoClaw Gateway)

Si tiene NemoClaw configurado con un gateway de mensajería (Capítulo 13), puede conectar la agencia de turismo directamente. El canal primario recomendado es **Telegram** (bot via NemoClaw); WhatsApp requiere Business API y es opcional:

```python
# telegram_bridge.py — webhook para NemoClaw + Telegram
"""
Conecta NemoClaw Telegram gateway con los agentes de turismo.
Requiere NemoClaw configurado (ver Capítulo 13).
"""
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
OPENCLAW_URL = "http://localhost:18789"

# Historial de conversaciones por número de teléfono
historiales = {}

def clasificar_consulta(texto: str) -> str:
    """Igual que en tourism_chat.py."""
    # (mismo código de clasificación)
    return "consultor-turismo"  # simplificado aquí


@app.route("/webhook/turismo", methods=["POST"])
def webhook_turismo():
    """Recibe mensajes de NemoClaw y responde via los agentes de turismo."""
    data = request.json
    
    numero = data.get("from", "unknown")
    mensaje = data.get("text", "")
    
    if not mensaje:
        return jsonify({"status": "ignored"})
    
    # Mantener historial por número
    if numero not in historiales:
        historiales[numero] = []
    
    historial = historiales[numero]
    agente = clasificar_consulta(mensaje)
    
    historial.append({"role": "user", "content": mensaje})
    
    resp = requests.post(
        f"{OPENCLAW_URL}/api/chat",
        json={"agent": agente, "messages": historial[-6:], "stream": False},
        timeout=120
    )
    
    if resp.status_code == 200:
        respuesta = resp.json().get("message", {}).get("content", "")
        historial.append({"role": "assistant", "content": respuesta})
        
        # Limitar historial a 20 mensajes
        historiales[numero] = historial[-20:]
        
        return jsonify({"reply": respuesta})
    
    return jsonify({"reply": "Lo siento, estoy experimentando dificultades técnicas. Intente en un momento."})


if __name__ == "__main__":
    print("[OK] Webhook de Agencia de Turismo activo en puerto 5005")
    app.run(host="0.0.0.0", port=5005)
```

```bash
pip install flask
python telegram_bridge.py &
```

---

## 21.6 Limpieza Post-Pipeline

```bash
# Detener servidores del pipeline
pkill -f "tourism_chat.py" 2>/dev/null || true
pkill -f "telegram_bridge.py" 2>/dev/null || true

# OpenClaw puede continuar activo para otros pipelines
# Si desea detenerlo:
# sudo systemctl stop openclaw 2>/dev/null || docker stop openclaw 2>/dev/null

pwr-15w
sync && echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
echo "[OK] Pipeline de agencia de turismo detenido"
```

---

## 21.7 Verificación Final

```bash
echo "╔═══════════════════════════════════════════════════════╗"
echo "║    VERIFICACIÓN CAPÍTULO 21 — AGENCIA DE TURISMO     ║"
echo "╚═══════════════════════════════════════════════════════╝"

echo ""
echo "── OpenClaw ──"
curl -sf http://localhost:18789/api/health > /dev/null \
  && echo "  [OK] OpenClaw activo en puerto 18789" \
  || echo "  ○  OpenClaw offline — ver Capítulo 13"

echo ""
echo "── Ollama ──"
curl -sf http://localhost:11434/api/version > /dev/null \
  && echo "  [OK] Ollama activo" || echo "  ○  Ollama offline"
ollama list 2>/dev/null | grep -q "qwen3:7b" \
  && echo "  [OK] qwen3:7b disponible" \
  || echo "  ○  qwen3:7b no instalado (ollama pull qwen3:7b)"

echo ""
echo "── Agentes configurados ──"
curl -sf http://localhost:18789/api/agents 2>/dev/null \
  | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    agents = [a['name'] for a in data] if isinstance(data, list) else []
    for a in ['consultor-turismo', 'agente-itinerario', 'agente-presupuesto']:
        print(f'  {\"[OK]\" if a in agents else \"○ \"} {a}')
except: print('  [WARN]  No se pudo obtener lista de agentes')
" || echo "  ○  Ejecute setup_agents.py primero"

echo ""
echo "═════════════════════════════════════════════════════════"
```

---

## 21.8 Escalabilidad y Extensiones

### 21.8.1 Bot de Telegram para la Agencia de Turismo

La agencia multi-agente puede integrarse con Telegram para atender consultas de viajeros directamente desde la mensajería. El usuario escribe su destino y preferencias; el Jetson responde con el itinerario completo.

**Flujo con N8N** (ver Capítulo 14):

```yaml
Nodo 1 — Telegram Trigger:
  tipo: telegram_trigger
  evento: message_received
  filtro: texto (consulta de viaje)

Nodo 2 — Execute Command:
  tipo: execute_command
  comando: |
    python3 ~/projects/tourism-agency/main.py \
      --query "{{message_text}}" \
      --output-format markdown
  timeout: 120

Nodo 3 — Send Message:
  tipo: telegram_send_message
  chat_id: {{chat_id}}
  texto: "{{output}}"
  parse_mode: Markdown
```

**Flujo con OpenClaw** (ver Capítulo 11A):

```json
"agents": {
  "turismo": {
    "description": "Agencia de turismo IA — itinerarios personalizados",
    "command": "python3 ~/projects/tourism-agency/main.py --query {{input}}",
    "channels": ["telegram"]
  }
}
```

### 21.8.2 Modo Mixto con OpenRouter

Para destinos exóticos o cuando el modelo local no tenga suficiente conocimiento geográfico actualizado, integre OpenRouter como backend alternativo:

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

```bash
# Aliases en ~/.bash_aliases (ver Capítulo 6)
alias turismo-local="USE_LOCAL_LLM=true  python3 ~/projects/tourism-agency/main.py"
alias turismo-cloud="USE_LOCAL_LLM=false python3 ~/projects/tourism-agency/main.py"
```

### 21.8.3 Evaluación de Backend de Inferencia

Para una agencia multi-agente con múltiples llamadas secuenciales al LLM por cada consulta:

| Backend | Ventaja | Desventaja | Recomendación |
|---|---|---|---|
| **Ollama** (qwen3:7b) | Simplicidad, API compatible | Mayor overhead por llamada | Ideal para 1 usuario |
| **llama.cpp** (qwen3:7b Q4_K_M) | Menor latencia por token | Requiere gestión manual | Buena opción para reducir tiempo de respuesta |
| **vLLM** | Throughput alto, batching | Startup lento, >4 GB VRAM | Solo si atiende múltiples usuarios concurrentes |

> **RECOMENDACIÓN:** Para uso personal o con pocos usuarios simultáneos, Ollama es suficiente. Si el bot de Telegram atiende más de 5 usuarios a la vez, cambie a vLLM para aprovechar el batching continuo y evitar colas de espera.

---

> **Próximo paso:** El Capítulo 22 construye el pipeline de automatización de embudo de ventas, usando la API oficial de Meta para publicar en Facebook e Instagram.
