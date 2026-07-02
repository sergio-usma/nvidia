# Capítulo 25 — Generador de Contenido para LinkedIn

## Introducción

LinkedIn es la red profesional más importante del mundo, pero crear contenido que realmente conecte — con voz auténtica y consistencia — es difícil de mantener. Este capítulo construye un generador de posts para LinkedIn que aprende de su propio estilo de escritura (few-shot prompting) y usa dos modelos en secuencia: primero razonamiento profundo para estructurar las ideas, luego refinamiento para el tono profesional. La publicación se realiza via la API oficial de LinkedIn.

**Prerequisitos:**
- Ollama con `qwen3:7b` o `deepseek-r1:7b` (Capítulo 12)
- Cuenta de LinkedIn con aplicación OAuth2 registrada

**Tiempo de generación por post:** 60–90 segundos
**Modo de energía:** 30W (modelos 7B)

> **API de LinkedIn:** Requiere una aplicación registrada en [developer.linkedin.com](https://developer.linkedin.com). Las cuentas personales tienen acceso al endpoint `w_member_social` para publicar. El token OAuth2 debe renovarse periódicamente (60–90 días según el tipo de acceso).

---

## 23.1 Prerrequisito — LinkedIn Developer Setup

### 23.1.1 Crear la Aplicación OAuth2

1. Vaya a [developer.linkedin.com](https://developer.linkedin.com) → **My Apps** → **Create App**
2. Seleccione su empresa (o créela)
3. En **Products**, solicite: **Sign In with LinkedIn using OpenID Connect** y **Share on LinkedIn**
4. En **Auth**, anote: `Client ID` y `Client Secret`
5. Configure **Authorized redirect URLs**: `http://localhost:8765/callback`

### 23.1.2 Obtener el Access Token (Flujo OAuth2)

```python
# scripts/linkedin_auth.py
"""
Flujo OAuth2 para obtener el access token de LinkedIn.
Ejecutar UNA VEZ para obtener el token; guardarlo para uso posterior.
"""
import json
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from pathlib import Path


CLIENT_ID = "your_client_id_here"
CLIENT_SECRET = "your_client_secret_here"
REDIRECT_URI = "http://localhost:8765/callback"
SCOPES = ["openid", "profile", "w_member_social"]


class OAuthHandler(BaseHTTPRequestHandler):
    """Servidor local que captura el código de autorización."""
    auth_code = None
    
    def do_GET(self):
        if "/callback" in self.path:
            params = dict(urllib.parse.parse_qsl(
                urllib.parse.urlparse(self.path).query
            ))
            OAuthHandler.auth_code = params.get("code")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h1>Autorizado. Puede cerrar esta ventana.</h1>")
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suprimir logs del servidor


def obtener_token():
    """Ejecuta el flujo OAuth2 completo."""
    
    # Paso 1: Redirigir al usuario a LinkedIn
    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&scope={urllib.parse.quote(' '.join(SCOPES))}"
        f"&state=jetson_linkedin_auth"
    )
    
    print("Abriendo LinkedIn en el browser para autorización...")
    print(f"Si no se abre automáticamente, visite:\n{auth_url}\n")
    webbrowser.open(auth_url)
    
    # Paso 2: Escuchar el callback
    print("Esperando autorización... (Complete el login en el browser)")
    server = HTTPServer(("localhost", 8765), OAuthHandler)
    server.handle_request()
    
    code = OAuthHandler.auth_code
    if not code:
        print("[ERROR] No se recibió código de autorización")
        return None
    
    print(f"[OK] Código de autorización recibido")
    
    # Paso 3: Intercambiar código por token
    token_resp = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
        }
    )
    
    token_data = token_resp.json()
    
    if "access_token" in token_data:
        # Guardar el token
        config_dir = Path(__file__).parent.parent / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        with open(config_dir / "linkedin_token.json", "w") as f:
            json.dump(token_data, f, indent=2)
        
        print(f"[OK] Token guardado en: config/linkedin_token.json")
        print(f"   Expira en: {token_data.get('expires_in', 'N/A')} segundos")
        return token_data["access_token"]
    else:
        print(f"[ERROR] Error obteniendo token: {token_data}")
        return None


if __name__ == "__main__":
    # Reemplazar CLIENT_ID y CLIENT_SECRET antes de ejecutar
    obtener_token()
```

```bash
# Ejecutar UNA VEZ para autenticarse
source ~/venvs/dev/bin/activate
python scripts/linkedin_auth.py
```

---

## 23.2 Script 1 — Generador de Posts con Few-Shot Prompting

```python
# scripts/post_generator.py
"""
Genera posts de LinkedIn en el estilo personal del usuario.
Usa few-shot prompting con posts previos del usuario como ejemplos.
"""
import json
import time
from openai import OpenAI
from pathlib import Path


def cargar_ejemplos_propios() -> list[str]:
    """
    Carga posts propios del usuario como ejemplos few-shot.
    Guarde sus mejores posts en config/mis_posts.json para entrenar el estilo.
    """
    ejemplos_path = Path(__file__).parent.parent / "config" / "mis_posts.json"
    
    if ejemplos_path.exists():
        with open(ejemplos_path) as f:
            return json.load(f).get("posts", [])
    
    # Posts de ejemplo si no hay propios configurados
    return [
        "La inteligencia artificial no reemplaza al profesional — amplifica sus capacidades. Llevo 5 años trabajando con IA y el patrón es siempre el mismo: quienes la adoptan temprano se convierten en indispensables.\n\n¿Cuándo fue la última vez que automatizaste algo en tu trabajo?\n\n#InteligenciaArtificial #Productividad #Liderazgo",
        "Lección de esta semana: el 80% del tiempo en proyectos de IA no es programar — es limpiar datos y definir bien el problema.\n\nLa parte 'glamorosa' de entrenar modelos representa quizás el 20% del trabajo real.\n\nSi estás empezando en data science, aprende SQL y Excel antes que Python.\n\n#DataScience #CarreraEnIA #ConsejoProfesional"
    ]


def generar_post_linkedin(
    tema: str,
    fuente: str = None,
    tipo: str = "reflexion",
    modelo_razon: str = "deepseek-r1:7b",
    modelo_refine: str = "qwen3:7b"
) -> dict:
    """
    Genera un post de LinkedIn en dos fases:
    1. Razonamiento (deepseek-r1 o qwen3 con thinking) — estructura las ideas
    2. Refinamiento (qwen3) — ajusta el tono y el estilo personal
    
    Args:
        tema: Tema o idea principal del post
        fuente: URL de noticia o artículo fuente (opcional)
        tipo: "reflexion", "noticia", "consejo", "historia", "pregunta"
    
    Returns:
        dict con 'borrador', 'post_final', 'hashtags'
    """
    cliente = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    
    ejemplos = cargar_ejemplos_propios()
    ejemplos_texto = "\n\n---\n\n".join(f"EJEMPLO {i+1}:\n{e}" for i, e in enumerate(ejemplos[:3]))
    
    tipos_guia = {
        "reflexion": "Una observación personal con lección aprendida. Comenzar con una declaración fuerte.",
        "noticia": "Análisis de una noticia reciente con perspectiva propia. Añadir contexto y opinión.",
        "consejo": "Tip accionable basado en experiencia. Concreto, específico, aplicable hoy.",
        "historia": "Mini-historia con inicio, conflicto y resolución. Terminar con la lección.",
        "pregunta": "Pregunta que invite a la reflexión. 3-4 párrafos + pregunta final abierta."
    }
    
    # ── FASE 1: Razonamiento ─────────────────────────────────
    print(f"  Fase 1/2 — Estructurando ideas ({modelo_razon})...")
    
    prompt_razon = f"""Quiero crear un post de LinkedIn sobre: "{tema}"
{"Fuente/contexto: " + fuente if fuente else ""}
Tipo de post: {tipo} — {tipos_guia.get(tipo, "post estándar")}

Analiza el tema y estructura las ideas principales:
1. ¿Cuál es el gancho (primera oración impactante)?
2. ¿Qué historia o contexto le da credibilidad?
3. ¿Cuál es la lección o valor principal para el lector?
4. ¿Cómo terminar con una llamada a la acción o pregunta?

No escribas el post todavía — solo analiza la estructura."""
    
    resp1 = cliente.chat.completions.create(
        model=modelo_razon,
        messages=[{"role": "user", "content": prompt_razon}],
        max_tokens=600
    )
    estructura = resp1.choices[0].message.content.strip()
    
    # ── FASE 2: Escritura con estilo personal ────────────────
    print(f"  Fase 2/2 — Escribiendo con estilo propio ({modelo_refine})...")
    
    prompt_refine = f"""Escribe un post de LinkedIn basándote en esta estructura:

{estructura}

Usando este ESTILO PERSONAL (adapta tu escritura a estos ejemplos):
{ejemplos_texto}

Reglas del post:
- Entre 150-300 palabras
- Voz en primera persona, tono auténtico (no corporativo)
- Párrafos cortos (2-3 oraciones máximo)
- Dejar línea en blanco entre párrafos
- No usar bullets ni numeración (es LinkedIn, no un informe)
- Incluir 3-5 hashtags relevantes AL FINAL (en una sola línea)
- El primer párrafo es el gancho — debe hacer que el lector quiera seguir leyendo

Escribe SOLO el post final listo para publicar."""
    
    resp2 = cliente.chat.completions.create(
        model=modelo_refine,
        messages=[{"role": "user", "content": prompt_refine}],
        max_tokens=700,
        temperature=0.75
    )
    post_final = resp2.choices[0].message.content.strip()
    
    # Extraer hashtags
    lineas = post_final.split("\n")
    hashtags = []
    post_sin_hashtags = []
    
    for linea in lineas:
        if linea.strip().startswith("#") and " " not in linea.strip().split("#")[1]:
            hashtags = [h for h in linea.split() if h.startswith("#")]
        else:
            post_sin_hashtags.append(linea)
    
    return {
        "tema": tema,
        "tipo": tipo,
        "estructura": estructura,
        "post_final": post_final,
        "post_cuerpo": "\n".join(post_sin_hashtags).strip(),
        "hashtags": hashtags
    }
```

---

## 23.3 Script 2 — Publicador en LinkedIn

```python
# scripts/linkedin_publisher.py
"""
Publica posts en LinkedIn via API oficial.
"""
import json
import requests
from pathlib import Path
from datetime import datetime


def cargar_token() -> str:
    """Carga el token de acceso de LinkedIn."""
    token_path = Path(__file__).parent.parent / "config" / "linkedin_token.json"
    
    if not token_path.exists():
        raise FileNotFoundError(
            "Token no encontrado. Ejecute primero: python scripts/linkedin_auth.py"
        )
    
    with open(token_path) as f:
        data = json.load(f)
    
    return data.get("access_token", "")


def obtener_perfil_id(access_token: str) -> str:
    """Obtiene el URN del perfil de LinkedIn."""
    resp = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15
    )
    
    if resp.status_code == 200:
        data = resp.json()
        sub = data.get("sub", "")
        return f"urn:li:person:{sub}"
    else:
        raise RuntimeError(f"Error obteniendo perfil: {resp.status_code} — {resp.text}")


def publicar_post(
    texto: str,
    access_token: str = None,
    visibilidad: str = "PUBLIC"
) -> dict:
    """
    Publica un post de texto en LinkedIn.
    
    Args:
        texto: Contenido del post (máximo 3000 caracteres)
        visibilidad: "PUBLIC", "CONNECTIONS", "LOGGED_IN"
    
    Returns:
        dict con 'post_id' y 'url' si fue exitoso
    """
    if access_token is None:
        access_token = cargar_token()
    
    # Obtener ID del autor
    autor_urn = obtener_perfil_id(access_token)
    
    # Payload para la API UGC Posts
    payload = {
        "author": autor_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": texto[:3000]  # LinkedIn máximo 3000 chars
                },
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": visibilidad
        }
    }
    
    resp = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        },
        json=payload,
        timeout=30
    )
    
    if resp.status_code in (200, 201):
        post_id = resp.headers.get("x-restli-id", "")
        # Construir URL aproximada (la URL real la asigna LinkedIn)
        print(f"  [OK] Post publicado en LinkedIn (ID: {post_id})")
        return {"post_id": post_id, "plataforma": "linkedin", "estado": "publicado"}
    else:
        error_data = {}
        try:
            error_data = resp.json()
        except:
            pass
        mensaje_error = error_data.get("message", resp.text[:200])
        print(f"  [ERROR] Error publicando: {resp.status_code} — {mensaje_error}")
        
        # Error común: token expirado
        if resp.status_code == 401:
            print("     Token expirado — ejecute: python scripts/linkedin_auth.py")
        
        return {"error": mensaje_error, "plataforma": "linkedin"}
```

---

## 23.4 Pipeline Interactivo Completo

```python
# linkedin_main.py
"""
Pipeline interactivo para generar y publicar contenido en LinkedIn.
"""
import json
import time
from scripts.post_generator import generar_post_linkedin
from scripts.linkedin_publisher import publicar_post


def pipeline_interactivo():
    print("""
╔═══════════════════════════════════════════════════════╗
║       GENERADOR DE CONTENIDO LINKEDIN — JETSON AI     ║
╚═══════════════════════════════════════════════════════╝
""")
    
    # Input del usuario
    print("¿Sobre qué tema desea escribir hoy?")
    tema = input("Tema: ").strip()
    
    print("\nTipo de post:")
    print("  1. reflexion — Observación personal con lección")
    print("  2. consejo   — Tip accionable basado en experiencia")
    print("  3. historia  — Mini-historia con lección")
    print("  4. noticia   — Análisis de noticia reciente")
    print("  5. pregunta  — Pregunta que invite a reflexionar")
    
    tipos = {"1": "reflexion", "2": "consejo", "3": "historia", "4": "noticia", "5": "pregunta"}
    opcion = input("Opción (1-5, default: 1): ").strip() or "1"
    tipo = tipos.get(opcion, "reflexion")
    
    fuente = None
    if tipo == "noticia":
        fuente = input("URL de la noticia fuente (opcional): ").strip() or None
    
    # Generar
    print(f"\n── Generando post de tipo '{tipo}'... ──")
    inicio = time.time()
    resultado = generar_post_linkedin(tema=tema, fuente=fuente, tipo=tipo)
    tiempo = time.time() - inicio
    
    # Mostrar resultado
    print(f"\n{'═' * 55}")
    print("POST GENERADO:")
    print('═' * 55)
    print(resultado["post_final"])
    print('═' * 55)
    print(f"Caracteres: {len(resultado['post_final'])}/3000")
    print(f"Generado en: {tiempo:.1f} segundos")
    
    # Opciones
    print("\n¿Qué desea hacer?")
    print("  1. Publicar ahora")
    print("  2. Regenerar (con el mismo tema)")
    print("  3. Guardar como borrador y salir")
    print("  4. Salir sin guardar")
    
    accion = input("Opción: ").strip()
    
    if accion == "1":
        print("\nPublicando en LinkedIn...")
        resultado_pub = publicar_post(resultado["post_final"])
        
        if "post_id" in resultado_pub:
            print("[OK] Post publicado exitosamente")
        else:
            print("[ERROR] Error al publicar — revise el token de acceso")
    
    elif accion == "2":
        print("\nRegenerando...")
        pipeline_interactivo()  # recursivo — vuelve al inicio con el mismo flujo
    
    elif accion == "3":
        from pathlib import Path
        import json as _json
        from datetime import datetime
        
        ruta = Path("output") / f"borrador_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        
        with open(ruta, "w", encoding="utf-8") as f:
            _json.dump(resultado, f, ensure_ascii=False, indent=2)
        
        print(f"[OK] Borrador guardado en: {ruta}")
    
    elif accion == "4":
        print("ℹ️  Saliendo sin guardar")


if __name__ == "__main__":
    import subprocess
    import sys
    
    # Verificar que Ollama está activo
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/version", timeout=3)
        if resp.status_code != 200:
            raise Exception()
    except:
        print("[WARN]  Ollama no está activo. Iniciando...")
        subprocess.run(["sudo", "systemctl", "start", "ollama"])
        import time
        time.sleep(5)
    
    pipeline_interactivo()
```

```bash
# Ejecutar el generador interactivo
source ~/venvs/dev/bin/activate
python linkedin_main.py
```

---

## 23.5 Guardar Estilo Personal (Few-Shot Training)

Para que el generador aprenda su estilo, guarde sus mejores posts como ejemplos:

```bash
# Crear el archivo de estilo personal
cat > ~/projects/linkedin-content/config/mis_posts.json << 'EOF'
{
    "perfil": {
        "nombre": "Su Nombre",
        "sector": "Tecnología / IA",
        "tono": "directo, honesto, sin buzzwords"
    },
    "posts": [
        "Primer post suyo que le gustó cómo quedó...",
        "Segundo post con buen engagement...",
        "Tercer post — el que más comentarios recibió..."
    ]
}
EOF
```

Cuantos más ejemplos proporcione (mínimo 3, ideal 10), mejor capturará el generador su voz.

---

## 23.6 Limpieza Post-Pipeline

```bash
# Pipeline sin contenedores GPU pesados
sudo systemctl stop ollama 2>/dev/null
pwr-15w
echo "[OK] Pipeline LinkedIn detenido"
```

---

## 23.7 Verificación Final

```bash
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   VERIFICACIÓN CAPÍTULO 23 — LINKEDIN CONTENT           ║"
echo "╚═══════════════════════════════════════════════════════╝"

echo ""
echo "── Ollama ──"
ollama list 2>/dev/null | grep -E "qwen3|deepseek" \
  && echo "  [OK] Modelos disponibles" || echo "  ○  Instalar: ollama pull qwen3:7b"

echo ""
echo "── Configuración LinkedIn ──"
[ -f ~/projects/linkedin-content/config/linkedin_token.json ] \
  && echo "  [OK] Token LinkedIn configurado" \
  || echo "  ○  Ejecutar: python scripts/linkedin_auth.py"
[ -f ~/projects/linkedin-content/config/mis_posts.json ] \
  && echo "  [OK] Ejemplos de estilo personal configurados" \
  || echo "  ○  Crear config/mis_posts.json con sus posts como ejemplos"

echo ""
echo "═════════════════════════════════════════════════════════"
```

---

## 23.8 Escalabilidad y Extensiones

### 23.8.1 Bot de Telegram para Generar y Publicar en LinkedIn

El pipeline puede integrarse con Telegram para recibir temas o ideas por chat y publicar automáticamente en LinkedIn sin acceso directo al Jetson.

**Flujo con N8N** (ver Capítulo 14):

```yaml
Nodo 1 — Telegram Trigger:
  tipo: telegram_trigger
  evento: message_received
  filtro: texto (tema o instrucción de publicación)
  # Ejemplo: "publica sobre inteligencia artificial en manufactura"

Nodo 2 — Execute Command:
  tipo: execute_command
  comando: |
    python3 ~/projects/linkedin-content/scripts/pipeline.py \
      --topic "{{message_text}}" \
      --style-file ~/projects/linkedin-content/data/mi_estilo.json
  timeout: 90

Nodo 3 — Send Message:
  tipo: telegram_send_message
  chat_id: {{chat_id}}
  texto: "Post publicado en LinkedIn: {{post_url}}"
```

**Flujo con OpenClaw** (ver Capítulo 11A):

```json
"agents": {
  "linkedin": {
    "description": "Genera y publica contenido en LinkedIn con estilo personal",
    "command": "python3 ~/projects/linkedin-content/scripts/pipeline.py --topic {{input}}",
    "channels": ["telegram"]
  }
}
```

### 23.8.2 Evaluación del Hermes Agent para Aprendizaje Adaptativo de Tendencias

**Hermes Agent** (NVIDIA NIM / local) es un modelo especializado en **function calling** y memoria episódica a largo plazo. Para el pipeline de LinkedIn, resulta especialmente útil porque puede:

- Aprender el vocabulario y los temas que generan más engagement en el perfil del usuario
- Almacenar en memoria las publicaciones anteriores y sus métricas para refinar el estilo
- Adaptar automáticamente el tono según el contexto (formal para artículos técnicos, conversacional para anécdotas)

**Comparativa para este caso de uso:**

| Modelo | Aprendizaje adaptativo | Creatividad | Memoria episódica | Uso de VRAM |
|---|---|---|---|---|
| qwen3:7b (actual) | No (few-shot manual) | Alta | No | ~5.5 GB |
| deepseek-r1:7b (refinamiento) | No | Alta | No | ~5.5 GB |
| **Hermes-3 (8B)** | Parcial (via RAG) | Alta | Sí (via tool calls) | ~6 GB |
| Hermes-3 (70B) vía OpenRouter | Sí | Muy Alta | Sí | Externo |

**Implementación con Hermes-3 local (8B):**

```bash
# Descargar Hermes-3 via Ollama
ollama pull hermes3:8b

# Verificar
ollama list | grep hermes
```

```python
# En pipeline.py — cambiar modelo según modo
import os

MODELO = os.getenv("LINKEDIN_MODEL", "qwen3:7b")
# Opciones:
#   "qwen3:7b"         — rapidez, creatividad
#   "deepseek-r1:7b"   — razonamiento estructurado
#   "hermes3:8b"       — function calling, seguimiento de contexto largo

cliente = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
```

```bash
# Alias para cambiar de modelo sin editar código
alias linkedin-qwen="LINKEDIN_MODEL=qwen3:7b    python3 ~/projects/linkedin-content/scripts/pipeline.py"
alias linkedin-deep="LINKEDIN_MODEL=deepseek-r1:7b python3 ~/projects/linkedin-content/scripts/pipeline.py"
alias linkedin-hermes="LINKEDIN_MODEL=hermes3:8b  python3 ~/projects/linkedin-content/scripts/pipeline.py"
```

> **EVALUACIÓN:** Hermes-3 es viable para este pipeline en el Jetson AGX Orin 64GB (8B cabe en ~6 GB VRAM). Su ventaja real aparece al implementar un sistema de memoria episódica que almacene las publicaciones anteriores en ChromaDB y las recupere como contexto — combinación RAG + Hermes que supera el few-shot manual de los otros modelos para mantener consistencia de estilo a lo largo del tiempo.

### 23.8.3 Modo Mixto con OpenRouter

Para publicaciones de gran visibilidad (artículos, noticias de empresa), use modelos de mayor capacidad vía OpenRouter:

```python
import os
from openai import OpenAI

USE_LOCAL = os.getenv("USE_LOCAL_LLM", "true").lower() == "true"

if USE_LOCAL:
    cliente = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    MODELO  = os.getenv("LINKEDIN_MODEL", "qwen3:7b")
else:
    cliente = OpenAI(
        base_url=os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1"),
        api_key=os.getenv("OPENROUTER_API_KEY", ""),
    )
    MODELO = "meta-llama/llama-3.3-70b-instruct:free"
```

```bash
alias linkedin-local="USE_LOCAL_LLM=true  python3 ~/projects/linkedin-content/scripts/pipeline.py"
alias linkedin-cloud="USE_LOCAL_LLM=false python3 ~/projects/linkedin-content/scripts/pipeline.py"
```

---

> **Próximo paso:** El Capítulo 24 construye el asistente de voz offline completo — faster-whisper + LLM + kokoro-tts — con latencia menor a 3 segundos desde que termina de hablar hasta que escucha la respuesta.
