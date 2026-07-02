# Capítulo 11D — Tool Calling: Herramientas Personalizadas para los Modelos del Jetson

## Introducción

El tool calling (llamada a funciones) es la capacidad del modelo para solicitar la ejecución de una herramienta externa durante la generación de una respuesta. En lugar de inventar información, el modelo dice "necesito ejecutar esta función con estos parámetros" — el código cliente ejecuta la función y devuelve el resultado al modelo para que construya la respuesta final.

Esta parte cubre la implementación práctica de tool calling en el Jetson AGX Orin con los modelos del Top 10: Qwen3.5 35B-A3B, Gemma 4 26B-A4B y GPT OSS 20B. Incluye ejemplos completos en Python y un cliente C++ mediante la API REST de llama.cpp.

**Modo energético:** MAXN para modelos ≥14B con tool calling. 30W es suficiente para modelos ≤9B.

> **Prerrequisito:** Un motor de inferencia activo con un modelo que soporte tool calling (ver tabla §13D.1.1).

---

## 13D.1 Fundamentos del Tool Calling

### 13D.1.1 Modelos con Soporte de Tool Calling en el Jetson

| Modelo | Motor | Parser | Puerto | Notas |
|--------|-------|--------|--------|-------|
| Qwen3.5 35B-A3B | vLLM | `qwen3_coder` | 8000 | Tool calling + razonamiento activable |
| Qwen3.5 9B | vLLM | `qwen3_coder` | 8000 | Velocidad ~55 tok/s |
| Qwen3.5 4B | vLLM | `qwen3_coder` | 8000 | El más liviano con tool calling |
| Gemma 4 26B-A4B | vLLM | `gemma4` | 8000 | Tool calling + visión |
| Gemma 4 E4B | vLLM | `gemma4` | 8000 | Multimodal compacto |
| GPT OSS 20B | vLLM | (nativo OpenAI) | 8000 | Compatible drop-in con SDK OpenAI |

> **NOTA:** Los modelos Nemotron y Cosmos Reason 2 no tienen soporte de tool calling documentado en la versión GGUF para llama.cpp. Para tool calling en llama.cpp, los modelos que sí lo soportan en formato GGUF son Gemma 4 E4B y Qwen3.5 4B con sus respectivos templates de Jinja.

### 13D.1.2 Formatos de Tool Calling

Existen dos formatos principales que los modelos del Jetson usan:

**Formato OpenAI (estándar — soportado por todos los modelos en vLLM):**

```json
{
  "model": "qwen35",
  "messages": [{"role": "user", "content": "¿Cuánto es 2+2?"}],
  "tools": [{
    "type": "function",
    "function": {
      "name": "calcular",
      "description": "Calcula una expresión matemática",
      "parameters": {
        "type": "object",
        "properties": {
          "expresion": {"type": "string", "description": "Expresión matemática"}
        },
        "required": ["expresion"]
      }
    }
  }],
  "tool_choice": "auto"
}
```

**Formato Hermes (usado internamente por Qwen3.5 y algunos modelos GGUF):**

El modelo genera una etiqueta especial con el JSON de la herramienta:

```
<tool_call>
{"name": "calcular", "arguments": {"expresion": "2+2"}}
</tool_call>
```

Con vLLM y el parser `qwen3_coder`, este formato se traduce automáticamente al formato OpenAI. El cliente recibe siempre el formato estándar OpenAI, independientemente del formato interno del modelo.

---

## 13D.2 Iniciar el Modelo con Soporte de Tool Calling

```bash
# Iniciar Qwen3.5 35B-A3B con tool calling habilitado
pwr-maxn
docker run --runtime nvidia -d \
  --name qwen35-35b \
  --restart no \
  --network host \
  --ipc host \
  --shm-size 8g \
  -e NVIDIA_VISIBLE_DEVICES=all \
  ghcr.io/nvidia-ai-iot/vllm:latest-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve Kbenkhaled/Qwen3.5-35B-A3B-quantized.w4a16 \
      --gpu-memory-utilization 0.70 \
      --enable-prefix-caching \
      --enable-auto-tool-choice \
      --tool-call-parser qwen3_coder \
      --served-model-name qwen35 \
      --max-model-len 8192 \
      --host 0.0.0.0 \
      --port 8000"

echo -n "Esperando qwen35"
until curl -sf http://localhost:8000/v1/models > /dev/null; do echo -n "."; sleep 30; done
echo " [OK]"
```

```bash
# Iniciar Gemma 4 26B-A4B con tool calling nativo gemma4
pwr-maxn
docker run --runtime nvidia -d \
  --name gemma4-26b-vllm \
  --restart no \
  --network host \
  --ipc host \
  --shm-size 8g \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin \
  bash -c "cd /opt && source venv/bin/activate && \
    vllm serve cyankiwi/gemma-4-26B-A4B-it-AWQ-4bit \
      --gpu-memory-utilization 0.75 \
      --enable-auto-tool-choice \
      --tool-call-parser gemma4 \
      --host 0.0.0.0 \
      --port 8000"

until curl -sf http://localhost:8000/v1/models > /dev/null; do echo -n "."; sleep 30; done
echo " [OK]"
```

---

## 13D.3 Ejemplos en Python

### 13D.3.1 Herramienta de Consulta del Sistema Jetson

```python
#!/usr/bin/env python3
"""
jetson_tool_agent.py — Agente con herramientas del sistema Jetson
Uso: source ~/venvs/llm/bin/activate && python3 ~/scripts/jetson_tool_agent.py
"""
import json, subprocess
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="not-needed")
MODEL = "qwen35"  # served-model-name configurado en vLLM

# ── Implementación de herramientas ──────────────────────────────────────────

def obtener_temperatura() -> dict:
    """Lee temperatura de la GPU del Jetson via tegrastats."""
    try:
        output = subprocess.run(
            ["tegrastats", "--interval", "500"],
            capture_output=True, text=True, timeout=2
        ).stdout.split("\n")[0]
        # Formato: ... GPU@45.5C ...
        import re
        temp = re.search(r'GPU@(\d+\.\d+)C', output)
        return {"temperatura_gpu_celsius": float(temp.group(1)) if temp else 0.0,
                "raw": output[:200]}
    except Exception as e:
        return {"error": str(e)}

def obtener_memoria_libre() -> dict:
    """Retorna la memoria RAM libre del sistema."""
    try:
        output = subprocess.run(["free", "-h"], capture_output=True, text=True).stdout
        lines = output.strip().split("\n")
        mem_line = [l for l in lines if l.startswith("Mem:")][0].split()
        return {
            "total": mem_line[1],
            "usada": mem_line[2],
            "libre": mem_line[3],
            "disponible": mem_line[6]
        }
    except Exception as e:
        return {"error": str(e)}

def obtener_modo_energia() -> dict:
    """Consulta el modo de energía activo (nvpmodel)."""
    try:
        output = subprocess.run(
            ["sudo", "nvpmodel", "--query"],
            capture_output=True, text=True
        ).stdout
        import re
        modo = re.search(r'Power Model:\s*(.*)', output)
        return {"modo_activo": modo.group(1).strip() if modo else "desconocido",
                "raw": output.strip()}
    except Exception as e:
        return {"error": str(e)}

def cambiar_modo_energia(modo: str) -> dict:
    """Cambia el modo de energía. Valores: maxn, 30w, 15w."""
    modos = {"maxn": "0", "30w": "2", "15w": "3"}
    if modo.lower() not in modos:
        return {"error": f"Modo desconocido: {modo}. Use: maxn, 30w, 15w"}
    cmd_id = modos[modo.lower()]
    try:
        subprocess.run(["sudo", "nvpmodel", "-m", cmd_id], check=True)
        subprocess.run(["sudo", "jetson_clocks"], check=True)
        return {"ok": True, "modo_configurado": modo.upper()}
    except subprocess.CalledProcessError as e:
        return {"error": f"nvpmodel falló: {e}"}

# ── Mapa de funciones disponibles ───────────────────────────────────────────
TOOL_MAP = {
    "obtener_temperatura": obtener_temperatura,
    "obtener_memoria_libre": obtener_memoria_libre,
    "obtener_modo_energia": obtener_modo_energia,
    "cambiar_modo_energia": lambda **kwargs: cambiar_modo_energia(**kwargs),
}

# ── Definición de herramientas (formato OpenAI) ─────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "obtener_temperatura",
            "description": "Obtiene la temperatura actual de la GPU del Jetson AGX Orin",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_memoria_libre",
            "description": "Obtiene la cantidad de memoria RAM libre y total del sistema",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_modo_energia",
            "description": "Consulta el modo de energía activo en el Jetson (nvpmodel)",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cambiar_modo_energia",
            "description": "Cambia el modo de energía del Jetson. maxn=50W máximo rendimiento, 30w=30W equilibrado, 15w=15W ahorro",
            "parameters": {
                "type": "object",
                "properties": {
                    "modo": {
                        "type": "string",
                        "enum": ["maxn", "30w", "15w"],
                        "description": "Modo de energía a configurar"
                    }
                },
                "required": ["modo"]
            }
        }
    }
]

# ── Bucle de conversación con tool calling ───────────────────────────────────

def ejecutar_herramienta(nombre: str, args: dict) -> str:
    if nombre not in TOOL_MAP:
        return json.dumps({"error": f"Herramienta desconocida: {nombre}"})
    try:
        resultado = TOOL_MAP[nombre](**args)
        return json.dumps(resultado, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

def chat_con_herramientas(pregunta: str) -> str:
    messages = [
        {"role": "system", "content": "Eres un asistente técnico del Jetson AGX Orin. Usa las herramientas disponibles para responder preguntas sobre el sistema."},
        {"role": "user", "content": pregunta}
    ]

    print(f"\n Usuario: {pregunta}")

    while True:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=500
        )

        msg = resp.choices[0].message
        finish = resp.choices[0].finish_reason

        messages.append({"role": "assistant", "content": msg.content, "tool_calls": msg.tool_calls})

        if finish == "tool_calls" and msg.tool_calls:
            for tc in msg.tool_calls:
                nombre = tc.function.name
                args = json.loads(tc.function.arguments)
                print(f"\n Herramienta: {nombre}({args})")
                resultado = ejecutar_herramienta(nombre, args)
                print(f" Resultado: {resultado[:200]}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": resultado
                })
        else:
            respuesta = msg.content or ""
            print(f"\n Asistente: {respuesta}")
            return respuesta

# ── Punto de entrada ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Ejemplos de preguntas que el agente puede responder usando herramientas:
    preguntas = [
        "¿Cuál es la temperatura actual de la GPU del Jetson?",
        "¿Cuánta memoria RAM tengo disponible?",
        "¿En qué modo de energía estoy y por qué debería cambiarlo si quiero ejecutar un modelo grande?",
        "Cambia el modo de energía a MAXN para que pueda cargar un modelo de 35B parámetros.",
    ]

    for pregunta in preguntas:
        chat_con_herramientas(pregunta)
        print("\n" + "─"*60)
```

```bash
# Guardar el script y ejecutar
cat > ~/scripts/jetson_tool_agent.py << 'EOF'
# (contenido del bloque Python anterior)
EOF

source ~/venvs/llm/bin/activate
python3 ~/scripts/jetson_tool_agent.py
```

```
# Salida esperada (extracto):
 Usuario: ¿Cuál es la temperatura actual de la GPU del Jetson?
 Herramienta: obtener_temperatura({})
 Resultado: {"temperatura_gpu_celsius": 45.5, "raw": "...GPU@45.5C..."}
 Asistente: La temperatura actual de la GPU del Jetson es de 45.5°C, lo que está dentro del rango normal de operación.
```

---

### 13D.3.2 Agente de Búsqueda Web + Respuesta

```python
#!/usr/bin/env python3
"""
web_search_agent.py — Agente que busca en la web y responde con fuentes
"""
import json, urllib.request, urllib.parse
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="not-needed")
MODEL = "qwen35"

BRAVE_API_KEY = "TU_BRAVE_API_KEY"  # Obtener en brave.com/search/api/

def buscar_web(consulta: str, num_resultados: int = 5) -> dict:
    """Busca en la web usando la API de Brave Search."""
    if not BRAVE_API_KEY or BRAVE_API_KEY == "TU_BRAVE_API_KEY":
        # Simulación si no hay API key
        return {
            "resultados": [
                {"titulo": f"Resultado simulado para: {consulta}",
                 "url": "https://example.com",
                 "descripcion": "Esta es una búsqueda simulada — configure BRAVE_API_KEY para búsquedas reales."}
            ]
        }
    try:
        url = f"https://api.search.brave.com/res/v1/web/search?q={urllib.parse.quote(consulta)}&count={num_resultados}"
        req = urllib.request.Request(url, headers={"Accept": "application/json", "X-Subscription-Token": BRAVE_API_KEY})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        resultados = data.get("web", {}).get("results", [])
        return {
            "resultados": [
                {"titulo": r.get("title"), "url": r.get("url"), "descripcion": r.get("description")}
                for r in resultados[:num_resultados]
            ]
        }
    except Exception as e:
        return {"error": str(e)}

TOOLS_WEB = [{
    "type": "function",
    "function": {
        "name": "buscar_web",
        "description": "Busca información actualizada en internet usando Brave Search",
        "parameters": {
            "type": "object",
            "properties": {
                "consulta": {"type": "string", "description": "Términos de búsqueda"},
                "num_resultados": {"type": "integer", "description": "Número de resultados (1-10)", "default": 5}
            },
            "required": ["consulta"]
        }
    }
}]

def buscar_y_responder(pregunta: str) -> str:
    messages = [
        {"role": "system", "content": "Eres un asistente que busca información actualizada en internet y responde con fuentes. Usa la herramienta buscar_web para obtener información antes de responder."},
        {"role": "user", "content": pregunta}
    ]

    while True:
        resp = client.chat.completions.create(
            model=MODEL, messages=messages,
            tools=TOOLS_WEB, tool_choice="auto", max_tokens=1000
        )
        msg = resp.choices[0].message
        finish = resp.choices[0].finish_reason
        messages.append({"role": "assistant", "content": msg.content, "tool_calls": msg.tool_calls})

        if finish == "tool_calls" and msg.tool_calls:
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
                resultado = buscar_web(**args)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(resultado, ensure_ascii=False)})
        else:
            return msg.content or ""

# Ejemplo de uso
print(buscar_y_responder("¿Cuáles son las novedades más recientes de JetPack 7.2 para Jetson?"))
```

---

### 13D.3.3 Tool Calling con Gemma 4 (Parser gemma4)

```python
#!/usr/bin/env python3
"""
gemma4_tools.py — Tool calling con Gemma 4 usando parser gemma4
La diferencia principal: usar --tool-call-parser gemma4 en vLLM y 
el modelo sirviendo en ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin
"""
import json
from openai import OpenAI

# Asegúrese de tener gemma4-26b-vllm corriendo en :8000
client = OpenAI(base_url="http://localhost:8000/v1", api_key="not-needed")

# Obtener el model ID dinámicamente
models_resp = client.models.list()
MODEL = models_resp.data[0].id  # auto-detectar el modelo activo
print(f"Modelo activo: {MODEL}")

TOOLS_GEMMA = [{
    "type": "function",
    "function": {
        "name": "analizar_imagen",
        "description": "Analiza el contenido de una imagen y extrae información específica",
        "parameters": {
            "type": "object",
            "properties": {
                "url_imagen": {"type": "string", "description": "URL pública de la imagen a analizar"},
                "tarea": {"type": "string", "description": "Qué analizar: 'texto', 'objetos', 'escena', 'anomalias'"}
            },
            "required": ["url_imagen", "tarea"]
        }
    }
}]

def analizar_imagen(url_imagen: str, tarea: str) -> dict:
    """Herramienta que usa el propio modelo de visión para analizar la imagen."""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": url_imagen}},
            {"type": "text", "text": f"Analiza esta imagen. Tarea específica: {tarea}. Responde en JSON con campos: 'resultado', 'confianza', 'detalles'."}
        ]}],
        max_tokens=500
    )
    try:
        return json.loads(resp.choices[0].message.content)
    except json.JSONDecodeError:
        return {"resultado": resp.choices[0].message.content, "confianza": "N/A"}

# Ejecutar agente con tool calling + visión
pregunta = "Analiza esta imagen de Cartagena: https://upload.wikimedia.org/wikipedia/commons/thumb/9/97/Cartagena_de_Indias.jpg/800px-Cartagena_de_Indias.jpg ¿Qué tipo de escena es y qué elementos turísticos se pueden ver?"

messages = [
    {"role": "system", "content": "Eres un guía turístico experto en Colombia. Usa la herramienta analizar_imagen para inspeccionar imágenes antes de responder."},
    {"role": "user", "content": pregunta}
]

while True:
    resp = client.chat.completions.create(
        model=MODEL, messages=messages,
        tools=TOOLS_GEMMA, tool_choice="auto", max_tokens=600
    )
    msg = resp.choices[0].message
    messages.append({"role": "assistant", "content": msg.content, "tool_calls": msg.tool_calls})

    if resp.choices[0].finish_reason == "tool_calls" and msg.tool_calls:
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            resultado = analizar_imagen(**args)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(resultado)})
    else:
        print(msg.content)
        break
```

---

## 13D.4 Cliente C++ via API REST de llama.cpp

Para proyectos de robótica o sistemas embebidos donde Python no es una opción, llama.cpp expone la misma API OpenAI en el puerto 8080. El siguiente ejemplo usa la biblioteca `libcurl` para hacer tool calling desde C++:

```cpp
// jetson_tool_client.cpp
// Compilar: g++ -o jetson_tool_client jetson_tool_client.cpp -lcurl -ljson11
// Instalar dependencias: sudo apt install libcurl4-openssl-dev libjson11-dev

#include <curl/curl.h>
#include <iostream>
#include <string>
#include <sstream>
#include <functional>

// Callback para acumular la respuesta HTTP
static size_t WriteCallback(void* contents, size_t size, size_t nmemb, std::string* out) {
    out->append((char*)contents, size * nmemb);
    return size * nmemb;
}

std::string http_post(const std::string& url, const std::string& body) {
    CURL* curl = curl_easy_init();
    std::string response;
    if (curl) {
        struct curl_slist* headers = nullptr;
        headers = curl_slist_append(headers, "Content-Type: application/json");
        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, body.c_str());
        curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
        curl_easy_setopt(curl, CURLOPT_TIMEOUT, 120L);
        curl_easy_perform(curl);
        curl_slist_free_all(headers);
        curl_easy_cleanup(curl);
    }
    return response;
}

int main() {
    // Herramienta: leer temperatura de tegrastats
    // En un proyecto real, esta función leería /sys/devices/virtual/thermal/thermal_zone*/temp
    auto get_temperature = []() -> std::string {
        FILE* pipe = popen("tegrastats --interval 500 2>/dev/null | head -1", "r");
        if (!pipe) return "\"error\"";
        char buffer[512];
        std::string result;
        while (fgets(buffer, sizeof(buffer), pipe) != nullptr)
            result += buffer;
        pclose(pipe);
        // Extraer temperatura GPU del output
        size_t pos = result.find("GPU@");
        if (pos != std::string::npos) {
            std::string temp = result.substr(pos + 4, 5);
            return "{\"temperatura_gpu_celsius\": " + temp.substr(0, temp.find('C')) + "}";
        }
        return "{\"temperatura_gpu_celsius\": 0}";
    };

    // Petición con tool calling a llama.cpp (compatible OpenAI)
    std::string request_body = R"({
        "model": "nemotron3-4b",
        "messages": [
            {"role": "system", "content": "Eres un monitor del sistema Jetson AGX Orin."},
            {"role": "user", "content": "¿Cuál es la temperatura actual de la GPU?"}
        ],
        "tools": [{
            "type": "function",
            "function": {
                "name": "get_temperature",
                "description": "Obtiene la temperatura de la GPU del Jetson",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        }],
        "tool_choice": "auto",
        "max_tokens": 200
    })";

    std::string response = http_post("http://localhost:8080/v1/chat/completions", request_body);
    std::cout << "Respuesta del modelo:\n" << response << std::endl;

    // En un cliente completo se parsearia el JSON de respuesta,
    // se detectaria finish_reason == "tool_calls",
    // se ejecutaria get_temperature() y se enviaria el resultado de vuelta.
    // Este ejemplo muestra la estructura de la primera petición.

    return 0;
}
```

```bash
# Compilar el cliente C++ (asegúrese de tener llama.cpp corriendo en :8080)
sudo apt install -y libcurl4-openssl-dev

g++ -O2 -o ~/scripts/jetson_tool_client ~/scripts/jetson_tool_client.cpp -lcurl
chmod +x ~/scripts/jetson_tool_client

# Ejecutar (con Nemotron3 Nano 4B activo en :8080)
~/scripts/jetson_tool_client
```

---

## 13D.5 Patrones de Error y Soluciones

### Respuesta vacía o `content: null` al usar tool calling

**Causa más común:** `--reasoning-parser` activado en el servidor vLLM. Cuando el reasoning parser está activo, las respuestas de texto van al campo `reasoning_content`, no a `content`, lo que parece un `content: null`.

```bash
# Verificar que --reasoning-parser NO está activo en el comando docker
docker inspect qwen35-35b | python3 -c \
  "import sys,json; cmd=' '.join(json.load(sys.stdin)[0]['Config']['Cmd']); print('reasoning-parser' in cmd)"
# Esperado: False
```

### El modelo no invoca la herramienta (`finish_reason: stop` en lugar de `tool_calls`)

```python
# Forzar el uso de una herramienta específica (en lugar de "auto"):
resp = client.chat.completions.create(
    model=MODEL,
    messages=messages,
    tools=TOOLS,
    tool_choice={"type": "function", "function": {"name": "nombre_herramienta"}},  # forzar
    max_tokens=500
)
```

### Argumentos de herramienta en formato incorrecto (JSON inválido)

```python
# Siempre usar try/except al parsear argumentos de herramienta:
try:
    args = json.loads(tc.function.arguments)
except json.JSONDecodeError as e:
    print(f"Error en argumentos de {tc.function.name}: {e}")
    args = {}
```

### Tool calling funciona con curl pero no con el SDK de Python

```python
# El SDK de OpenAI v1.x requiere que tool_calls se envíe como objeto, no como None
# Al construir el mensaje de assistant para la segunda vuelta:
messages.append({
    "role": "assistant",
    "content": msg.content,                           # puede ser None
    "tool_calls": msg.tool_calls if msg.tool_calls else None  # no omitir
})
```

---

## 13D.6 Script de Prueba Rápida de Tool Calling

```bash
# Prueba rápida de tool calling via curl
# Requiere modelo con tool calling activo en :8000

# Definir una herramienta simple
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen35",
    "messages": [{"role": "user", "content": "¿Cuál es el clima en Medellín?"}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "obtener_clima",
        "description": "Obtiene el clima de una ciudad",
        "parameters": {
          "type": "object",
          "properties": {
            "ciudad": {"type": "string"},
            "pais": {"type": "string"}
          },
          "required": ["ciudad"]
        }
      }
    }],
    "tool_choice": "auto",
    "max_tokens": 200
  }' | python3 -c "
import sys, json
resp = json.load(sys.stdin)
msg = resp['choices'][0]['message']
finish = resp['choices'][0]['finish_reason']
print('finish_reason:', finish)
if msg.get('tool_calls'):
    tc = msg['tool_calls'][0]
    print('Herramienta llamada:', tc['function']['name'])
    print('Argumentos:', tc['function']['arguments'])
else:
    print('Respuesta directa:', msg.get('content'))
"
```

```
# Salida esperada:
finish_reason: tool_calls
Herramienta llamada: obtener_clima
Argumentos: {"ciudad": "Medellín", "pais": "Colombia"}
```

---

## Resumen de el Capítulo 13D

El tool calling convierte los modelos del Jetson en agentes capaces de tomar acciones reales:

- **Formato OpenAI estándar** — funciona con todos los modelos en vLLM; el parser del modelo (`qwen3_coder` o `gemma4`) hace la traducción interna
- **`--reasoning-parser` OMITIDO** en vLLM — su presencia causa `content: null` en clientes estándar
- **`tool_choice: "auto"`** — deja al modelo decidir cuándo usar herramientas; use `tool_choice: forced` para forzar una herramienta específica
- **Siempre incluir `tool_calls` en el mensaje de assistant** al construir el historial de conversación para la segunda vuelta
- **llama.cpp también soporta tool calling** via la misma API OpenAI en :8080, accesible desde Python y C++

Con estas herramientas, el Jetson AGX Orin puede operar como un agente autónomo que monitorea el sistema, ejecuta acciones de hardware y responde en tiempo real a solicitudes de WhatsApp, navegador o código propio.
