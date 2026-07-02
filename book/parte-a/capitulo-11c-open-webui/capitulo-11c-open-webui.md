# Capítulo 11C — Open WebUI: Interfaz Gráfica para Todos los Motores del Jetson

## Introducción

Open WebUI proporciona una interfaz web estilo ChatGPT que conecta simultáneamente con Ollama, vLLM y llama.cpp desde cualquier navegador de la red local. Funciona como **PWA** en móviles y soporta subida de documentos, **RAG**, pipelines Python y entrada de voz.

> **NOTA — Glosario de conceptos de este capítulo:**
>
> - **PWA (Progressive Web App):** Aplicación web que puede instalarse en el teléfono como si fuera una app nativa. No se descarga desde la tienda de apps — se instala directamente desde el navegador. Funciona sin internet cuando el Jetson está en la misma red local.
>
> - **RAG (Retrieval-Augmented Generation):** Técnica que permite al modelo de lenguaje consultar documentos propios como contexto antes de generar su respuesta. En lugar de depender únicamente de su conocimiento de entrenamiento, el modelo puede "leer" archivos PDF, DOCX o TXT que usted suba.
>
> - **Embeddings:** Representaciones numéricas del texto (vectores de alta dimensión) que permiten búsqueda por similitud semántica. Son fundamentales para el RAG: el texto del documento se convierte en embeddings y se busca cuáles son más similares a la pregunta del usuario.
>
> - **Certificado SSL / TLS:** El mecanismo criptográfico que convierte HTTP en HTTPS. Garantiza que la comunicación entre el navegador y el servidor está cifrada. Los navegadores modernos bloquean el acceso al micrófono en conexiones HTTP sin certificado.
>
> - **CA local (Certificate Authority local):** Entidad que firma certificados TLS en la red local, sin necesidad de un dominio público ni de pagar a una CA externa. `mkcert` (sección 13C.11) crea una CA local en el Jetson cuyo certificado raíz puede instalarse en Windows para que el navegador confíe en él.

Este capítulo cubre dos partes: la **configuración con SSL local** (necesaria para habilitar el micrófono en el navegador) y un **proyecto práctico de aprendizaje de inglés** usando el modelo multimodal Nemotron Omni.

A diferencia de los motores de inferencia, Open WebUI **no carga modelos en GPU** — consume únicamente ~200–400 MB de RAM. Sin embargo, para mantener la arquitectura clean-start, se usa `--restart no` como todos los servicios on-demand.

**Modo energético:** 30W en reposo. Cambie a MAXN solo cuando el motor de inferencia lo requiera.

> **Prerrequisito:** Docker activo (`docker-on`) y al menos un motor de inferencia corriendo del Capítulo anterior. El bot de Telegram del Capítulo 13A es independiente de Open WebUI.

---

## 13C.1 Instalación

### 13C.1.1 Primer Arranque

```bash
# Activar Docker si esta desactivado
docker-on

# Descargar e iniciar Open WebUI
# Puerto 3000 (evita conflicto con llama.cpp en :8080 y vLLM en :8000)
# --restart no = clean-start: no arranca automaticamente tras reinicios
docker run -d \
  --name open-webui \
  --restart no \
  --network host \
  -v open-webui-data:/app/backend/data \
  -e OLLAMA_BASE_URL=http://localhost:11434 \
  ghcr.io/open-webui/open-webui:main
```

```bash
# Esperar a que arranque (30-60 segundos la primera vez)
docker logs open-webui --follow
# Esperar la línea: "Application startup complete."
# Presionar Ctrl+C para salir de los logs (el contenedor sigue corriendo)
```

```bash
# Verificar que está activo
curl -s http://localhost:3000 | grep -o '<title>[^<]*</title>'
# Salida esperada: <title>Open WebUI</title>
```

Abra desde el navegador en cualquier equipo de la red local:

```
http://192.168.1.100:3000
```

En la primera visita, Open WebUI solicita crear una cuenta de administrador local (sin conexión a internet).

> **ADVERTENCIA — Conflicto de puertos:** El puerto interno de Open WebUI es 8080, pero llama.cpp también usa 8080. Con `--network host` se expone el puerto interno directamente. Por eso este libro usa la configuración de red host **sin mapeo de puertos**, y Open WebUI escucha en el puerto 3000 mediante configuración interna. Si necesita ajustar el puerto, use `-e PORT=3000 -p 3000:3000`.

### 13C.1.2 Habilitar UFW para acceso desde red local

```bash
# Permitir acceso al puerto 3000 desde la red local
sudo ufw allow 3000/tcp comment "Open WebUI"
sudo ufw status | grep 3000
```

---

## 13C.2 Conectar Múltiples Backends de Inferencia

Open WebUI puede conectarse simultáneamente a Ollama y a cualquier endpoint compatible con la API de OpenAI (vLLM, llama.cpp):

```bash
# Configuración multi-backend
# IMPORTANTE: stop sin rm — el contenedor retiene el volumen de datos y usuarios
docker stop open-webui

docker run -d \
  --name open-webui \
  --restart no \
  --network host \
  --add-host=host.docker.internal:host-gateway \
  -v open-webui:/app/backend/data \
  -e OLLAMA_BASE_URL=http://localhost:11434 \
  -e OPENAI_API_BASE_URLS="http://localhost:8000/v1;http://localhost:8080/v1" \
  -e OPENAI_API_KEYS="vllm-local;llama-local" \
  ghcr.io/open-webui/open-webui:main

docker logs open-webui --follow
```

```
# Salida esperada (extracto):
INFO:     Application startup complete.
```

Los modelos disponibles en cada motor aparecen automáticamente en el selector de modelos de la interfaz web.

> **NOTA — Coherencia de API Keys:** Los valores `vllm-local` y `llama-local` en `OPENAI_API_KEYS` deben coincidir exactamente con los argumentos `--api-key` usados al lanzar vLLM y llama.cpp en el Capítulo 12. Si en su `~/.bash_aliases` definió `VLLM_API_KEY` con un valor distinto de `vllm-local`, reemplace la línea correspondiente en el comando `docker run`:
> ```bash
> -e OPENAI_API_KEYS="${VLLM_API_KEY:-vllm-local};llama-local"
> ```
> Si no definió `VLLM_API_KEY`, el valor por defecto `vllm-local` es correcto y no necesita cambiar nada.

**Alternativa — configurar desde la interfaz gráfica:**
- Configuración (icono engranaje) → Connections → OpenAI API
- Agregar URL: `http://localhost:8000/v1` con API Key: `vllm-local`
- Agregar URL: `http://localhost:8080/v1` con API Key: `llama-local`

---

## 13C.3 Upload de Documentos y RAG

Open WebUI incluye soporte nativo para RAG (Retrieval-Augmented Generation): sube documentos PDF, DOCX o TXT y el agente los usa como contexto.

```bash
# Verificar que el procesador de documentos está activo
docker exec open-webui ls /app/backend/data/uploads/ 2>/dev/null \
  && echo "[OK] Directorio de uploads disponible" \
  || echo "[WARN]  Primera inicialización en curso"
```

**Desde la interfaz web:**
1. Abrir una conversación nueva
2. Icono de clip (adjuntar) → seleccionar PDF o DOCX
3. El documento se indexa automáticamente (~30 segundos por 100 páginas)
4. Hacer preguntas sobre el documento en la misma conversación

**Configurar el motor de embeddings:**

> **NOTA — El RAG requiere un modelo de embeddings:** Sin un modelo de embeddings activo, la indexación de documentos en Open WebUI falla silenciosamente — el documento se "sube" pero no se indexa y el modelo no puede consultarlo. **Instale `nomic-embed-text` antes de subir cualquier documento para RAG.**

- Configuración → Documents → Embedding Model
- Para Jetson: seleccionar `nomic-embed-text` (disponible via Ollama) — consume ~1 GB de RAM

```bash
# Paso 1: Asegurarse de que Ollama está activo
sudo systemctl start ollama || docker-on

# Paso 2: Instalar el modelo de embeddings
ollama pull nomic-embed-text
# Tarda ~2 minutos — modelo de 274 MB

# Verificar que quedó instalado
ollama list | grep nomic
# Salida esperada: nomic-embed-text    latest    ...    274 MB
```

> **CONSEJO:** El modelo `nomic-embed-text` es muy liviano (~274 MB) y compatible con el Jetson. Una vez instalado, Ollama lo mantiene disponible permanentemente sin necesidad de reinstalarlo. Si usó el troubleshooting del Capítulo 12 y ya lo instaló ahí, omita el paso anterior.

---

## 13C.4 Pipelines — Procesamiento Personalizado

Open WebUI soporta pipelines: interceptores Python que procesan la solicitud antes de enviarla al modelo. Útiles para: traducción automática, preprocesamiento de imágenes, filtrado de contenido, enrutamiento entre modelos.

```bash
# Crear un pipeline de traducción automática al español
mkdir -p ~/scripts/webui-pipelines

cat > ~/scripts/webui-pipelines/translate_to_spanish.py << 'EOF'
"""
Pipeline: Traduce la respuesta al español si la petición fue en inglés.
Guardar en el directorio de pipelines de Open WebUI y activar desde la interfaz.
"""
from typing import List, Union, Generator, Iterator

class Pipeline:
    def __init__(self):
        self.name = "Auto-translate to Spanish"
        self.type = "pipe"

    async def on_startup(self):
        print("Pipeline translate_to_spanish activado")

    async def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator, Iterator]:
        # Agregar instrucción al sistema para responder en español
        if "system" not in [m["role"] for m in messages]:
            messages.insert(0, {
                "role": "system",
                "content": "Responde siempre en español, independientemente del idioma de la pregunta."
            })
        yield f"Procesando con {model_id}...\n"
EOF

echo "Pipeline creado en ~/scripts/webui-pipelines/"
echo "Para activar: Settings → Pipelines → Upload pipeline file"
```

---

## 13C.5 Uso como PWA en Dispositivos Móviles

Open WebUI funciona como Progressive Web App — puede instalarse en el teléfono como una app nativa:

> **NOTA — SSL requerido para el micrófono en PWA:** La instalación de la app PWA funciona con HTTP simple (`http://...`). Sin embargo, si desea usar la **entrada de voz** (micrófono) desde el teléfono, el navegador móvil exige HTTPS. En ese caso, configure primero el certificado SSL con `mkcert` (sección 13C.11) y acceda vía `https://192.168.1.100:3000`. Sin SSL, el ícono del micrófono en la interfaz simplemente no aparecerá en dispositivos móviles.

**Android (Chrome):**
1. Abrir `http://192.168.1.100:3000` en Chrome del teléfono (o `https://` si ya configuró SSL)
2. Menú (3 puntos) → "Añadir a pantalla de inicio"
3. Confirmar → La app aparece en el home del teléfono

**iOS (Safari):**
1. Abrir `http://192.168.1.100:3000` en Safari del iPhone (o `https://` si ya configuró SSL)
2. Botón compartir → "Añadir a inicio"
3. Confirmar → La app aparece en el home del iPhone

La app PWA funciona sin internet — usa el Jetson de la red local como backend.

---

## 13C.6 Uso de la API de Open WebUI

Open WebUI expone una API compatible con OpenAI que permite automatizar conversaciones:

```bash
# Obtener la API key desde la interfaz web:
# Settings → Account → API Keys → Create new secret key

# Guardar la key en una variable
OWUI_API_KEY="sk-xxxxxxxxxxxxxxxxxxxx"

# Listar modelos disponibles
curl -s http://localhost:3000/api/models \
  -H "Authorization: Bearer $OWUI_API_KEY" \
  | python3 -c "import sys,json; [print(m['id']) for m in json.load(sys.stdin)['data']]"
```

```python
# Cliente Python — compatible con SDK de OpenAI
# source ~/venvs/llm/bin/activate && python3 este_script.py

from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:3000/api",
    api_key="sk-xxxxxxxxxxxxxxxxxxxx"  # API key de Open WebUI
)

response = client.chat.completions.create(
    model="google/gemma-4-E4B-it",  # ID del modelo en vLLM
    messages=[
        {"role": "user", "content": "Hola, ¿qué puedes hacer por mí?"}
    ],
    max_tokens=200
)

print(response.choices[0].message.content)
```

---

## 13C.7 Scripts de Gestión (sin borrar el contenedor)

Un error común es usar `docker stop && docker rm` para "reiniciar" Open WebUI, lo que borra los usuarios y conversaciones guardados en el volumen Docker. Los scripts correctos distinguen entre **parar** (preserva datos), **eliminar** (borra todo) y **actualizar** (nueva imagen, preserva datos):

```bash
# Crear scripts de gestión
cat > ~/scripts/webui-manage.sh << 'WEBUI_SCRIPT'
#!/bin/bash
# Uso: webui-manage.sh [start|stop|restart|status|update|kill]

case "$1" in
  start)
    docker start open-webui && echo "[OK] Open WebUI iniciado"
    until curl -sf http://localhost:3000 > /dev/null; do sleep 5; done
    echo "[OK] Disponible en http://$(hostname -I | awk '{print $1}'):3000"
    ;;
  stop)
    docker stop open-webui && echo "Open WebUI detenido (datos preservados)"
    ;;
  restart)
    docker restart open-webui
    until curl -sf http://localhost:3000 > /dev/null; do sleep 5; done
    echo "[OK] Open WebUI reiniciado"
    ;;
  status)
    docker inspect --format='Estado: {{.State.Status}}' open-webui 2>/dev/null \
      || echo "Contenedor no existe"
    curl -sf http://localhost:3000 > /dev/null && echo "Web: accesible en :3000" || echo "Web: no responde"
    ;;
  update)
    echo "Actualizando imagen Open WebUI (preservando datos)..."
    docker pull ghcr.io/open-webui/open-webui:main
    docker stop open-webui && docker rm open-webui
    docker run -d \
      --name open-webui --restart no \
      --network host --add-host=host.docker.internal:host-gateway \
      -v open-webui:/app/backend/data \
      -e OLLAMA_BASE_URL=http://localhost:11434 \
      -e OPENAI_API_BASE_URLS="http://localhost:8000/v1;http://localhost:8080/v1" \
      -e OPENAI_API_KEYS="vllm-local;llama-local" \
      ghcr.io/open-webui/open-webui:main
    until curl -sf http://localhost:3000 > /dev/null; do sleep 5; done
    echo "[OK] Open WebUI actualizado"
    ;;
  kill)
    echo "ADVERTENCIA: Esto elimina el contenedor y preserva el volumen de datos"
    docker stop open-webui && docker rm open-webui
    echo "Contenedor eliminado (datos en volumen Docker 'open-webui' intactos)"
    ;;
  *)
    echo "Uso: $0 [start|stop|restart|status|update|kill]"
    ;;
esac
WEBUI_SCRIPT

chmod +x ~/scripts/webui-manage.sh
```

---

## 13C.8 Aliases para el Día a Día

```bash
# Agregar al ~/.bashrc
cat >> ~/.bashrc << 'EOF'

# ── Open WebUI ───────────────────────────────────────────────────────────
alias start-webui='~/scripts/webui-manage.sh start'
alias stop-webui='~/scripts/webui-manage.sh stop'
alias restart-webui='~/scripts/webui-manage.sh restart'
alias webui-status='~/scripts/webui-manage.sh status'
alias update-webui='~/scripts/webui-manage.sh update'
alias kill-webui='~/scripts/webui-manage.sh kill'
alias webui-logs='docker logs open-webui --follow'
alias webui-url='echo "http://$(hostname -I | awk '"'"'{print $1}'"'"'):3000"'
EOF

source ~/.bashrc
```

---

## 13C.9 Monitoreo

```bash
# Ver logs en tiempo real
docker logs open-webui --follow

# Filtrar solo errores
docker logs open-webui --follow 2>&1 | grep -i "error\|exception\|warning"

# Ver uso de recursos del contenedor
docker stats open-webui --no-stream

# Verificar que los backends están visibles desde el contenedor
docker exec open-webui curl -sf http://localhost:8000/v1/models \
  && echo "[OK] vLLM visible desde el contenedor"
docker exec open-webui curl -sf http://localhost:11434/api/tags \
  && echo "[OK] Ollama visible desde el contenedor"
```

---

## 13C.10 Solución de Problemas

### Puerto 3000 no accesible desde Windows

```bash
# Verificar que UFW permite el puerto 3000
sudo ufw status | grep 3000
# Si no aparece:
sudo ufw allow 3000/tcp comment "Open WebUI"

# Verificar que el contenedor está corriendo con red del host
docker inspect open-webui | python3 -c \
  "import sys,json; c=json.load(sys.stdin)[0]; print('NetworkMode:', c['HostConfig']['NetworkMode'])"
# Esperado: NetworkMode: host
```

### Los modelos de vLLM no aparecen en el selector

```bash
# Verificar que vLLM está activo antes de abrir Open WebUI
curl -sf http://localhost:8000/v1/models > /dev/null \
  && echo "[OK] vLLM activo" || echo "[ERROR] vLLM inactivo — ejecute start-qwen35 primero"

# Si vLLM acaba de iniciarse, refrescar los modelos en Open WebUI:
# Settings → Connections → Refresh (icono de recarga junto a la URL)
```

### Los usuarios o conversaciones se perdieron después de `docker rm`

```bash
# Verificar que el volumen Docker todavía existe
docker volume ls | grep open-webui
# Si aparece: docker volume ls → open-webui  local  → los datos están intactos

# Recrear el contenedor apuntando al mismo volumen
docker run -d \
  --name open-webui --restart no \
  --network host --add-host=host.docker.internal:host-gateway \
  -v open-webui:/app/backend/data \   # ← Este volumen contiene los datos
  -e OLLAMA_BASE_URL=http://localhost:11434 \
  ghcr.io/open-webui/open-webui:main
```

> **CONSEJO:** Nunca use `docker volume rm open-webui` a menos que quiera borrar todos los usuarios, conversaciones y documentos cargados. El volumen es persistente entre reinicios del contenedor.

### Upload de documentos falla o no indexa

```bash
# Verificar que el modelo de embeddings está instalado en Ollama
ollama list | grep nomic

# Si no está instalado:
ollama pull nomic-embed-text

# Después de instalar el modelo, configurar en Open WebUI:
# Settings → Documents → Embedding Model Backend: Ollama
# Embedding Model: nomic-embed-text
```

---

## 13C.11 SSL Local con mkcert — Desbloquear el Micrófono en el Navegador

Los navegadores modernos (Chrome, Edge, Firefox) bloquean el acceso al micrófono en conexiones HTTP. Para usar la función de **entrada de voz** de Open WebUI desde Windows, necesita HTTPS. La solución más limpia es `mkcert` — crea certificados TLS de confianza local sin necesidad de un dominio ni de pagar a una CA.

### 13C.11.1 Instalar mkcert en el Jetson

```bash
# Instalar mkcert
sudo apt install -y libnss3-tools
curl -L https://github.com/FiloSottile/mkcert/releases/download/v1.4.4/mkcert-v1.4.4-linux-arm64 \
  -o ~/bin/mkcert
chmod +x ~/bin/mkcert

# Verificar:
mkcert --version
```

```
# Salida esperada:
v1.4.4
```

### 13C.11.2 Crear la CA local y el certificado

```bash
# Instalar la CA local de mkcert en el sistema del Jetson
mkcert -install

# Crear certificado para la IP del Jetson
# IMPORTANTE: reemplaza 192.168.1.100 con la IP estatica del Capitulo 2
mkdir -p ~/certs/openwebui
cd ~/certs/openwebui

mkcert 192.168.1.100 localhost 127.0.0.1
```

```
# Salida esperada:
Created a new certificate valid for the following names:
 - "192.168.1.100"
 - "localhost"
 - "127.0.0.1"

The certificate is at "./192.168.1.100+2.pem" and the key at "./192.168.1.100+2-key.pem"
```

### 13C.11.3 Instalar la CA en Windows (para que el navegador confíe)

```bash
# Ver donde esta el archivo de la CA de mkcert:
mkcert -CAROOT
# Ejemplo: /home/jetson/.local/share/mkcert

# Copiar el archivo rootCA.pem a Windows via SCP [EN WINDOWS POWERSHELL]:
# scp jetson:~/.local/share/mkcert/rootCA.pem C:\Users\TU_USUARIO\Desktop\jetson-CA.pem
```

```
# En Windows — instalar la CA en el almacen de certificados:
# 1. Doble clic en jetson-CA.pem
# 2. "Instalar certificado" -> "Equipo local" -> "Colocar todos los certificados en el siguiente almacen"
# 3. Seleccionar "Entidades de certificacion raiz de confianza" -> Finalizar
# 4. Reiniciar Chrome/Edge
```

### 13C.11.4 Relanzar Open WebUI con HTTPS

```bash
# Detener la instancia HTTP existente
docker stop open-webui 2>/dev/null || true

# Lanzar con SSL
docker run -d \
  --name open-webui \
  --restart no \
  --network host \
  -v open-webui-data:/app/backend/data \
  -v ~/certs/openwebui:/certs \
  -e OLLAMA_BASE_URL=http://localhost:11434 \
  -e WEBUI_SSL_CERT_FILE=/certs/192.168.1.100+2.pem \
  -e WEBUI_SSL_KEY_FILE=/certs/192.168.1.100+2-key.pem \
  ghcr.io/open-webui/open-webui:main

docker logs -f open-webui | grep -E "https|started|error"
```

```
# Salida esperada:
INFO:     Uvicorn running on https://0.0.0.0:3000
INFO:     Application startup complete.
```

```bash
# Verificar HTTPS desde el Jetson:
curl -sk https://localhost:3000 | grep -o '<title>[^<]*</title>'
# Salida: <title>Open WebUI</title>
```

Acceda desde Windows: `https://192.168.1.100:3000` — el navegador debe mostrar el candado verde.

> **CONSEJO:** Una vez instalada la CA de mkcert en Windows, también puede acceder a otros servicios del Jetson con HTTPS usando el mismo certificado (N8N, servicios FastAPI, etc.).

---

## 13C.12 Proyecto — Asistente de Conversación en Inglés con Nemotron Omni

Nemotron-Nano-Omni es el modelo multimodal de NVIDIA que acepta texto, imagen y audio. En este proyecto construimos una aplicación de aprendizaje de inglés que usa el micrófono del navegador (habilitado por SSL del paso anterior) para una conversación fluida.

**Lo que construiremos:** Un asistente que:
1. Recibe audio del micrófono vía Open WebUI
2. Transcribe la voz a texto (STT interno del modelo)
3. Responde en inglés con correcciones gramaticales y traducción al español
4. Reproduce la respuesta en voz (TTS en el Capítulo 17)

### 13C.12.1 Iniciar el motor de inferencia (Nemotron Omni)

```bash
# Nemotron Omni requiere MAXN (~24 GB RAM, ~45 tok/s)
sudo nvpmodel -m 0 && sudo jetson_clocks
echo "Modo MAXN activado"

# Descargar el modelo GGUF (si no esta descargado):
# hf download nvidia/Nemotron-Nano-Omni-GGUF --include "nemotron-nano-omni-Q4_K_M.gguf" \
#   --local-dir ~/data/models/gguf/

# Iniciar llama.cpp con soporte multimodal
# (ver Capitulo 12 §12.2 para la compilacion de llama.cpp)
GGUF=$(ls ~/data/models/gguf/*nemotron*omni*.gguf 2>/dev/null | head -1)
[ -z "$GGUF" ] && echo "[ERROR] Modelo Nemotron Omni no encontrado" && exit 1

~/llama.cpp/build/bin/llama-server \
  -m "$GGUF" \
  --host 0.0.0.0 --port 8080 \
  -c 32768 -ngl 999 --flash-attn \
  --mmproj ~/data/models/gguf/nemotron-omni-mmproj.gguf &

# Verificar arranque (~30-60 segundos):
until curl -sf http://localhost:8080/health > /dev/null; do sleep 5; echo -n "."; done
echo " [OK] Nemotron Omni activo en :8080"
```

### 13C.12.2 Configurar Open WebUI para usar Nemotron Omni

```bash
# Conectar Open WebUI a llama.cpp:
# 1. Abrir https://192.168.1.100:3000 en Windows (con SSL del paso anterior)
# 2. Admin Panel -> Settings -> Connections -> OpenAI API -> "+"
# 3. URL: http://localhost:8080/v1   API Key: llama-local
# 4. Guardar

# Verificar que el modelo aparece en el selector de Open WebUI
curl -s http://localhost:8080/v1/models | python3 -m json.tool | grep '"id"'
```

### 13C.12.3 Crear el System Prompt del asistente de inglés

En Open WebUI → crear un nuevo "Workspace" con este system prompt:

```
# [COPIAR EN Open WebUI -> Admin Panel -> Models -> Edit -> System Prompt]

You are an English conversation assistant helping a Spanish speaker improve their English.

INSTRUCTIONS:
1. The user will speak or type in Spanish or broken English
2. Respond ALWAYS in this format:
   - [CORRECTED]: The grammatically correct version of what the user said (in English)
   - [RESPONSE]: Your natural conversational response (in English, simple vocabulary)
   - [TRADUCCION]: Spanish translation of your response
3. Keep responses SHORT (2-3 sentences max) to maintain conversation flow
4. Be encouraging and patient
5. If the user asks to practice a specific topic, adapt the conversation to that topic

Start by greeting the user in English and asking what they want to practice today.
```

### 13C.12.4 Flujo de conversación

```bash
# En Windows (Chrome con la CA instalada):
# 1. Abrir https://192.168.1.100:3000
# 2. Seleccionar modelo "nemotron-omni" en el dropdown
# 3. Hacer clic en el icono de microfono (solo disponible con HTTPS)
# 4. Hablar en espanol o ingles incorrecto
# 5. El asistente responde con correccion + respuesta + traduccion
```

```
# Ejemplo de conversacion:
Usuario: "I go to the store yesterday"
Asistente:
[CORRECTED]: "I went to the store yesterday"
[RESPONSE]: Great! You're using past tense. What did you buy at the store?
[TRADUCCION]: ¡Bien! Estás usando el tiempo pasado. ¿Qué compraste en la tienda?
```

### 13C.12.5 Monitoreo durante la sesión

```bash
# Ver el uso de recursos durante la conversacion (en otra terminal):
watch -n 2 'docker stats open-webui --no-stream && echo "---" && \
  curl -s http://localhost:8080/metrics 2>/dev/null | grep "tokens" | head -3'

# O usar jtop para ver GPU + RAM en tiempo real:
jtop
```

> **CONSEJO:** Para una experiencia completa con voz de salida (el asistente habla en inglés), configure el TTS de Open WebUI conectándolo al servidor Kokoro del Capítulo 17. La entrada es el micrófono (habilitado por SSL), la salida es texto-a-voz via Kokoro.

---

## Resumen del Capítulo 13C

Open WebUI es la interfaz gráfica que unifica todos los motores de inferencia del Jetson:

- Puerto 3000 (`--restart no` — arranque limpio como todos los servicios)
- El volumen `open-webui-data` guarda usuarios, conversaciones y documentos de forma persistente
- SSL local con mkcert desbloquea el micrófono del navegador — indispensable para el proyecto de inglés
- **Nunca use `docker rm open-webui`** para reiniciar — use `docker restart open-webui` (preserva el volumen)
- Funciona como PWA en iOS y Android desde `https://192.168.1.100:3000`

El capítulo siguiente (13D) cubre tool calling avanzado: cómo implementar herramientas personalizadas que los modelos pueden invocar automáticamente, con ejemplos Python integrados en Open WebUI.
