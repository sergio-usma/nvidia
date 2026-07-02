# Capítulo 24 — Automatización de Embudo de Ventas para Redes Sociales

## Introducción

Crear contenido de calidad para Facebook e Instagram de forma consistente es uno de los mayores desafíos del marketing digital. Este capítulo construye un pipeline que genera posts completos — con variaciones A/B, hashtags optimizados y diferentes tonos — y los publica automáticamente usando la Meta Graph API oficial.

El Jetson genera el contenido localmente (sin costos de API de IA), y la publicación se hace vía la API oficial de Meta, lo que cumple completamente con los términos de servicio de la plataforma.

**Prerequisitos:**
- Ollama activo con `qwen3:7b` (Capítulo 12)
- Cuenta de Facebook Business con una Facebook Page
- App de Meta Developers con permisos `pages_manage_posts` y `instagram_content_publish`
- Token de acceso de página (Page Access Token) — válido a largo plazo

**Tiempo de generación por campaña (5 posts):** 3–8 minutos
**Modo de energía:** 30W (solo generación de texto)

> **NOTA DE CUMPLIMIENTO:** Este pipeline usa exclusivamente la Meta Graph API oficial. Requiere una Facebook Page verificada, una aplicación de Meta Developers configurada y un Page Access Token válido. No incluye scraping, bots no autorizados, ni técnicas que violen los términos de servicio de Meta.

---

## 22.1 Prerrequisito — Meta Developers Setup

### 22.1.1 Obtener el Page Access Token

1. Vaya a [developers.facebook.com](https://developers.facebook.com) y cree una aplicación de tipo "Business"
2. En su aplicación → **Add Products** → **Facebook Login** y **Instagram Graph API**
3. En **Permisos de la app**, solicite:
 - `pages_manage_posts`
 - `pages_read_engagement`
 - `instagram_content_publish`
 - `instagram_basic`
4. Use el **Graph API Explorer** para obtener un token de usuario y luego genere un **Page Access Token** de larga duración
5. Para extender la validez a 60 días, use el endpoint de extensión de tokens

```bash
# Guardar el token de forma segura (nunca en código versionado)
mkdir -p ~/projects/sales-funnel/config
cat > ~/projects/sales-funnel/config/secrets.json << 'EOF'
{
    "meta": {
        "page_access_token": "EAAxxxx...",
        "page_id": "123456789",
        "instagram_account_id": "987654321",
        "app_id": "111222333",
        "app_secret": "abc123def456"
    }
}
EOF
chmod 600 ~/projects/sales-funnel/config/secrets.json
```

> **SEGURIDAD:** Nunca incluya el token en archivos de código fuente. El archivo `secrets.json` debe estar en `.gitignore` si usa control de versiones.

---

## 22.2 Estructura del Proyecto

```bash
mkdir -p ~/projects/sales-funnel/{config,scripts,output,templates}
cd ~/projects/sales-funnel
```

---

## 22.3 Script 1 — Generador de Contenido con LLM

```python
# scripts/content_generator.py
"""
Genera contenido de redes sociales para Facebook e Instagram.
"""
import json
import time
from openai import OpenAI
from pathlib import Path


def cargar_config() -> dict:
    """Carga configuración y secrets."""
    config_path = Path(__file__).parent.parent / "config"
    secrets = {}
    if (config_path / "secrets.json").exists():
        with open(config_path / "secrets.json") as f:
            secrets = json.load(f)
    return secrets


def generar_post_facebook(
    tema: str,
    producto: str,
    tono: str = "profesional",
    modelo: str = "qwen3:7b"
) -> dict:
    """
    Genera un post de Facebook completo con variaciones A/B.
    
    Args:
        tema: Tema o mensaje principal del post
        producto: Nombre del producto o servicio
        tono: "profesional", "casual", "inspiracional", "educativo"
    
    Returns:
        dict con 'variante_a', 'variante_b', 'hashtags'
    """
    cliente = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    
    prompt = f"""Crea un post de Facebook sobre "{tema}" para el producto/servicio "{producto}".

Tono: {tono}

Crea DOS variantes (A/B testing) siguiendo estas reglas:
- Variante A: comienza con una pregunta al lector
- Variante B: comienza con un hecho impactante o estadística
- Cada variante: 150-300 palabras
- Incluir llamada a la acción al final
- No usar emojis excesivos (máximo 3 por post)
- Incluir 5-8 hashtags relevantes en una sección aparte

Responde SOLO en este formato JSON:
{{
  "variante_a": "Texto del post A...",
  "variante_b": "Texto del post B...",
  "hashtags": ["hashtag1", "hashtag2", "hashtag3", "hashtag4", "hashtag5"]
}}"""
    
    respuesta = cliente.chat.completions.create(
        model=modelo,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1200,
        temperature=0.8
    )
    
    contenido = respuesta.choices[0].message.content.strip()
    
    # Extraer JSON
    if "```json" in contenido:
        contenido = contenido.split("```json")[1].split("```")[0].strip()
    elif "```" in contenido:
        contenido = contenido.split("```")[1].split("```")[0].strip()
    
    try:
        return json.loads(contenido)
    except json.JSONDecodeError:
        # Fallback si el modelo no genera JSON válido
        return {
            "variante_a": contenido[:500],
            "variante_b": contenido[500:1000] if len(contenido) > 500 else contenido,
            "hashtags": ["#marketing", "#negocio", "#emprendimiento"]
        }


def generar_caption_instagram(
    tema: str,
    producto: str,
    post_facebook: str,
    modelo: str = "qwen3:7b"
) -> str:
    """
    Genera un caption de Instagram adaptado del post de Facebook.
    Instagram permite hasta 2200 caracteres pero los mejores captions son más cortos.
    """
    cliente = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    
    prompt = f"""Adapta este contenido de Facebook para Instagram:

PRODUCTO: {producto}
TEMA: {tema}
POST FACEBOOK:
{post_facebook[:600]}

Para Instagram:
- Máximo 150 palabras en el cuerpo principal
- Primer párrafo IMPACTANTE (primeras 125 chars son las que se ven sin expandir)
- Saltos de línea entre párrafos (3-4 párrafos)
- Al final: 15-20 hashtags relevantes (mezclar populares y nicho)
- Incluir emojis estratégicos (máximo 5)

Devuelve SOLO el texto del caption listo para copiar."""
    
    respuesta = cliente.chat.completions.create(
        model=modelo,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600,
        temperature=0.8
    )
    
    return respuesta.choices[0].message.content.strip()


def generar_campana(
    tema: str,
    producto: str,
    cantidad_posts: int = 5,
    tonos: list = None
) -> list[dict]:
    """
    Genera una campaña completa de múltiples posts.
    
    Args:
        tema: Tema general de la campaña
        producto: Producto o servicio
        cantidad_posts: Número de posts a generar
        tonos: Lista de tonos para rotar
    """
    if tonos is None:
        tonos = ["profesional", "educativo", "inspiracional", "casual", "urgente"]
    
    print(f">> Generando campaña para '{producto}' — tema: '{tema}'")
    print(f"   {cantidad_posts} posts, tonos: {', '.join(tonos[:cantidad_posts])}")
    
    campana = []
    
    for i in range(cantidad_posts):
        tono = tonos[i % len(tonos)]
        print(f"\n  Post {i+1}/{cantidad_posts} ({tono})...")
        
        inicio = time.time()
        
        # Generar post Facebook
        post_fb = generar_post_facebook(tema, producto, tono)
        
        # Generar caption Instagram basado en variante A
        caption_ig = generar_caption_instagram(tema, producto, post_fb.get("variante_a", ""))
        
        campana.append({
            "numero": i + 1,
            "tono": tono,
            "facebook": post_fb,
            "instagram_caption": caption_ig,
            "generado_en": time.time()
        })
        
        print(f"     [OK] Generado en {time.time()-inicio:.1f}s")
    
    return campana
```

---

## 22.4 Script 2 — Publicador via Meta Graph API

```python
# scripts/meta_publisher.py
"""
Publica contenido en Facebook Page e Instagram Business usando Meta Graph API.
Documentación oficial: https://developers.facebook.com/docs/graph-api
"""
import json
import requests
from pathlib import Path
from datetime import datetime


def cargar_secrets() -> dict:
    secrets_path = Path(__file__).parent.parent / "config" / "secrets.json"
    with open(secrets_path) as f:
        return json.load(f)


def publicar_en_facebook(texto: str, programar_en: datetime = None) -> dict:
    """
    Publica un post en la Facebook Page.
    
    Args:
        texto: Contenido del post
        programar_en: Si se proporciona, programa el post para esa fecha/hora
    
    Returns:
        dict con 'post_id' y 'url' si fue exitoso
    """
    secrets = cargar_secrets()
    meta_cfg = secrets["meta"]
    
    endpoint = f"https://graph.facebook.com/v18.0/{meta_cfg['page_id']}/feed"
    
    payload = {
        "message": texto,
        "access_token": meta_cfg["page_access_token"]
    }
    
    if programar_en:
        # Programación requiere que la fecha sea entre 10 min y 30 días en el futuro
        timestamp = int(programar_en.timestamp())
        payload["published"] = False
        payload["scheduled_publish_time"] = timestamp
    
    resp = requests.post(endpoint, data=payload, timeout=30)
    resultado = resp.json()
    
    if "id" in resultado:
        post_id = resultado["id"]
        url_post = f"https://www.facebook.com/{post_id}"
        print(f"  [OK] Post en Facebook: {url_post}")
        return {"post_id": post_id, "url": url_post, "plataforma": "facebook"}
    else:
        error = resultado.get("error", {})
        print(f"  [ERROR] Error Facebook: {error.get('message', 'Error desconocido')}")
        return {"error": error, "plataforma": "facebook"}


def publicar_en_instagram(caption: str, imagen_url: str = None) -> dict:
    """
    Publica un post de texto en Instagram Business.
    
    NOTA: Instagram requiere una imagen para posts en el feed regular.
    Para posts solo de texto, use Instagram Stories (requiere imagen o video).
    Este método usa la API de Reels/Carousel con imagen opcional.
    
    Args:
        caption: Texto del caption con hashtags
        imagen_url: URL pública de la imagen a publicar (requerida para feed)
    
    Returns:
        dict con 'post_id' si fue exitoso
    """
    secrets = cargar_secrets()
    meta_cfg = secrets["meta"]
    
    ig_account_id = meta_cfg["instagram_account_id"]
    access_token = meta_cfg["page_access_token"]
    
    # Paso 1: Crear el media container
    if imagen_url:
        container_payload = {
            "image_url": imagen_url,
            "caption": caption,
            "access_token": access_token
        }
    else:
        # Sin imagen: publicar como Reel de texto (usando imagen placeholder)
        print("  [WARN]  Instagram requiere imagen para posts en feed")
        print("     Proporcione imagen_url para publicar en Instagram")
        return {"error": "imagen_url_requerida", "plataforma": "instagram"}
    
    resp1 = requests.post(
        f"https://graph.facebook.com/v18.0/{ig_account_id}/media",
        data=container_payload,
        timeout=30
    )
    data1 = resp1.json()
    
    if "id" not in data1:
        error = data1.get("error", {})
        print(f"  [ERROR] Error creando container IG: {error.get('message', '')}")
        return {"error": error, "plataforma": "instagram"}
    
    container_id = data1["id"]
    
    # Paso 2: Publicar el container
    resp2 = requests.post(
        f"https://graph.facebook.com/v18.0/{ig_account_id}/media_publish",
        data={"creation_id": container_id, "access_token": access_token},
        timeout=30
    )
    data2 = resp2.json()
    
    if "id" in data2:
        post_id = data2["id"]
        print(f"  [OK] Post en Instagram: ID={post_id}")
        return {"post_id": post_id, "plataforma": "instagram"}
    else:
        error = data2.get("error", {})
        print(f"  [ERROR] Error publicando en IG: {error.get('message', '')}")
        return {"error": error, "plataforma": "instagram"}


def guardar_campana_local(campana: list, nombre: str = "campana"):
    """Guarda el contenido generado localmente antes de publicar."""
    output_path = Path("output") / f"{nombre}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(campana, f, ensure_ascii=False, indent=2)
    
    print(f"  [OK] Campaña guardada localmente: {output_path}")
    return str(output_path)
```

---

## 22.5 Orquestador Principal

```python
# main.py
"""
Orquestador principal del pipeline de ventas.
"""
import json
import sys
from pathlib import Path
from scripts.content_generator import generar_campana
from scripts.meta_publisher import publicar_en_facebook, guardar_campana_local


def ejecutar_campana(
    tema: str,
    producto: str,
    cantidad_posts: int = 3,
    publicar: bool = False,
    variante: str = "a"  # "a" o "b"
):
    """
    Pipeline completo: generar → guardar → (opcional) publicar
    """
    print(f"""
═══════════════════════════════════════════════
  PIPELINE DE CONTENIDO PARA REDES SOCIALES
  Producto: {producto}
  Tema: {tema}
  Posts: {cantidad_posts}
  Publicar: {'Sí' if publicar else 'No (solo generar)'}
═══════════════════════════════════════════════
""")
    
    # Generar contenido
    campana = generar_campana(tema, producto, cantidad_posts)
    
    # Guardar localmente siempre
    ruta_guardada = guardar_campana_local(campana, nombre=producto.replace(" ", "_"))
    
    # Mostrar preview
    print(f"\n── Preview de la campaña ({len(campana)} posts) ──")
    for post in campana:
        print(f"\n[Post {post['numero']} — tono: {post['tono']}]")
        var = post["facebook"].get(f"variante_{variante}", "")
        print(var[:200] + "..." if len(var) > 200 else var)
        print(f"Hashtags: {' '.join(post['facebook'].get('hashtags', [])[:5])}")
    
    # Publicar si se solicitó
    if publicar:
        print(f"\n── Publicando {len(campana)} posts en Facebook ──")
        print("[WARN]  Los posts se publicarán inmediatamente. ¿Continuar? (s/n): ", end="")
        confirmacion = input().strip().lower()
        
        if confirmacion == "s":
            for post in campana:
                var_texto = post["facebook"].get(f"variante_{variante}", "")
                hashtags = " ".join(post["facebook"].get("hashtags", []))
                texto_completo = f"{var_texto}\n\n{hashtags}"
                
                resultado = publicar_en_facebook(texto_completo)
                post["publicado_facebook"] = resultado
            
            # Actualizar el archivo con IDs de posts publicados
            with open(ruta_guardada, "w", encoding="utf-8") as f:
                json.dump(campana, f, ensure_ascii=False, indent=2)
            
            print(f"\n[OK] Campaña publicada y actualizada en: {ruta_guardada}")
        else:
            print("ℹ️  Publicación cancelada — contenido guardado localmente")
    
    return campana


if __name__ == "__main__":
    # Ejemplo de uso
    ejecutar_campana(
        tema="Los beneficios de la inteligencia artificial para pequeñas empresas",
        producto="Consultoría AI para Pymes",
        cantidad_posts=3,
        publicar=False  # Cambiar a True cuando esté listo para publicar
    )
```

```bash
# Instalar flask y ejecutar
source ~/venvs/dev/bin/activate
python main.py
```

---

## 22.6 Limpieza Post-Pipeline

```bash
# El pipeline de sales funnel no usa contenedores Docker GPU
# Solo detener Ollama si no se necesita más

sudo systemctl stop ollama
pwr-15w
sync && echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
echo "[OK] Pipeline de sales funnel detenido"
```

---

## 22.7 Verificación Final

```bash
echo "╔═══════════════════════════════════════════════════════╗"
echo "║    VERIFICACIÓN CAPÍTULO 22 — SALES FUNNEL              ║"
echo "╚═══════════════════════════════════════════════════════╝"

echo ""
echo "── Ollama ──"
curl -sf http://localhost:11434/api/version > /dev/null && echo "  [OK] Activo" || echo "  ○  Offline"
ollama list 2>/dev/null | grep -q "qwen3" && echo "  [OK] qwen3:7b disponible" || echo "  ○  Instalar: ollama pull qwen3:7b"

echo ""
echo "── Configuración Meta ──"
[ -f ~/projects/sales-funnel/config/secrets.json ] \
  && echo "  [OK] secrets.json configurado" \
  || echo "  ○  Crear config/secrets.json con Page Access Token"

echo ""
echo "── Scripts ──"
for s in content_generator.py meta_publisher.py; do
  [ -f ~/projects/sales-funnel/scripts/$s ] && echo "  [OK] $s" || echo "  ○  $s"
done

echo ""
echo "═════════════════════════════════════════════════════════"
```

---

## 22.8 Escalabilidad y Extensiones

### 22.8.1 Bot de Telegram para Generación y Publicación de Contenido

El pipeline puede integrarse con Telegram para que el usuario solicite la publicación de contenido desde su teléfono, sin acceso directo al Jetson.

**Flujo con N8N** (ver Capítulo 14):

```yaml
Nodo 1 — Telegram Trigger:
  tipo: telegram_trigger
  evento: message_received
  filtro: texto (instrucción de publicación)
  # Ejemplo: "publica post sobre descuento 20% zapatos tenis este fin de semana"

Nodo 2 — Execute Command:
  tipo: execute_command
  comando: |
    python3 ~/projects/sales-funnel/scripts/01_generate_content.py \
      --prompt "{{message_text}}" \
      --output /tmp/post_output.json
  timeout: 60

Nodo 3 — Execute Command:
  tipo: execute_command
  comando: |
    python3 ~/projects/sales-funnel/scripts/02_publish_meta.py \
      --input /tmp/post_output.json
  timeout: 30

Nodo 4 — Send Message:
  tipo: telegram_send_message
  chat_id: {{chat_id}}
  texto: "Publicado en Facebook e Instagram. URL: {{post_url}}"
```

**Flujo con OpenClaw** (ver Capítulo 11A):

```json
"agents": {
  "sales_funnel": {
    "description": "Publica contenido de marketing en redes sociales",
    "command": "python3 ~/projects/sales-funnel/scripts/run_pipeline.py --prompt {{input}}",
    "channels": ["telegram"]
  }
}
```

### 22.8.2 Modo Mixto con OpenRouter

Para campañas de alto impacto donde se requiera mayor creatividad o análisis de mercado:

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
alias funnel-local="USE_LOCAL_LLM=true  python3 ~/projects/sales-funnel/scripts/01_generate_content.py"
alias funnel-cloud="USE_LOCAL_LLM=false python3 ~/projects/sales-funnel/scripts/01_generate_content.py"
```

### 22.8.3 Evaluación de Backend de Inferencia

El pipeline de ventas realiza pocas llamadas al LLM (generación del copy de 1–3 variantes), por lo que la eficiencia de memoria es más importante que el throughput:

| Backend | Ventaja | Desventaja | Recomendación |
|---|---|---|---|
| **Ollama** (qwen3:7b) | Simple, fácil configuración | Carga completa del modelo en RAM | Adecuado |
| **llama.cpp** (qwen3:7b Q4_K_M) | Menor uso de VRAM (~4 GB vs ~5.5 GB) | API compatible pero gestión manual | **Recomendado** si el Jetson corre otros servicios en paralelo |
| **vLLM** | Alto throughput | Overhead innecesario para 1–3 requests | No recomendado para este caso |

> **CONSEJO:** Si el Jetson ejecuta simultáneamente Open WebUI y el pipeline de ventas, use llama.cpp con `qwen3:7b Q4_K_M` para reducir el consumo de VRAM de ~5.5 GB a ~4 GB y dejar más memoria disponible para el resto del sistema.

---

> **Próximo paso:** El Capítulo 23 construye el generador de contenido para LinkedIn con OAuth2 y few-shot prompting basado en el estilo personal del usuario.
