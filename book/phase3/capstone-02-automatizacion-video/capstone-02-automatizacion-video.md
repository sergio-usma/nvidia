# Capstone 02 — Automatización de Contenido en Video con IA

## Introducción

Este capítulo demuestra cómo construir un sistema de producción de contenido en video completamente automatizado sobre el Jetson AGX Orin 64GB — sin intervención humana en el proceso de creación, con costo operativo menor a $1/mes en electricidad.

El caso de uso implementado es el canal **"Daily Prayers"** — videos cortos espirituales de 30–40 segundos, publicados diariamente en YouTube Shorts y TikTok, basados en los Salmos y Proverbios de la Biblia, con voz en español latino, imágenes fotorrealistas generadas con IA y sin afiliación a ninguna religión específica. La arquitectura es genérica y puede adaptarse a cualquier tipo de canal de contenido: recetas de cocina, noticias locales, motivación diaria, tutoriales técnicos, etc.

**Los 7 agentes del sistema:**

| Agente | Función | Herramienta | Modo |
|--------|---------|-------------|------|
| 1 | Generador de scripts | Ollama Qwen3.5-4B | 30W |
| 2 | Generador de imágenes | Stable Diffusion WebUI | MAXN |
| 3 | Narrador TTS + timestamps | kokoro-tts + faster-whisper | 30W |
| 4 | Ensamblador de video | ffmpeg (CPU) | 30W |
| 5 | Publicador YouTube | YouTube Data API v3 | 30W |
| 6 | Publicador TikTok | TikTok Content Posting API | 30W |
| 7 | Reporter de analytics | N8N + Analytics APIs | 30W |

**Parrilla de contenidos:** Salmos y Proverbios intercalados, grupos de 10 versículos consecutivos (cruzando capítulos cuando es necesario). Total: ~241 videos ≈ **8 meses de contenido diario** sin repetir.

**Presupuesto de energía:** $0.003/hora en modo 30W = menos de **$0.90/mes** en electricidad para producir 30 videos.

---

## 32.1 Arquitectura del Pipeline

<!-- INFOGRAFÍA: Arquitectura del Pipeline de 7 Agentes — Daily Prayers — pendiente de diseño gráfico (paleta NVIDIA #0F3D3D / accent #1D9CB8, texto mínimo 10pt, optimizado para KDP Kindle dark/light) -->


```
Google Sheets
  (parrilla: ~241 filas, Salmos+Proverbios intercalados, status=pending)
    ↓
N8N Cron 7:00 AM
  → lee próxima fila status="pending"
  → marca status="generating"
    ↓
FastAPI Pipeline Server :8090
  (orquestador local — N8N lo llama vía 172.18.0.1:8090)
    ↓
  [Etapa 1] Agente 1 — Script Generator (Ollama Qwen3.5-4B)
    → 5–6 escenas: {texto, duración_seg, prompt_imagen, arquetipo_personaje}
    → título ≤20 chars, emoji
    → guarda metadata.json
    → jetson-clean → libera RAM
    ↓
  [Etapa 2] Agente 2 — Image Generator (SD WebUI API :7860)
    → 1 imagen 608×1080 por escena (upscale a 1080×1920 con ffmpeg)
    → prompt negativo: sin símbolos religiosos
    → rotación automática de arquetipos de diversidad
    → docker stop sdwebui → libera GPU
    ↓
  [Etapa 3] Agente 3 — TTS + Subtítulos
    → kokoro-tts es_e: prayer.mp3
    → faster-whisper: word-level timestamps
    → Python: genera prayer.srt + prayer.ass (blanco, borde negro, 5% margen)
    → docker stop ambos → libera RAM
    ↓
  [Etapa 4] Agente 4 — Video Assembly (ffmpeg, CPU puro)
    → Ken Burns: zoom lento 1.0→1.05 por escena
    → xfade crossfade 0.5s entre escenas
    → overlay prayer.ass (burned-in)
    → output: prayer_social.mp4 (1080×1920, ~35s) + prayer_editable.mp4 (soft subs)
    → actualiza Google Sheets: status="ready"
    ↓
N8N Trigger (status="ready")
  ↓
  [Etapa 5] Agente 5 — YouTube Publisher
    → título: "Junio 29 - <Nombre> <emoji>"
    → descripción auto, #Shorts, 9:16 → detectado como Short automáticamente
    ↓
  [Etapa 6] Agente 6 — TikTok Publisher [REQUIERE VERIFICACIÓN]
    → mismo video, título adaptado
    → actualiza Google Sheets: status="published", yt_url, tt_url
    ↓
N8N Cron 9:00 PM
  [Etapa 7] Analytics Reporter
    → YouTube Analytics API: views, CTR, avg_retention
    → TikTok Analytics API
    → email con reporte diario
```

**Presupuesto de memoria (pipeline 100% secuencial):**

| Etapa | GPU RAM pico | Tiempo |
|-------|-------------|--------|
| Script gen (Ollama 4B) | ~5 GB | ~2 min |
| jetson-clean | 0 GB | 30s |
| Imagen ×5 (SD WebUI) | ~6 GB | ~15 min |
| docker stop SD WebUI | 0 GB | 10s |
| TTS + timestamps | ~3 GB | ~2 min |
| docker stop ×2 | 0 GB | 10s |
| Video ffmpeg (CPU) | 0 GB | ~2 min |
| Publicar (APIs) | 0 GB | ~1 min |
| **Total diario** | **pico 6 GB** | **~22 min** |

---

## 32.2 Preparación del Entorno

### 32.2.1 Dependencias Python

```bash
#
source ~/venvs/llm/bin/activate
pip install \
  google-api-python-client \
  google-auth-httplib2 \
  google-auth-oauthlib \
  fastapi uvicorn \
  gspread oauth2client \
  pillow

echo "[OK] Dependencias instaladas"
```

### 32.2.2 Estructura de Directorios

```bash
# Crear estructura del proyecto Daily Prayers
mkdir -p /data/prayers
mkdir -p ~/projects/daily-prayers/{scripts,config,logs}
mkdir -p ~/projects/daily-prayers/scripts/{agents,utils,workers}

echo "[OK] Directorios creados"
ls ~/projects/daily-prayers/
```

### 32.2.3 Google Cloud — Habilitar APIs

Las APIs de Google requieren una cuenta de Google Cloud (gratuita hasta ciertos límites):

```
1. Ir a: console.cloud.google.com
2. Crear proyecto: "daily-prayers-jetson"
3. Habilitar las siguientes APIs:
   - YouTube Data API v3
   - YouTube Analytics API v2
   - Google Sheets API
4. Crear credenciales:
   - Tipo: OAuth 2.0 (para YouTube upload)
   - Tipo: Service Account (para Google Sheets)
5. Descargar:
   - client_secrets.json → ~/projects/daily-prayers/config/
   - service_account.json → ~/projects/daily-prayers/config/
```

```bash
# Verificar que los archivos de credenciales existen
ls -la ~/projects/daily-prayers/config/
# Salida esperada:
# client_secrets.json   ← YouTube OAuth2
# service_account.json  ← Google Sheets Service Account
```

---

## 32.3 Parrilla de Contenidos en Google Sheets

### 32.3.1 Datos de Versículos (Salmos + Proverbios)

```python
#!/usr/bin/env python3
"""
generate_content_calendar.py — Genera la parrilla completa en Google Sheets
Grupos de 10 versículos consecutivos, Salmos y Proverbios intercalados.
"""
import json
from pathlib import Path

# Número de versículos por capítulo
# Salmos (150 capítulos)
SALMOS_VERSES = {
    1:6, 2:12, 3:8, 4:8, 5:12, 6:10, 7:17, 8:9, 9:20, 10:18,
    11:7, 12:8, 13:6, 14:7, 15:5, 16:11, 17:15, 18:50, 19:14, 20:9,
    21:13, 22:31, 23:6, 24:10, 25:22, 26:12, 27:14, 28:9, 29:11, 30:12,
    31:24, 32:11, 33:22, 34:22, 35:28, 36:12, 37:40, 38:22, 39:13, 40:17,
    41:13, 42:11, 43:5, 44:26, 45:17, 46:11, 47:9, 48:14, 49:20, 50:23,
    51:19, 52:9, 53:6, 54:7, 55:23, 56:13, 57:11, 58:11, 59:17, 60:12,
    61:8, 62:12, 63:11, 64:10, 65:13, 66:20, 67:7, 68:35, 69:36, 70:5,
    71:24, 72:20, 73:28, 74:23, 75:10, 76:12, 77:20, 78:72, 79:13, 80:19,
    81:16, 82:8, 83:18, 84:12, 85:13, 86:17, 87:7, 88:18, 89:52, 90:17,
    91:16, 92:15, 93:5, 94:23, 95:11, 96:13, 97:12, 98:9, 99:9, 100:5,
    101:8, 102:28, 103:22, 104:35, 105:45, 106:48, 107:43, 108:13, 109:31, 110:7,
    111:10, 112:10, 113:9, 114:8, 115:18, 116:19, 117:2, 118:29, 119:176, 120:7,
    121:8, 122:9, 123:4, 124:8, 125:5, 126:6, 127:5, 128:6, 129:8, 130:8,
    131:3, 132:18, 133:3, 134:3, 135:21, 136:26, 137:9, 138:8, 139:24, 140:13,
    141:10, 142:7, 143:12, 144:15, 145:21, 146:10, 147:20, 148:14, 149:9, 150:6,
}

# Proverbios (31 capítulos)
PROVERBIOS_VERSES = {
    1:33, 2:22, 3:35, 4:27, 5:23, 6:35, 7:27, 8:36, 9:18, 10:32,
    11:31, 12:28, 13:25, 14:35, 15:33, 16:33, 17:28, 18:24, 19:29, 20:30,
    21:31, 22:29, 23:35, 24:34, 25:28, 26:28, 27:27, 28:28, 29:27, 30:33,
    31:31,
}

def agrupar_en_bloques_de_10(libro_name: str, verses_dict: dict) -> list:
    """Genera lista de grupos de 10 versículos consecutivos cruzando capítulos."""
    # Construir lista lineal de (capitulo, versiculo)
    todos = []
    for cap in sorted(verses_dict.keys()):
        for v in range(1, verses_dict[cap] + 1):
            todos.append((cap, v))

    grupos = []
    for i in range(0, len(todos), 10):
        bloque = todos[i:i+10]
        if not bloque:
            continue

        cap_inicio, v_inicio = bloque[0]
        cap_fin, v_fin = bloque[-1]

        if cap_inicio == cap_fin:
            ref = f"{libro_name} {cap_inicio}:{v_inicio}–{v_fin}"
        else:
            ref = f"{libro_name} {cap_inicio}:{v_inicio} – {cap_fin}:{v_fin}"

        grupos.append({
            "libro": libro_name,
            "referencia": ref,
            "capitulo_inicio": cap_inicio,
            "versiculo_inicio": v_inicio,
            "capitulo_fin": cap_fin,
            "versiculo_fin": v_fin,
            "num_versiculos": len(bloque)
        })

    return grupos

def generar_parrilla_intercalada() -> list:
    """Intercala grupos de Salmos y Proverbios día a día."""
    salmos = agrupar_en_bloques_de_10("Salmos", SALMOS_VERSES)
    proverbios = agrupar_en_bloques_de_10("Proverbios", PROVERBIOS_VERSES)

    parrilla = []
    max_len = max(len(salmos), len(proverbios))
    for i in range(max_len):
        if i < len(salmos):
            parrilla.append({"fila": len(parrilla) + 1, **salmos[i]})
        if i < len(proverbios):
            parrilla.append({"fila": len(parrilla) + 1, **proverbios[i]})

    return parrilla

if __name__ == "__main__":
    parrilla = generar_parrilla_intercalada()
    print(f"Total de videos en la parrilla: {len(parrilla)}")
    print(f"Salmos: {sum(1 for p in parrilla if p['libro']=='Salmos')}")
    print(f"Proverbios: {sum(1 for p in parrilla if p['libro']=='Proverbios')}")
    print(f"Duración estimada: {len(parrilla)} días ≈ {len(parrilla)/30:.1f} meses")
    print("\nPrimeros 5 grupos:")
    for p in parrilla[:5]:
        print(f"  Fila {p['fila']}: {p['referencia']} ({p['num_versiculos']} versículos)")

    # Guardar para importar a Google Sheets
    output_path = Path.home() / "projects/daily-prayers/config/parrilla.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(parrilla, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Parrilla guardada en {output_path}")
```

```
# Salida esperada al ejecutar
Total de videos en la parrilla: 241
Salmos: 150
Proverbios: 91
Duración estimada: 241 días ≈ 8.0 meses

Primeros 5 grupos:
  Fila 1: Salmos 1:1–6 (6 versículos — cap 1 completo + 4 del cap 2)
  Fila 2: Proverbios 1:1–10 (10 versículos)
  Fila 3: Salmos 2:5 – 3:5 (10 versículos)
  Fila 4: Proverbios 1:11–20 (10 versículos)
  Fila 5: Salmos 3:6 – 4:8 (10 versículos)
```

### 32.3.2 Importar Parrilla a Google Sheets

```python
#!/usr/bin/env python3
"""
setup_google_sheets.py — Crea y llena la hoja de cálculo de contenidos.
"""
import json
from pathlib import Path
import gspread
from oauth2client.service_account import ServiceAccountCredentials

CONFIG_DIR = Path.home() / "projects/daily-prayers/config"

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

def crear_parrilla_sheets():
    # Autenticar con Service Account
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        str(CONFIG_DIR / "service_account.json"), SCOPES
    )
    cliente = gspread.authorize(creds)

    # Crear o abrir la hoja
    try:
        hoja = cliente.open("Daily Prayers — Parrilla de Contenidos")
        print("Hoja existente encontrada.")
    except gspread.SpreadsheetNotFound:
        hoja = cliente.create("Daily Prayers — Parrilla de Contenidos")
        print("[OK] Nueva hoja creada.")

    sheet = hoja.sheet1

    # Encabezados
    encabezados = [
        "id", "libro", "referencia", "cap_inicio", "ver_inicio",
        "cap_fin", "ver_fin", "titulo", "emoji", "status",
        "fecha_programada", "carpeta_local", "youtube_url",
        "tiktok_url", "yt_views", "tt_views", "generado_en"
    ]
    sheet.update("A1", [encabezados])

    # Formatear encabezado (negrita, color)
    sheet.format("A1:Q1", {
        "textFormat": {"bold": True},
        "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.6},
        "horizontalAlignment": "CENTER"
    })

    # Cargar parrilla generada
    parrilla = json.loads((CONFIG_DIR / "parrilla.json").read_text())

    # Llenar filas
    filas = []
    for p in parrilla:
        filas.append([
            p["fila"],
            p["libro"],
            p["referencia"],
            p["capitulo_inicio"],
            p["versiculo_inicio"],
            p["capitulo_fin"],
            p["versiculo_fin"],
            "",          # título — lo genera el Agente 1
            "",          # emoji — lo genera el Agente 1
            "pending",   # status inicial
            "",          # fecha_programada
            "",          # carpeta_local
            "",          # youtube_url
            "",          # tiktok_url
            "",          # yt_views
            "",          # tt_views
            "",          # generado_en
        ])

    sheet.update("A2", filas)
    print(f"[OK] {len(filas)} filas cargadas en Google Sheets")
    print(f"   URL: {hoja.url}")
    return hoja.url

if __name__ == "__main__":
    url = crear_parrilla_sheets()
    print(f"\nAbrir en el navegador: {url}")
```

```bash
# Ejecutar los scripts de setup
source ~/venvs/llm/bin/activate
python3 ~/projects/daily-prayers/scripts/generate_content_calendar.py
python3 ~/projects/daily-prayers/scripts/setup_google_sheets.py
```

### 32.3.3 Obtener el Texto de los Versículos (API Biblia)

El texto de los versículos se puede rellenar automáticamente usando una API de la Biblia. La columna `versos_texto` en Google Sheets debe tener el texto en español antes de que el Agente 1 lo procese:

```python
# scripts/fetch_bible_text.py — Obtiene texto de versículos en español (RVR1960)
# API primaria: getbible.net (gratuita, sin clave, soporte RVR1960)
# API de respaldo: api.esv.org en inglés (requiere clave gratuita, solo inglés)
# API alternativa de respaldo: scripture.api.bible (requiere clave gratuita)
import requests
import time

# ⚠ Reemplaza con tu clave si usas scripture.api.bible como primaria
API_BIBLE_KEY = ""  # obtener en scripture.api.bible → registrar app gratuita

def obtener_texto_getbible(libro: str, cap_inicio: int, ver_inicio: int,
                           cap_fin: int, ver_fin: int) -> str:
    """Primario: getbible.net — gratuito, sin clave, español RVR1960."""
    abbrev = "rvr1960"
    try:
        url = f"https://getbible.net/v2/{abbrev}/{cap_inicio}.json"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            chapter = resp.json()
            versos = []
            for v_num, v_data in chapter.get("verses", {}).items():
                vn = int(v_num)
                if cap_inicio == cap_fin:
                    if ver_inicio <= vn <= ver_fin:
                        versos.append(v_data.get("verse", ""))
                else:
                    versos.append(v_data.get("verse", ""))
            return " ".join(versos).strip()
    except Exception as e:
        print(f"  [WARN] getbible.net error: {e}")
    return ""

def obtener_texto_api_bible(referencia: str) -> str:
    """Respaldo: scripture.api.bible — requiere API key gratuita."""
    if not API_BIBLE_KEY:
        return ""
    RVR_BIBLE_ID = "b32b9d1b64b4ef29-01"  # RVR1960 en scripture.api.bible
    url = f"https://api.scripture.api.bible/v1/bibles/{RVR_BIBLE_ID}/passages/{referencia}"
    headers = {"api-key": API_BIBLE_KEY}
    try:
        resp = requests.get(url, headers=headers, params={"content-type": "text"}, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("data", {}).get("content", "")
    except Exception as e:
        print(f"  [WARN] api.bible error: {e}")
    return ""

def obtener_texto(libro: str, cap_inicio: int, ver_inicio: int,
                  cap_fin: int, ver_fin: int) -> str:
    """Intenta primario → respaldo → texto de placeholder."""
    texto = obtener_texto_getbible(libro, cap_inicio, ver_inicio, cap_fin, ver_fin)
    if texto:
        return texto
    # Respaldo con api.bible si hay clave
    ref = f"{libro}.{cap_inicio}.{ver_inicio}-{libro}.{cap_fin}.{ver_fin}"
    texto = obtener_texto_api_bible(ref)
    if texto:
        return texto
    # Placeholder que el Agente 1 maneja con gracia
    return f"({libro} {cap_inicio}:{ver_inicio}–{cap_fin}:{ver_fin})"
```

> **NOTA:** `getbible.net` es gratuito y no requiere registro. Si la API cambia de URL o formato, verifique `https://getbible.net/api` para la versión actualizada. `scripture.api.bible` ofrece una clave gratuita con 5.000 peticiones/mes.

---

## 32.4 Agente 1 — Generador de Scripts

El Agente 1 toma los versículos del día y genera el guión completo de la plegaria: texto de cada escena, duración, prompt de imagen y arquetipo de personaje.

### 32.4.1 Sistema de Diversidad de Personajes

```python
# config/archetypes.py — 120 arquetipos rotativos para diversidad de representación
# Cubre: todas las edades (5-80+), razas/etnias, géneros, contextos y situaciones de vida
PERSON_ARCHETYPES = [
    # ── Asia Oriental ──────────────────────────────────────────────────────────
    "a 40-year-old Asian woman sitting peacefully in a park at sunset",
    "a 60-year-old Japanese man meditating in a minimalist room at dawn",
    "a Korean teenage girl looking at the sky from a rooftop at dawn",
    "an Indian boy, 10 years old, reading quietly at a library table",
    "a 30-year-old Chinese woman writing in a journal by a window at night",
    "a 65-year-old Japanese grandmother tending her garden in the morning mist",
    "a Thai monk, 50 years old, walking barefoot on a stone path at sunrise",
    "a 22-year-old Filipino man volunteering at a community kitchen",
    "an Indian woman in her 35s in a colorful sari, hands joined in prayer",
    "a 45-year-old Vietnamese father helping his daughter with homework",
    # ── África y Diáspora Africana ─────────────────────────────────────────────
    "a 20-year-old Black man working at a desk in a modern office",
    "a 55-year-old African woman in colorful traditional clothing, outdoors",
    "an elderly Black couple holding hands on a porch swing",
    "an African American father and young son at home, sharing a moment",
    "a 32-year-old Kenyan woman smiling while harvesting tea leaves at dawn",
    "a Nigerian grandfather, 78 years old, seated under a large tree",
    "a 27-year-old Afro-Caribbean woman dancing with joy at a community event",
    "an Ethiopian boy, 12 years old, with a book under a blue sky",
    "a 48-year-old Ghanaian man praying in a small community church",
    "a South African woman, 38, hugging her teenage daughter at home",
    # ── América Latina y Caribe ────────────────────────────────────────────────
    "a Hispanic girl, 8 years old, playing in a sunny garden",
    "a white-haired Latin American grandfather walking in a wheat field",
    "a 45-year-old Brazilian man embracing his elderly mother indoors",
    "a 25-year-old Mexican woman lighting a candle in a church at dusk",
    "a Colombian family of four sitting around a dinner table, laughing",
    "a 70-year-old Peruvian woman in traditional Andean clothing at a market",
    "a teenage boy from Argentina sitting on a hillside watching the horizon",
    "a 33-year-old Chilean mother reading a bedtime story to her child",
    "a Cuban musician, 55 years old, playing guitar on a porch at sunset",
    "a 19-year-old Venezuelan student studying by candlelight",
    # ── Europa y América del Norte ─────────────────────────────────────────────
    "a 35-year-old white man kneeling by a river in a forest",
    "a diverse group of young friends sitting together at twilight outdoors",
    "a 28-year-old Italian woman holding a rosary in a cathedral",
    "a 50-year-old German farmer at sunrise, looking over a golden field",
    "an Irish grandfather, 72, sitting by a fireplace with a cup of tea",
    "a 15-year-old American girl writing in her diary on her bedroom floor",
    "a 42-year-old French man in a busy café, eyes closed, a moment of calm",
    "a Polish grandmother, 68, kneeling in a snow-covered church courtyard",
    "a 30-year-old Canadian Indigenous man standing by a mountain lake",
    "a 58-year-old Russian woman tending icons on a shelf at home",
    # ── Oriente Medio y Asia Central ──────────────────────────────────────────
    "a 30-year-old Middle Eastern woman with eyes closed, hands together",
    "a 28-year-old Arab man laughing with colleagues in a café",
    "a Turkish elderly woman, 74, sitting quietly in a courtyard at dusk",
    "a 25-year-old Iranian student looking out a university window",
    "an Afghan shepherd, 55 years old, standing on a hill at sunrise",
    "a 38-year-old Lebanese mother and her daughter walking in a blooming garden",
    "a 45-year-old Pakistani businessman pausing to pray in his office",
    "a Syrian boy, 9 years old, drawing on paper at a refugee learning center",
    "an Israeli grandmother, 77, lighting Shabbat candles at a kitchen table",
    "a 32-year-old Jordanian woman smiling as she bakes bread at home",
    # ── Pueblos Indígenas y Pacífico ──────────────────────────────────────────
    "a Native American woman in her 40s standing in a mountain landscape",
    "a young Polynesian mother holding her baby in a tropical garden",
    "a 30-year-old Canadian Indigenous man standing by a mountain lake",
    "a Maori elder, 68, carving wood in a quiet workshop",
    "a 20-year-old Aboriginal Australian woman looking at the stars at night",
    "a Navajo grandfather, 80, wrapping himself in a blanket by a fire",
    "a Hawaiian fisherman, 44, standing on a boat at dawn",
    "a 16-year-old Inuit girl sitting in the snow looking at the northern lights",
    "a Māori family group smiling together outside their communal meeting house",
    "a 35-year-old Amazonian Indigenous man with his young son in the forest",
    # ── Personas Mayores (60+) ────────────────────────────────────────────────
    "a 75-year-old white-haired woman sitting in a rocking chair by a window",
    "an elderly Asian woman and a European man sitting together on a bench",
    "a 80-year-old Black man with gentle eyes, hands clasped in his lap",
    "a 67-year-old Latina woman tending flowers in a small sunny garden",
    "an elderly couple of mixed races, holding hands while watching the sunset",
    "a 70-year-old South Asian woman sitting cross-legged on a floor mat",
    "a 78-year-old Middle Eastern man with a long white beard, smiling softly",
    "a 65-year-old Native American woman weaving a blanket by a fire",
    "a 72-year-old Italian woman cooking in a sunlit kitchen",
    "an elderly Japanese couple bowing to each other at a temple gate",
    # ── Niños y Jóvenes (5-18) ────────────────────────────────────────────────
    "a group of children of different ethnicities playing together in a park",
    "a 5-year-old child with eyes wide open looking at a butterfly in a garden",
    "a 10-year-old Black girl drawing with crayons at a kitchen table",
    "a 14-year-old Asian boy practicing piano in a warm living room",
    "a 7-year-old Hispanic boy kneeling beside his bed saying his prayers",
    "a group of diverse middle-school students laughing during lunch outdoors",
    "a 16-year-old girl of mixed ethnicity painting at an easel by a window",
    "a 12-year-old South Asian boy flying a kite in an open field",
    "three young children of different backgrounds sharing a book on grass",
    "a 9-year-old Indigenous girl helping her grandmother pick vegetables",
    # ── Momentos Cotidianos Universales ───────────────────────────────────────
    "a 25-year-old mixed-race young woman standing on a beach at sunrise",
    "a 43-year-old nurse sitting in a quiet corridor during a long shift",
    "a 37-year-old teacher writing on a blackboard in an empty classroom",
    "a 29-year-old farmer watching the first light touch his crops",
    "a 50-year-old construction worker taking a break, looking at the sky",
    "a 34-year-old single mother reading a story to her sleeping toddler",
    "a 26-year-old street artist finishing a mural in the early morning",
    "a 40-year-old firefighter kneeling in prayer after a long night shift",
    "a 55-year-old doctor resting her head in her hands between patients",
    "a 31-year-old man sitting alone on a park bench, a moment of stillness",
    # ── Conexión y Comunidad ──────────────────────────────────────────────────
    "a multigenerational family of four generations gathered around a table",
    "two elderly women of different backgrounds sharing tea and smiling",
    "a choir of diverse faces singing together in a community hall",
    "a young couple of mixed ethnicities holding hands at a beach at sunset",
    "a circle of people from many cultures sitting together outdoors at dusk",
    "a volunteer group of mixed ages and backgrounds planting trees together",
    "a group of elderly men playing chess in a sunny public park",
    "a family of refugees embracing outside their new home for the first time",
    "a street corner preacher, 60s, speaking quietly to a small, attentive crowd",
    "a hospital room: an elderly patient and a young nurse sharing a quiet smile",
    # ── Oraciones y Espiritualidad ────────────────────────────────────────────
    "a 50-year-old woman kneeling in prayer beside a candle-lit altar at home",
    "a man of 40 with open palms raised toward the morning sky",
    "a 33-year-old woman sitting in the pew of an empty sunlit church",
    "a Buddhist nun, 60, raking stones in a serene garden",
    "a 25-year-old man lying face down in humble prayer on a stone floor",
    "a grandmother and granddaughter bowing their heads together at a table",
    "a 45-year-old woman lighting incense sticks in a small home shrine",
    "a lone figure of a man standing at the edge of a cliff facing the sunrise",
    "a 38-year-old woman sitting cross-legged on a rooftop at dusk, eyes closed",
    "a 70-year-old man with tears of gratitude streaming down his face, smiling",
]

def get_next_archetype(used_count: int) -> str:
    """Devuelve el siguiente arquetipo en la rotación cíclica."""
    return PERSON_ARCHETYPES[used_count % len(PERSON_ARCHETYPES)]
```

### 32.4.2 Prompt del Generador de Scripts

```python
SCRIPT_PROMPT_TEMPLATE = """Eres un escritor espiritual experto en plegarias universales.

VERSÍCULOS FUENTE:
{referencia}
{versos_texto}

INSTRUCCIONES:
- Crea una plegaria breve e inspiradora de 30–40 segundos de duración total al leerla en voz alta
- Divide la plegaria en 5 escenas (mínimo) a 6 escenas (máximo)
- Cada escena dura entre 5 y 7 segundos
- La plegaria es universal: válida para cualquier persona que crea en un poder superior, sin importar su religión o denominación
- NO menciones ninguna religión específica, ningún nombre de santos, ninguna denominación
- NO uses palabras como "cristiano", "católico", "judío", "islámico", "buda", etc.
- El tono es cálido, esperanzador, íntimo y sincero — como si hablaras directamente al corazón
- El texto debe ser en español latino, sin errores ortográficos

PERSONAJE PARA LAS IMÁGENES: {arquetipo}

Responde ÚNICAMENTE con este JSON (sin markdown, sin explicaciones):
{{
  "titulo": "<máximo 20 caracteres, describe el tema central>",
  "emoji": "<un solo emoji que represente el tema>",
  "escenas": [
    {{
      "num": 1,
      "texto": "<texto de la escena, máximo 25 palabras>",
      "duracion_seg": 6,
      "prompt_imagen": "<prompt en inglés, fotorrealista, {arquetipo}, paisaje o lugar cotidiano, {estilo_imagen}>",
      "negativo": "cross, crucifix, bible, church, star of david, crescent moon, lotus, om symbol, rosary, saints, religious icons, cartoon, anime, deformed, watermark, text, blur"
    }}
  ]
}}"""

IMAGEN_STYLE = "photorealistic, cinematic lighting, 8k quality, warm tones, peaceful atmosphere, natural environment, no religious symbols"
```

### 32.4.3 Script del Agente 1

```python
#!/usr/bin/env python3
"""
agent_01_script_generator.py — Genera el guión de la plegaria del día.
Motor: Ollama Qwen3.5-4B (bajo consumo, suficiente para generación de texto estructurado)
"""
import json
import requests
import subprocess
import time
from pathlib import Path
from datetime import datetime
from config.archetypes import get_next_archetype

OLLAMA_URL = "http://localhost:11434"
CONFIG_DIR = Path.home() / "projects/daily-prayers/config"
PRAYERS_DIR = Path("/data/prayers")

def obtener_modelo_ollama():
    """Asegura que el modelo esté disponible y lo carga."""
    modelos = requests.get(f"{OLLAMA_URL}/api/tags").json()
    nombres = [m["name"] for m in modelos.get("models", [])]
    if not any("qwen3.5" in n for n in nombres):
        print("Descargando Qwen3.5:4b (primera vez)...")
        subprocess.run(["ollama", "pull", "qwen3.5:4b"], check=True)
    # Asegurar que Ollama está corriendo
    subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)

def generar_script(fila: dict, arquetipo: str) -> dict:
    """Llama a Ollama y retorna el JSON del guión."""
    from config.prompt_templates import SCRIPT_PROMPT_TEMPLATE, IMAGEN_STYLE

    prompt = SCRIPT_PROMPT_TEMPLATE.format(
        referencia=fila["referencia"],
        versos_texto=fila.get("versos_texto", "(versículos no disponibles — usar los de la referencia)"),
        arquetipo=arquetipo,
        estilo_imagen=IMAGEN_STYLE
    )

    resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": "qwen3.5:4b",
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 2000}
        },
        timeout=180
    )
    resp.raise_for_status()
    texto = resp.json()["response"].strip()

    # Limpiar posible markdown del JSON
    if "```json" in texto:
        texto = texto.split("```json")[1].split("```")[0].strip()
    elif "```" in texto:
        texto = texto.split("```")[1].split("```")[0].strip()

    return json.loads(texto)

def crear_carpeta_proyecto(titulo: str) -> Path:
    """Crea la carpeta del proyecto con el formato AAAA.DD.MM_titulo."""
    ahora = datetime.now()
    titulo_clean = titulo.lower().replace(" ", "-")[:20]
    titulo_clean = "".join(c for c in titulo_clean if c.isalnum() or c == "-")
    nombre_carpeta = f"{ahora.year}.{ahora.day:02d}.{ahora.month:02d}_{titulo_clean}"
    carpeta = PRAYERS_DIR / nombre_carpeta
    for sub in ["images", "audio", "subtitles", "video"]:
        (carpeta / sub).mkdir(parents=True, exist_ok=True)
    return carpeta

def ejecutar(fila: dict, indice_arquetipo: int) -> dict:
    """Ejecuta el Agente 1 y retorna la metadata completa del proyecto."""
    print(f"[Agente 1] Procesando: {fila['referencia']}")

    obtener_modelo_ollama()
    arquetipo = get_next_archetype(indice_arquetipo)
    print(f"  Arquetipo de personaje: {arquetipo[:60]}...")

    script = generar_script(fila, arquetipo)
    print(f"  Título generado: '{script['titulo']}' {script['emoji']}")
    print(f"  Escenas: {len(script['escenas'])}")

    carpeta = crear_carpeta_proyecto(script["titulo"])
    print(f"  Carpeta: {carpeta}")

    # Guardar metadata completa
    metadata = {
        "fila_id": fila["fila"],
        "referencia": fila["referencia"],
        "libro": fila["libro"],
        "titulo": script["titulo"],
        "emoji": script["emoji"],
        "arquetipo": arquetipo,
        "carpeta": str(carpeta),
        "escenas": script["escenas"],
        "generado_en": datetime.now().isoformat(),
        "status": "script_done"
    }

    with open(carpeta / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # Detener Ollama para liberar RAM antes de la generación de imágenes
    subprocess.run(["pkill", "-f", "ollama serve"], capture_output=True)
    time.sleep(2)
    subprocess.run(["sudo", "sync"])
    subprocess.run(["sudo", "sh", "-c", "echo 3 > /proc/sys/vm/drop_caches"])
    print("  [OK] RAM liberada (Ollama detenido)")

    return metadata
```

---

## 32.5 Agente 2 — Generador de Imágenes (Stable Diffusion WebUI)

### 32.5.1 Instalar Stable Diffusion WebUI

```bash
# Descargar el container SD WebUI para JP 7.2 [REQUIERE VERIFICACIÓN tag r39.2.0]
docker pull dustynv/stable-diffusion-webui:r39.2.0 2>/dev/null \
  || { echo "[REQUIERE VERIFICACIÓN] usando tag alternativo disponible:"; \
       docker search dustynv/stable-diffusion-webui; }

# Iniciar SD WebUI con API habilitada
docker run --runtime nvidia -d \
  --name sdwebui \
  --restart no \
  --network host \
  -v $HOME/.cache/huggingface:/root/.cache/huggingface \
  -v /data/sd-models:/models \
  dustynv/stable-diffusion-webui:r39.2.0 \
  --api --nowebui --port 7860 --no-half-vae

echo -n "Esperando SD WebUI (~3-5 minutos en primer arranque)"
until curl -sf http://localhost:7860/sdapi/v1/options > /dev/null 2>&1; do
  echo -n "."; sleep 15
done
echo " [OK] SD WebUI API activa en :7860"

docker logs sdwebui --follow &
```

> **Modelo recomendado:** Realistic Vision v6.0 (basado en SD 1.5). Descargar desde la pestaña "Models" de la UI, o manualmente colocando el archivo `.safetensors` en `/data/sd-models/Stable-diffusion/`. El modelo puede descargarse desde Hugging Face (civitai.com también, pero requiere cuenta). Tamaño: ~2 GB.

**Guardrails de generación — parámetros obligatorios para resultados consistentes:**

```python
# En agent_02_image_generator.py — configuración de generación
SD_PARAMS_BASE = {
    "width": 608,
    "height": 1080,                  # vertical 9:16 para Shorts/TikTok
    "steps": 25,
    "cfg_scale": 7,
    "sampler_name": "DPM++ 2M Karras",
    "restore_faces": True,           # evita deformidades faciales
    "tiling": False,
    # Prompt negativo global — aplicado a TODAS las imágenes
    "negative_prompt": (
        "cartoon, anime, painting, drawing, illustration, sketch, unrealistic, "
        "deformed hands, extra fingers, missing fingers, mutated hands, "
        "ugly, disfigured, blurry, low quality, pixelated, "
        "nsfw, nude, explicit, sexual, violent, gore, "
        "religious symbols, crosses, crescent moon, star of david, om symbol, "
        "text, watermark, logo, signature, frame, border"
    ),
}
# NOTA: "restore_faces" activa GFPGAN internamente — evita deformidades
# La proporción 608x1080 se escala a 1080x1920 con ffmpeg en el Agente 4
```

```bash
# Verificar modelo cargado
curl -s http://localhost:7860/sdapi/v1/options \
  | python3 -c "import sys,json; opts=json.load(sys.stdin); print('Modelo activo:', opts.get('sd_model_checkpoint','?'))"
```

### 32.5.2 Script del Agente 2

```python
#!/usr/bin/env python3
"""
agent_02_image_generator.py — Genera imágenes fotorrealistas via SD WebUI API.
Una imagen por escena (5–6 imágenes). Diversidad garantizada por arquetipo.
"""
import requests
import base64
import json
import time
import subprocess
from pathlib import Path

SDWEBUI_URL = "http://localhost:7860"

# Configuración de generación
SD_CONFIG = {
    "width": 608,            # SD 1.5 native (upscale a 1080 con ffmpeg)
    "height": 1080,          # Portrait 9:16 aproximado
    "steps": 28,             # Calidad/velocidad balance
    "cfg_scale": 7.5,        # Adherencia al prompt
    "sampler_name": "DPM++ 2M Karras",
    "restore_faces": True,   # Mejora caras realistas
}

NEGATIVE_BASE = (
    "cross, crucifix, bible, church, star of david, crescent moon, lotus flower, "
    "om symbol, rosary beads, saints, religious icons, religious symbols, "
    "cartoon, anime, illustration, painting, 3d render, deformed, mutated, "
    "blurry, watermark, text, signature, low quality, nsfw"
)

def generar_imagen(prompt: str, negativo: str, seed: int, carpeta_images: Path, nombre: str) -> str:
    """Genera una imagen via API de SD WebUI y la guarda."""
    payload = {
        **SD_CONFIG,
        "prompt": prompt,
        "negative_prompt": negativo or NEGATIVE_BASE,
        "seed": seed,
        "save_images": False,  # Manejamos el guardado manualmente
    }

    resp = requests.post(f"{SDWEBUI_URL}/sdapi/v1/txt2img", json=payload, timeout=300)
    resp.raise_for_status()

    img_b64 = resp.json()["images"][0]
    img_bytes = base64.b64decode(img_b64)

    ruta_salida = carpeta_images / nombre
    with open(ruta_salida, "wb") as f:
        f.write(img_bytes)

    return str(ruta_salida)

def ejecutar(metadata: dict) -> dict:
    """Genera todas las imágenes del proyecto."""
    carpeta = Path(metadata["carpeta"])
    carpeta_images = carpeta / "images"
    escenas = metadata["escenas"]

    print(f"[Agente 2] Generando {len(escenas)} imágenes...")
    print(f"  Arquetipo base: {metadata['arquetipo'][:60]}...")

    imagenes_generadas = []

    for escena in escenas:
        num = escena["num"]
        prompt = escena["prompt_imagen"]
        negativo = escena.get("negativo", NEGATIVE_BASE)
        seed = 1000 + num * 137 + metadata["fila_id"]  # Semilla determinista pero variada

        nombre_archivo = f"scene_{num:02d}.png"
        print(f"  Escena {num}/{len(escenas)}: generando... (seed={seed})", end=" ")
        t0 = time.time()

        ruta = generar_imagen(prompt, negativo, seed, carpeta_images, nombre_archivo)
        duracion = time.time() - t0

        print(f"[OK] ({duracion:.0f}s) → {nombre_archivo}")
        imagenes_generadas.append({
            "escena": num,
            "archivo": nombre_archivo,
            "ruta": ruta,
            "prompt": prompt,
            "seed": seed
        })

    # Actualizar metadata
    metadata["imagenes"] = imagenes_generadas
    metadata["status"] = "images_done"

    with open(carpeta / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # Detener SD WebUI para liberar GPU
    subprocess.run(["docker", "stop", "sdwebui"], capture_output=True)
    subprocess.run(["docker", "rm", "sdwebui"], capture_output=True)
    time.sleep(3)
    subprocess.run(["sudo", "sync"])
    subprocess.run(["sudo", "sh", "-c", "echo 3 > /proc/sys/vm/drop_caches"])
    print("  [OK] GPU liberada (SD WebUI detenido)")

    return metadata
```

---

## 32.6 Agente 3 — TTS + Subtítulos Sincronizados

### 32.6.1 Síntesis de Voz con kokoro-tts

```python
#!/usr/bin/env python3
"""
agent_03_tts_subtitles.py — Genera el audio y los subtítulos sincronizados.
Voz: kokoro-tts es_e (español latino masculino, tono inspirador)
Timestamps: faster-whisper (word-level)
Subtítulos: prayer.srt + prayer.ass (blanco, borde negro, margen 5% bottom)
"""
import requests
import json
import subprocess
import time
import os
from pathlib import Path

KOKORO_PORT = 8880
WHISPER_PORT = 8000

# Formato ASS para subtítulos estéticos
ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,62,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,0,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
# Alignment=5: centrado horizontal Y vertical (mitad del alto del frame 1920px)
# \fad(150,150) en cada línea Dialogue → fade-in 150ms + fade-out 150ms

def iniciar_kokoro():
    """Inicia el container de kokoro-tts."""
    subprocess.run([
        "docker", "run", "--runtime", "nvidia", "-d",
        "--name", "kokoro-tts", "--restart", "no", "--network", "host",
        "-v", f"{os.path.expanduser('~')}/.cache/huggingface:/root/.cache/huggingface",
        "dustynv/kokoro-tts:r39.2.0"
    ], capture_output=True)
    print("  Esperando kokoro-tts...", end=" ")
    for _ in range(30):
        try:
            requests.get(f"http://localhost:{KOKORO_PORT}/health", timeout=2)
            print("[OK]")
            return
        except:
            time.sleep(5); print(".", end="", flush=True)
    raise RuntimeError("kokoro-tts no respondió")

def iniciar_whisper():
    """Inicia faster-whisper para generar timestamps."""
    subprocess.run([
        "docker", "run", "--runtime", "nvidia", "-d",
        "--name", "faster-whisper", "--restart", "no", "--network", "host",
        "-e", "WHISPER_MODEL=small",   # small es suficiente para timestamps de audio propio
        "-e", "WHISPER_DEVICE=cuda",
        "-e", "WHISPER_COMPUTE_TYPE=float16",
        "-e", "WHISPER_LANGUAGE=es",
        "dustynv/faster-whisper:r39.2.0"
    ], capture_output=True)
    print("  Esperando faster-whisper...", end=" ")
    for _ in range(20):
        try:
            requests.get(f"http://localhost:{WHISPER_PORT}/health", timeout=2)
            print("[OK]"); return
        except:
            time.sleep(8); print(".", end="", flush=True)
    raise RuntimeError("faster-whisper no respondió")

def generar_texto_completo(escenas: list) -> str:
    """Une el texto de todas las escenas en un solo párrafo para el TTS."""
    return " ".join(e["texto"] for e in escenas)

def sintetizar_audio(texto: str, ruta_mp3: Path) -> None:
    """Genera el MP3 via kokoro-tts API."""
    resp = requests.post(
        f"http://localhost:{KOKORO_PORT}/v1/audio/speech",
        json={
            "model": "kokoro",
            "input": texto,
            "voice": "es_e",        # Español masculino
            "speed": 0.92,          # Ligeramente más lento para tono solemne
            "response_format": "mp3"
        },
        timeout=120
    )
    resp.raise_for_status()
    ruta_mp3.write_bytes(resp.content)
    print(f"  [OK] Audio generado: {ruta_mp3.stat().st_size // 1024} KB")

def obtener_timestamps(ruta_mp3: Path) -> list:
    """Transcribe el MP3 con faster-whisper para obtener timestamps por palabra."""
    resp = requests.post(
        f"http://localhost:{WHISPER_PORT}/v1/audio/transcriptions",
        files={"file": ("prayer.mp3", open(ruta_mp3, "rb"))},
        data={
            "model": "whisper-1",
            "language": "es",
            "response_format": "verbose_json",
            "timestamp_granularities[]": "word"
        },
        timeout=120
    )
    resp.raise_for_status()
    datos = resp.json()
    palabras = datos.get("words", [])
    print(f"  [OK] Timestamps: {len(palabras)} palabras detectadas")
    return palabras

def seg_a_srt(segundos: float) -> str:
    """Convierte segundos a formato SRT (HH:MM:SS,mmm)."""
    h = int(segundos // 3600)
    m = int((segundos % 3600) // 60)
    s = int(segundos % 60)
    ms = int((segundos % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def seg_a_ass(segundos: float) -> str:
    """Convierte segundos a formato ASS (H:MM:SS.cc)."""
    h = int(segundos // 3600)
    m = int((segundos % 3600) // 60)
    s = segundos % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def generar_subtitulos(palabras: list, carpeta_subs: Path) -> tuple:
    """Genera SRT y ASS con grupos de 5–6 palabras por línea."""
    PALABRAS_POR_LINEA = 5
    grupos = []
    for i in range(0, len(palabras), PALABRAS_POR_LINEA):
        bloque = palabras[i:i + PALABRAS_POR_LINEA]
        if not bloque:
            continue
        texto_linea = " ".join(p["word"] for p in bloque)
        inicio = bloque[0]["start"]
        fin = bloque[-1]["end"]
        grupos.append({"texto": texto_linea, "inicio": inicio, "fin": fin})

    # Generar SRT
    srt_path = carpeta_subs / "prayer.srt"
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, g in enumerate(grupos, 1):
            f.write(f"{i}\n")
            f.write(f"{seg_a_srt(g['inicio'])} --> {seg_a_srt(g['fin'])}\n")
            f.write(f"{g['texto']}\n\n")

    # Generar ASS
    ass_path = carpeta_subs / "prayer.ass"
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ASS_HEADER)
        for g in grupos:
            f.write(
                f"Dialogue: 0,{seg_a_ass(g['inicio'])},{seg_a_ass(g['fin'])},"
                f"Default,,0,0,0,,"
                f"{{\\fad(150,150)}}{g['texto']}\n"
            )
            # \fad(150,150) → fade-in 150ms + fade-out 150ms por línea

    print(f"  [OK] Subtítulos: {len(grupos)} líneas → prayer.srt + prayer.ass")
    return srt_path, ass_path

def ejecutar(metadata: dict) -> dict:
    """Ejecuta el Agente 3: TTS + timestamps + subtítulos."""
    carpeta = Path(metadata["carpeta"])
    escenas = metadata["escenas"]

    print("[Agente 3] Generando TTS y subtítulos...")

    texto_completo = generar_texto_completo(escenas)
    print(f"  Texto: {len(texto_completo.split())} palabras")

    iniciar_kokoro()
    iniciar_whisper()

    ruta_mp3 = carpeta / "audio" / "prayer.mp3"
    sintetizar_audio(texto_completo, ruta_mp3)
    palabras = obtener_timestamps(ruta_mp3)

    # Guardar timestamps raw
    (carpeta / "audio" / "timestamps.json").write_text(
        json.dumps(palabras, indent=2, ensure_ascii=False)
    )

    srt_path, ass_path = generar_subtitulos(palabras, carpeta / "subtitles")

    # Detener containers
    for nombre in ["kokoro-tts", "faster-whisper"]:
        subprocess.run(["docker", "stop", nombre], capture_output=True)
        subprocess.run(["docker", "rm", nombre], capture_output=True)
    subprocess.run(["sudo", "sync"])
    subprocess.run(["sudo", "sh", "-c", "echo 3 > /proc/sys/vm/drop_caches"])
    print("  [OK] Containers TTS/STT detenidos, RAM liberada")

    metadata["audio_mp3"] = str(ruta_mp3)
    metadata["subtitulos_srt"] = str(srt_path)
    metadata["subtitulos_ass"] = str(ass_path)
    metadata["status"] = "audio_done"

    with open(carpeta / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    return metadata
```

---

## 32.7 Agente 4 — Ensamblaje de Video con ffmpeg

### 32.7.1 Estrategia de Composición

Cada imagen recibe un efecto Ken Burns (zoom lento 1.0→1.05, centrado) durante su duración de escena. Las imágenes se concatenan con transiciones `xfade` de 0.5 segundos. Finalmente se mezclan con el audio y se añaden los subtítulos.

```python
#!/usr/bin/env python3
"""
agent_04_video_assembly.py — Ensambla el video final con ffmpeg.
Ken Burns effect + xfade transitions + subtítulos + audio
Output: 1080×1920, ~30-40 segundos, H.264, AAC
"""
import subprocess
import json
import shutil
from pathlib import Path

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30

def segundos_a_frames(segundos: float) -> int:
    return int(segundos * FPS)

def generar_clip_ken_burns(img_path: Path, duracion_seg: float, salida: Path) -> None:
    """Genera un clip con efecto Ken Burns (zoom in suave) para una imagen."""
    frames = segundos_a_frames(duracion_seg)
    # Upscale imagen a 1080×1920 y aplicar Ken Burns
    subprocess.run([
        "ffmpeg", "-y",
        "-loop", "1",
        "-t", str(duracion_seg + 0.6),   # +0.6s de margen para el xfade
        "-i", str(img_path),
        "-vf", (
            f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},"
            f"zoompan=z='min(zoom+0.0008,1.05)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={frames + 18}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT},"
            f"fps={FPS}"
        ),
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        str(salida)
    ], check=True, capture_output=True)

def concatenar_con_xfade(clips: list, duracion_transicion: float = 0.5) -> str:
    """Concatena clips con transición xfade crossfade entre ellos."""
    if len(clips) == 1:
        return clips[0]

    # Construir filtergraph de xfade encadenado
    inputs = []
    for c in clips:
        inputs.extend(["-i", c])

    # Calcular offsets para xfade (fin de cada clip - transicion)
    duraciones = []
    for clip in clips:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", clip],
            capture_output=True, text=True
        )
        duraciones.append(float(probe.stdout.strip()))

    filtros = []
    offset_acum = 0.0
    etiqueta_actual = "[0]"

    for i in range(1, len(clips)):
        offset_acum += duraciones[i-1] - duracion_transicion
        etiqueta_salida = f"[xf{i}]"
        filtros.append(
            f"{etiqueta_actual}[{i}]xfade=transition=fade:"
            f"duration={duracion_transicion}:offset={offset_acum:.3f}{etiqueta_salida}"
        )
        etiqueta_actual = etiqueta_salida

    tmp_concat = str(clips[0]).replace("scene_01_kb.mp4", "concat_video.mp4")
    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", ";".join(filtros),
        "-map", etiqueta_actual,
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        tmp_concat
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return tmp_concat

def mezclar_audio_y_subs(video_concat: str, audio_mp3: str, ass_path: str,
                          salida_social: str, salida_editable: str) -> None:
    """Combina video + audio + subtítulos para producir los dos outputs."""
    # Video social: subtítulos quemados (burned-in)
    subprocess.run([
        "ffmpeg", "-y",
        "-i", video_concat,
        "-i", audio_mp3,
        "-vf", f"ass={ass_path}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "22",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",   # Para reproducción streaming
        salida_social
    ], check=True, capture_output=True)
    print(f"  [OK] prayer_social.mp4 listo")

    # Video editable: subtítulos como pista separada (soft subs)
    subprocess.run([
        "ffmpeg", "-y",
        "-i", video_concat,
        "-i", audio_mp3,
        "-i", ass_path.replace(".ass", ".srt"),
        "-c:v", "libx264", "-preset", "medium", "-crf", "22",
        "-c:a", "aac", "-b:a", "192k",
        "-c:s", "mov_text",
        "-metadata:s:s:0", "language=spa",
        "-shortest",
        salida_editable
    ], check=True, capture_output=True)
    print(f"  [OK] prayer_editable.mp4 listo (subtítulos como pista separada)")

def ejecutar(metadata: dict) -> dict:
    """Ensambla el video final del proyecto."""
    carpeta = Path(metadata["carpeta"])
    escenas = metadata["escenas"]
    imagenes = metadata["imagenes"]

    print(f"[Agente 4] Ensamblando video ({len(escenas)} escenas)...")

    tmp_dir = carpeta / "video" / "tmp"
    tmp_dir.mkdir(exist_ok=True)

    # 1. Generar clips Ken Burns por escena
    clips_kb = []
    for escena, img_info in zip(escenas, imagenes):
        img_path = Path(img_info["ruta"])
        duracion = escena["duracion_seg"]
        salida_clip = tmp_dir / f"scene_{escena['num']:02d}_kb.mp4"
        print(f"  Ken Burns escena {escena['num']}...", end=" ")
        generar_clip_ken_burns(img_path, duracion, salida_clip)
        clips_kb.append(str(salida_clip))
        print("[OK]")

    # 2. Concatenar con xfade
    print("  Concatenando con transiciones crossfade...", end=" ")
    video_concat = concatenar_con_xfade(clips_kb)
    print("[OK]")

    # 3. Mezclar audio + subtítulos
    print("  Mezclando audio y subtítulos...", end=" ")
    mezclar_audio_y_subs(
        video_concat=video_concat,
        audio_mp3=metadata["audio_mp3"],
        ass_path=metadata["subtitulos_ass"],
        salida_social=str(carpeta / "video" / "prayer_social.mp4"),
        salida_editable=str(carpeta / "video" / "prayer_editable.mp4")
    )

    # 4. Limpiar temporales
    shutil.rmtree(tmp_dir, ignore_errors=True)

    # Verificar duración del video final
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(carpeta / "video" / "prayer_social.mp4")],
        capture_output=True, text=True
    )
    duracion_final = float(probe.stdout.strip())
    print(f"  [OK] Video final: {duracion_final:.1f} segundos")

    if not (28 <= duracion_final <= 45):
        print(f"  [WARN]  ADVERTENCIA: Duración {duracion_final:.1f}s fuera del rango 30–40s")

    metadata["video_social"] = str(carpeta / "video" / "prayer_social.mp4")
    metadata["video_editable"] = str(carpeta / "video" / "prayer_editable.mp4")
    metadata["duracion_seg"] = duracion_final
    metadata["status"] = "video_done"

    with open(carpeta / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    return metadata
```

---

## 32.8 Pipeline FastAPI Server (Puerto 8090)

N8N (en Docker bridge) llama al pipeline server vía `http://172.18.0.1:8090/`. El servidor orquesta los 4 agentes secuencialmente y reporta el estado.

```python
#!/usr/bin/env python3
"""
pipeline_server.py — Servidor FastAPI que orquesta los 4 agentes de producción.
Puerto: 8090. N8N lo llama vía 172.18.0.1:8090.
"""
import json
import threading
import time
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uvicorn

# Importar los 4 agentes
import sys
sys.path.insert(0, str(Path.home() / "projects/daily-prayers/scripts/agents"))
import agent_01_script_generator as agente1
import agent_02_image_generator as agente2
import agent_03_tts_subtitles as agente3
import agent_04_video_assembly as agente4

app = FastAPI(title="Daily Prayers Pipeline Server")

# Estado de jobs en memoria
jobs: dict = {}

class FilaPayload(BaseModel):
    fila_id: int
    libro: str
    referencia: str
    cap_inicio: int
    ver_inicio: int
    cap_fin: int
    ver_fin: int
    indice_arquetipo: int = 0

def ejecutar_pipeline(job_id: str, fila: dict):
    """Pipeline completo en background thread."""
    jobs[job_id]["estado"] = "running"
    jobs[job_id]["etapa"] = "Agente 1 — Script Generator"

    try:
        # Etapa 1: Script
        metadata = agente1.ejecutar(fila, fila.get("indice_arquetipo", 0))
        jobs[job_id]["carpeta"] = metadata["carpeta"]
        jobs[job_id]["etapa"] = "Agente 2 — Image Generator"

        # Etapa 2: Imágenes
        metadata = agente2.ejecutar(metadata)
        jobs[job_id]["etapa"] = "Agente 3 — TTS + Subtítulos"

        # Etapa 3: Audio + subtítulos
        metadata = agente3.ejecutar(metadata)
        jobs[job_id]["etapa"] = "Agente 4 — Video Assembly"

        # Etapa 4: Video
        metadata = agente4.ejecutar(metadata)

        jobs[job_id]["estado"] = "completed"
        jobs[job_id]["etapa"] = "Completado"
        jobs[job_id]["metadata"] = metadata
        jobs[job_id]["fin"] = datetime.now().isoformat()

    except Exception as e:
        jobs[job_id]["estado"] = "error"
        jobs[job_id]["error"] = str(e)
        # Limpieza de emergencia
        import subprocess
        for nombre in ["sdwebui", "kokoro-tts", "faster-whisper"]:
            subprocess.run(["docker", "stop", nombre], capture_output=True)
        subprocess.run(["sudo", "sh", "-c", "echo 3 > /proc/sys/vm/drop_caches"])

@app.post("/pipeline/start")
async def iniciar_pipeline(fila: FilaPayload, background_tasks: BackgroundTasks):
    """Inicia el pipeline para una fila de Google Sheets."""
    job_id = f"job_{fila.fila_id}_{int(time.time())}"
    jobs[job_id] = {
        "job_id": job_id,
        "fila_id": fila.fila_id,
        "estado": "queued",
        "etapa": "En cola",
        "inicio": datetime.now().isoformat()
    }
    background_tasks.add_task(ejecutar_pipeline, job_id, fila.dict())
    return {"job_id": job_id, "estado": "queued"}

@app.get("/pipeline/{job_id}/status")
async def estado_pipeline(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    job = jobs[job_id]
    return {
        "job_id": job_id,
        "estado": job["estado"],
        "etapa": job.get("etapa"),
        "carpeta": job.get("carpeta"),
        "error": job.get("error")
    }

@app.get("/health")
async def health():
    return {"status": "ok", "jobs_activos": sum(1 for j in jobs.values() if j["estado"] == "running")}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8090, log_level="info")
```

```bash
# Iniciar el Pipeline Server
source ~/venvs/llm/bin/activate
nohup python3 ~/projects/daily-prayers/scripts/pipeline_server.py \
  > ~/logs/pipeline_server.log 2>&1 &
echo $! > ~/projects/daily-prayers/pipeline_server.pid
echo "[OK] Pipeline Server iniciado en :8090 (PID $(cat ~/projects/daily-prayers/pipeline_server.pid))"

# Verificar
curl -s http://localhost:8090/health
```

---

## 32.9 N8N Workflows

### 32.9.1 Workflow 1 — Producción Diaria (Cron 7 AM)

Importar en N8N (`http://localhost:5678`) → Settings → Import Workflow:

```json
{
  "name": "Daily Prayers — Producción Diaria",
  "nodes": [
    {
      "name": "Cron 7:00 AM",
      "type": "n8n-nodes-base.scheduleTrigger",
      "parameters": {
        "rule": {"cronExpression": "0 7 * * *"}
      }
    },
    {
      "name": "Leer Google Sheets",
      "type": "n8n-nodes-base.googleSheets",
      "parameters": {
        "operation": "getAll",
        "sheetId": "REEMPLAZAR_CON_ID_DE_LA_HOJA",
        "range": "A:Q",
        "filters": {"values": [{"lookupColumn": "status", "lookupValue": "pending"}]},
        "limit": 1
      }
    },
    {
      "name": "Iniciar Pipeline",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "http://172.18.0.1:8090/pipeline/start",
        "sendBody": true,
        "bodyContentType": "json",
        "jsonBody": "={{ {fila_id: $json.id, libro: $json.libro, referencia: $json.referencia, cap_inicio: $json.cap_inicio, ver_inicio: $json.ver_inicio, cap_fin: $json.cap_fin, ver_fin: $json.ver_fin} }}"
      }
    },
    {
      "name": "Esperar Completado (polling cada 3 min)",
      "type": "n8n-nodes-base.wait",
      "parameters": {"amount": 3, "unit": "minutes"}
    },
    {
      "name": "Verificar Estado",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "GET",
        "url": "=http://172.18.0.1:8090/pipeline/{{ $json.job_id }}/status"
      }
    },
    {
      "name": "Actualizar Sheets — status=ready",
      "type": "n8n-nodes-base.googleSheets",
      "parameters": {
        "operation": "update",
        "sheetId": "REEMPLAZAR_CON_ID_DE_LA_HOJA",
        "row": "={{ $('Leer Google Sheets').item.json.id }}",
        "dataToSend": {"titulo": "={{ $json.metadata.titulo }}", "status": "ready"}
      }
    }
  ]
}
```

### 32.9.2 Workflow 2 — Publicación con Aprobación Humana

> **Filosofía:** Antes de publicar en redes sociales, el video sube a Google Drive y se envía un email con el enlace de previsualización al administrador. Solo después de una aprobación explícita (click en el enlace de aprobación) se publica. Esto evita errores o contenido inesperado en el canal.

**Flujo:**
```
Video completado (status=ready)
    ↓
Subir a Google Drive (carpeta daily-prayers-pending/)
    ↓
Enviar email al administrador: enlace de Drive + enlace de aprobación
    ↓
Webhook espera aprobación (timeout: 24h)
    ↓ (aprobado)
Publicar YouTube + TikTok
    ↓
Actualizar Sheets: status=published
    ↓ (rechazado con nota)
Actualizar Sheets: status=review_failed
Notificar para revisión manual
```

```json
{
  "name": "Daily Prayers — Publicación con Aprobación",
  "nodes": [
    {
      "name": "Webhook video=ready",
      "type": "n8n-nodes-base.webhook",
      "parameters": {"path": "prayers-ready", "httpMethod": "POST"}
    },
    {
      "name": "Subir a Google Drive",
      "type": "n8n-nodes-base.googleDrive",
      "parameters": {
        "operation": "upload",
        "folderId": "REEMPLAZAR_CON_ID_CARPETA_DRIVE",
        "fileName": "={{ $json.video_filename }}",
        "fileContent": "={{ $binary.data }}"
      }
    },
    {
      "name": "Email de Aprobación",
      "type": "n8n-nodes-base.gmail",
      "parameters": {
        "to": "REEMPLAZAR_CON_EMAIL_ADMIN",
        "subject": "=Daily Prayers {{ $json.referencia }} — pendiente de aprobación",
        "message": "=<p>Video listo para revisión:</p><p><a href='{{ $('Subir a Google Drive').item.json.webViewLink }}'>Ver en Google Drive</a></p><p><a href='http://172.18.0.1:5678/webhook/approve?id={{ $json.fila_id }}&token={{ $json.approval_token }}'>APROBAR</a> | <a href='http://172.18.0.1:5678/webhook/reject?id={{ $json.fila_id }}&token={{ $json.approval_token }}'>RECHAZAR</a></p>"
      }
    },
    {
      "name": "Esperar Aprobación (24h)",
      "type": "n8n-nodes-base.wait",
      "parameters": {"resume": "webhook", "webhookSuffix": "={{ 'approve-' + $json.fila_id }}"}
    },
    {
      "name": "Publicar YouTube",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "http://172.18.0.1:8090/publish/youtube",
        "jsonBody": "={{ $json }}"
      }
    },
    {
      "name": "Publicar TikTok",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "http://172.18.0.1:8090/publish/tiktok",
        "jsonBody": "={{ $json }}"
      }
    },
    {
      "name": "Actualizar Sheets — published",
      "type": "n8n-nodes-base.googleSheets",
      "parameters": {
        "operation": "update",
        "sheetId": "REEMPLAZAR_CON_ID_DE_LA_HOJA",
        "row": "={{ $json.fila_id }}",
        "dataToSend": {
          "status": "published",
          "youtube_url": "={{ $('Publicar YouTube').item.json.url }}",
          "tiktok_url": "={{ $('Publicar TikTok').item.json.url }}"
        }
      }
    }
  ]
}
```

> **Tokens de aprobación:** Genere un UUID por video en el pipeline server (`approval_token = str(uuid.uuid4())`) y guárdelo en `metadata.json`. El webhook de N8N valida el token antes de aprobar. Si el administrador rechaza, el status cambia a `review_failed` y el video permanece en Drive para revisión manual.

---

## 32.10 Agente 5 — Publicación en YouTube Shorts

```python
#!/usr/bin/env python3
"""
agent_05_youtube_publisher.py — Publica el video en YouTube como Short.
Requiere: google-api-python-client, OAuth2 configurado.
"""
import os
import json
from pathlib import Path
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

CONFIG_DIR = Path.home() / "projects/daily-prayers/config"
TOKEN_FILE = CONFIG_DIR / "youtube_token.json"
SECRETS_FILE = CONFIG_DIR / "client_secrets.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

EMOJIS_POR_LIBRO = {
    "Salmos": ["🙏", "✨", "💫", "🌟", "🕊️", "🌅", "💙", "🌿"],
    "Proverbios": ["[TIP]", "📖", "🌱", "*", "", "💎", "🌺", "🎯"]
}

def obtener_credenciales() -> Credentials:
    """Obtiene o refresca las credenciales OAuth2 de YouTube."""
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(SECRETS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())

    return creds

def generar_titulo_youtube(metadata: dict) -> str:
    """Genera el título formateado: 'Junio 29 - Paz Interior ✨'"""
    ahora = datetime.now()
    MESES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
              "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
    fecha_str = f"{MESES[ahora.month-1]} {ahora.day}"
    return f"{fecha_str} - {metadata['titulo']} {metadata['emoji']}"

def generar_descripcion(metadata: dict) -> str:
    """Genera la descripción del video."""
    return (
        f"Una plegaria inspirada en {metadata['referencia']}.\n\n"
        f"Un momento de reflexión y esperanza para comenzar el día con gratitud.\n\n"
        f"#{metadata['libro']} #PlegariaDiaria #Inspiracion #DailyPrayers #Shorts"
    )

def publicar_youtube(metadata: dict) -> str:
    """Sube el video a YouTube y retorna la URL."""
    creds = obtener_credenciales()
    youtube = build("youtube", "v3", credentials=creds)

    titulo = generar_titulo_youtube(metadata)
    descripcion = generar_descripcion(metadata)
    video_path = metadata["video_social"]

    print(f"[Agente 5] Subiendo a YouTube: '{titulo}'")
    print(f"  Archivo: {video_path} ({Path(video_path).stat().st_size // (1024*1024)} MB)")

    request_body = {
        "snippet": {
            "title": titulo[:100],         # YouTube límite 100 chars
            "description": descripcion,
            "tags": ["plegaria", "salmos", "proverbios", "shorts", "inspiracion",
                     "espiritualidad", "dios", "meditacion", "daily prayers"],
            "categoryId": "22",             # People & Blogs
            "defaultLanguage": "es",
        },
        "status": {
            "privacyStatus": "public",
            "madeForKids": False,
            "selfDeclaredMadeForKids": False,
        }
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True,
                            mimetype="video/mp4")
    request = youtube.videos().insert(
        part=",".join(request_body.keys()),
        body=request_body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  Subiendo: {int(status.progress() * 100)}%...", end="\r")

    video_id = response["id"]
    url = f"https://youtu.be/{video_id}"
    print(f"\n  [OK] Publicado en YouTube: {url}")
    return url
```

---

## 32.11 Agente 6 — Publicación en TikTok

> **[REQUIERE VERIFICACIÓN]:** La TikTok Content Posting API v2 requiere aprobación manual del equipo de TikTok para desarrolladores. El proceso puede tomar 2–4 semanas. Solicitar acceso en: developers.tiktok.com → "Content Posting API".

```python
#!/usr/bin/env python3
"""
agent_06_tiktok_publisher.py — Publica el video en TikTok.
[REQUIERE VERIFICACIÓN] — necesita aprobación de la Content Posting API.
"""
import requests
import json
from pathlib import Path

CONFIG_DIR = Path.home() / "projects/daily-prayers/config"
TIKTOK_CONFIG_FILE = CONFIG_DIR / "tiktok_credentials.json"

def cargar_credenciales_tiktok() -> dict:
    if not TIKTOK_CONFIG_FILE.exists():
        raise FileNotFoundError(
            "Credenciales TikTok no encontradas.\n"
            "1. Registrarse en developers.tiktok.com\n"
            "2. Solicitar acceso a 'Content Posting API'\n"
            "3. Crear app → obtener client_key + client_secret\n"
            "4. Completar flujo OAuth → guardar access_token\n"
            f"5. Crear {TIKTOK_CONFIG_FILE} con: {{\"access_token\": \"...\", \"open_id\": \"...\"}}"
        )
    return json.loads(TIKTOK_CONFIG_FILE.read_text())

def publicar_tiktok(metadata: dict, titulo: str) -> str:
    """
    Sube el video a TikTok via Content Posting API v2.
    Flujo: init upload → upload chunks → complete → publish.
    """
    creds = cargar_credenciales_tiktok()
    access_token = creds["access_token"]
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    video_path = Path(metadata["video_social"])
    video_size = video_path.stat().st_size

    # Paso 1: Inicializar upload
    init_resp = requests.post(
        "https://open.tiktokapis.com/v2/post/publish/video/init/",
        headers=headers,
        json={
            "post_info": {
                "title": titulo[:150],    # TikTok límite 150 chars
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_stitch": False,
                "disable_comment": False,
                "video_cover_timestamp_ms": 1000
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": video_size,    # Un solo chunk (video pequeño)
                "total_chunk_count": 1
            }
        }
    )
    init_resp.raise_for_status()
    data = init_resp.json()["data"]
    publish_id = data["publish_id"]
    upload_url = data["upload_url"]

    # Paso 2: Upload del video
    with open(video_path, "rb") as f:
        upload_resp = requests.put(
            upload_url,
            data=f,
            headers={
                "Content-Type": "video/mp4",
                "Content-Range": f"bytes 0-{video_size-1}/{video_size}",
                "Content-Length": str(video_size)
            }
        )
    upload_resp.raise_for_status()

    url = f"https://www.tiktok.com/video/{publish_id}"
    print(f"  [OK] Publicado en TikTok: {url}")
    return url
```

---

## 32.12 Agente 7 — Reporte Diario de Analytics

```python
#!/usr/bin/env python3
"""
agent_07_analytics_reporter.py — Genera reporte diario de performance del canal.
Ejecutado por N8N a las 9:00 PM.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

CONFIG_DIR = Path.home() / "projects/daily-prayers/config"

def obtener_analytics_youtube(video_id: str = None) -> dict:
    """Obtiene métricas de YouTube Analytics para los últimos 7 días."""
    creds = Credentials.from_authorized_user_file(
        str(CONFIG_DIR / "youtube_token.json"),
        scopes=["https://www.googleapis.com/auth/yt-analytics.readonly",
                "https://www.googleapis.com/auth/youtube.readonly"]
    )
    analytics = build("youtubeAnalytics", "v2", credentials=creds)
    youtube = build("youtube", "v3", credentials=creds)

    # Info del canal
    canal_resp = youtube.channels().list(part="statistics,snippet", mine=True).execute()
    canal = canal_resp["items"][0]

    # Métricas de los últimos 7 días
    hoy = datetime.now().strftime("%Y-%m-%d")
    hace_7_dias = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    metricas = analytics.reports().query(
        ids="channel==MINE",
        startDate=hace_7_dias,
        endDate=hoy,
        metrics="views,estimatedMinutesWatched,averageViewPercentage,subscribersGained,likes",
        dimensions="day"
    ).execute()

    return {
        "canal": canal["snippet"]["title"],
        "suscriptores": canal["statistics"]["subscriberCount"],
        "vistas_totales": canal["statistics"]["viewCount"],
        "videos_totales": canal["statistics"]["videoCount"],
        "metricas_7_dias": metricas.get("rows", []),
        "columnas": [h["name"] for h in metricas.get("columnHeaders", [])]
    }

def formatear_reporte(datos: dict) -> str:
    """Genera el texto del reporte diario."""
    ahora = datetime.now()
    lineas = [
        f"📊 REPORTE DAILY PRAYERS — {ahora.strftime('%d/%m/%Y')}",
        f"{'='*50}",
        f"Canal: {datos['canal']}",
        f"Suscriptores: {int(datos['suscriptores']):,}",
        f"Vistas totales del canal: {int(datos['vistas_totales']):,}",
        f"Videos publicados: {datos['videos_totales']}",
        f"",
        f"📈 Últimos 7 días:",
    ]

    total_vistas = 0
    total_subs = 0
    for fila in datos.get("metricas_7_dias", []):
        fecha, vistas, minutos, retencion, subs, likes = fila
        total_vistas += int(vistas)
        total_subs += int(subs)
        lineas.append(f"  {fecha}: {int(vistas):,} vistas, {retencion:.1f}% retención")

    lineas.extend([
        f"",
        f"Total 7 días: {total_vistas:,} vistas, {total_subs:,} suscriptores nuevos",
        f"",
        f"🤖 Generado automáticamente por el Jetson AGX Orin 64GB"
    ])

    return "\n".join(lineas)

def ejecutar() -> str:
    print("[Agente 7] Generando reporte de analytics...")
    datos = obtener_analytics_youtube()
    reporte = formatear_reporte(datos)

    # Guardar reporte
    reporte_path = Path.home() / f"logs/analytics_{datetime.now().strftime('%Y%m%d')}.txt"
    reporte_path.write_text(reporte, encoding="utf-8")
    print(f"[OK] Reporte guardado: {reporte_path}")
    print(reporte)
    return reporte
```

---

## 32.13 Modo Energético y Prevención OOM

### 32.13.1 Secuencia de Energía del Pipeline Completo

```bash
# El pipeline_server.py gestiona esto automáticamente.
# Resumen manual para referencia:

# Etapa 1: Script (Ollama 4B)
pwr-30w && ollama serve
# → ejecutar Agente 1
pkill -f "ollama serve" && sync && echo 3 | sudo tee /proc/sys/vm/drop_caches

# Etapa 2: Imágenes (SD WebUI)
pwr-maxn  # MAXN para generación de imágenes
docker-on
docker run --runtime nvidia ... dustynv/stable-diffusion-webui:r39.2.0 ...
# → ejecutar Agente 2
docker stop sdwebui && docker rm sdwebui
sync && echo 3 | sudo tee /proc/sys/vm/drop_caches

# Etapa 3: TTS + STT (kokoro + whisper)
pwr-30w
docker run ... kokoro-tts:r39.2.0
docker run ... faster-whisper:r39.2.0
# → ejecutar Agente 3
docker stop kokoro-tts faster-whisper && docker rm kokoro-tts faster-whisper

# Etapa 4: Video (ffmpeg CPU)
# pwr-30w ya activo — no necesita GPU
# → ejecutar Agente 4

# Post-pipeline
pwr-15w  # Ahorro entre publicaciones
```

### 32.13.2 Aliases

```bash
# Agregar al ~/.bash_aliases
cat >> ~/.bash_aliases << 'EOF'

# ── Daily Prayers Pipeline ──────────────────────────────────────────
alias prayers-start='source ~/venvs/llm/bin/activate && \
  nohup python3 ~/projects/daily-prayers/scripts/pipeline_server.py \
  > ~/logs/pipeline_server.log 2>&1 & echo "Pipeline Server :8090 iniciado"'
alias prayers-stop='pkill -f pipeline_server.py && echo "Pipeline Server detenido"'
alias prayers-logs='tail -f ~/logs/pipeline_server.log'
alias prayers-status='curl -s http://localhost:8090/health | python3 -m json.tool'
alias prayers-test='curl -s -X POST http://localhost:8090/pipeline/start \
  -H "Content-Type: application/json" \
  -d "{\"fila_id\":1,\"libro\":\"Salmos\",\"referencia\":\"Salmos 1:1-6\",\"cap_inicio\":1,\"ver_inicio\":1,\"cap_fin\":1,\"ver_fin\":6}"'
EOF

source ~/.bash_aliases
```

---

## 32.14 Solución de Problemas

### SD WebUI: OOM durante generación de imagen

```bash
# Reducir resolución o steps
# Cambiar en agent_02_image_generator.py:
# SD_CONFIG = {"width": 512, "height": 896, "steps": 20, ...}
# Y en el mismo script, reducir la seed range

# Verificar GPU disponible antes de iniciar
free -h | grep -i mem
docker stats sdwebui --no-stream 2>/dev/null
```

### kokoro-tts: Voz `es_e` no disponible

```bash
# Listar voces disponibles en el container
docker exec kokoro-tts python3 -c "from kokoro import list_voices; print(list_voices())" 2>/dev/null

# Voces alternativas de español en kokoro:
# es_e → español masculino
# Si no está disponible, usar piper-tts como fallback:
python3 -m piper --model ~/jetson-ai-data/models/piper-voices/es_ES-mls_10246-medium.onnx \
  --output_file /data/prayers/test/audio/prayer.mp3 < /tmp/texto_prueba.txt
```

### ffmpeg xfade: `Invalid option: transition`

```bash
# Verificar versión de ffmpeg que soporta xfade
ffmpeg -version | grep "ffmpeg version"
# xfade requiere ffmpeg >= 4.3
# Si la versión es antigua:
sudo apt install -y ffmpeg
# o compilar desde fuente con --enable-libx264
```

### YouTube: `quotaExceeded` en la API

```bash
# La API de YouTube tiene quota de 10,000 unidades/día.
# Un upload = ~1,600 unidades → límite ~6 uploads/día con cuenta básica.
# Solución: solicitar quota extra en Google Cloud Console → APIs → YouTube Data API v3
# O publicar en horario nocturno para distribuir el gasto de quota.
```

### TikTok: `access_token` expirado

```bash
# El access_token de TikTok expira cada 24 horas.
# Usar refresh_token para renovarlo automáticamente:
# POST https://open.tiktokapis.com/v2/oauth/token/
# body: grant_type=refresh_token&client_key=X&client_secret=X&refresh_token=X
```

---

---

## 32.15 Escalabilidad y Extensiones

### 32.15.1 Advertencia de Memoria — Qué Cargar y Cuándo

El pipeline de video usa múltiples servicios pesados. El Jetson tiene **~59 GB disponibles** (64 GB menos el OS base), pero no todos los agentes deben estar activos simultáneamente:

| Fase del pipeline | Agentes activos | VRAM/RAM usada | VRAM libre aprox. |
|---|---|---|---|
| Generación de script (Agente 1) | Ollama Qwen3.5-4B | ~5 GB | ~54 GB |
| Generación de imagen (Agente 2) | SD WebUI | ~8–12 GB | ~42–46 GB |
| TTS + Subtítulos (Agente 3) | kokoro-tts + faster-whisper | ~4 GB | ~50 GB |
| Ensamble de video (Agente 4) | ffmpeg (CPU) | ~1 GB RAM | ~58 GB |
| **Pipeline completo encadenado** | **Secuencial (no simultáneo)** | **~12 GB pico** | **~47 GB** |

> **IMPORTANTE:** Los agentes se ejecutan en secuencia, no en paralelo. El orquestador (§32.8) arranca cada servicio cuando lo necesita y lo detiene al terminar. Nunca deje SD WebUI y Ollama corriendo simultáneamente si no los está usando — SD WebUI solo consume ~8 GB cuando está activo pero ocupa el bus de memoria de la GPU.

**Script de verificación de memoria antes de ejecutar el pipeline:**

```bash
# Añadir al orquestador antes de iniciar cada video
RAM_LIBRE=$(free -g | awk '/^Mem:/{print $7}')
if [ "$RAM_LIBRE" -lt 20 ]; then
    echo "[WARN] Menos de 20 GB libres ($RAM_LIBRE GB) — ejecutando limpieza"
    docker stop kokoro-tts sd-webui 2>/dev/null
    sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
    sleep 2
fi
```

### 32.15.2 Evaluación de Backend LLM para Generación de Scripts

El Agente 1 (generación de scripts) es el único que usa un LLM. Los scripts de video son cortos (~200 palabras), lo que limita la ventana de contexto necesaria:

| Backend | Modelo recomendado | VRAM | Velocidad script (~200 palabras) | Calidad |
|---|---|---|---|---|
| **Ollama** (actual) | Qwen3.5-4B | ~5 GB | ~15–25 seg | Alta |
| **llama.cpp** | Qwen3.5-4B Q4_K_M | ~2.5 GB | **~8–12 seg** | Alta |
| **llama.cpp** | Mistral-7B Q4_K_M | ~4 GB | ~12–18 seg | Alta |
| **vLLM** | Qwen3.5-7B | ~7 GB | ~20 seg (startup alto) | Muy Alta |

> **RECOMENDACIÓN:** Para este pipeline, **llama.cpp con Qwen3.5-4B Q4_K_M** es la mejor opción: usa la mitad de VRAM que Ollama (dejando más para SD WebUI), genera el script en la mitad del tiempo, y la calidad del script es equivalente dada la corta longitud del output. vLLM no aporta ventaja para este caso de un solo usuario.

**Configurar llama.cpp como reemplazo de Ollama (Agente 1):**

```bash
# Descargar modelo GGUF
huggingface-cli download Qwen/Qwen3.5-4B-GGUF \
  --include "Qwen3.5-4B-Q4_K_M.gguf" \
  --local-dir ~/data/models/gguf/

# Lanzar servidor en puerto alternativo
~/bin/llama-server \
  --model ~/data/models/gguf/Qwen3.5-4B-Q4_K_M.gguf \
  --ctx-size 2048 \
  --n-gpu-layers 99 \
  --port 11435 \
  --host 0.0.0.0 &

# En agent_01_script_generator.py — cambiar URL de Ollama a llama.cpp
# OLLAMA_URL = "http://localhost:11434"   ← original
OLLAMA_URL = "http://localhost:11435"   # ← llama.cpp server
```

### 32.15.3 Extensión a Otros Tipos de Canal

La arquitectura es completamente adaptable. Solo es necesario cambiar el Agente 1 (generador de scripts) y la parrilla de contenidos en Google Sheets:

| Tipo de canal | Cambios en Agente 1 | Parrilla de contenidos |
|---|---|---|
| Recetas de cocina | Prompt: "genera receta de 30 seg para..." | Base de datos de ingredientes |
| Noticias locales | Prompt: "resume esta noticia en 40 seg..." | RSS feed de fuentes locales |
| Frases motivacionales | Prompt: "crea reflexión de 30 seg sobre..." | CSV con temas diarios |
| Tutoriales técnicos | Prompt: "explica concepto X en 45 seg..." | Lista de conceptos |

```python
# En agent_01_script_generator.py — sistema parametrizable
CHANNEL_TYPE = os.getenv("CHANNEL_TYPE", "prayers")  # prayers | cooking | news | motivation

PROMPTS = {
    "prayers": "Genera un script de 30-40 segundos basado en este versículo: {versiculo}",
    "cooking": "Genera un script de 45 segundos para esta receta: {receta}",
    "news":    "Resume esta noticia en 30 segundos para video: {noticia}",
    "motivation": "Crea una reflexión motivacional de 35 segundos sobre: {tema}",
}

prompt = PROMPTS.get(CHANNEL_TYPE, PROMPTS["prayers"])
```

---

## Resumen del Capítulo

El canal **Daily Prayers** es un negocio de contenido completamente automatizado funcionando desde el Jetson AGX Orin 64GB:

- **241 videos** pre-planificados (8 meses de contenido) almacenados en Google Sheets
- **7 agentes** especializados, cada uno haciendo un trabajo, conectados vía N8N y FastAPI
- **100% offline** para producción (Ollama + SD WebUI + kokoro-tts + ffmpeg)
- **API para publicación** (YouTube Data API + TikTok Content Posting API)
- **Costo operativo**: ~$0.90/mes en electricidad para producir 30 videos mensuales
- **Tiempo de producción**: ~22 minutos por video, ejecutado automáticamente a las 7 AM

No se construye un equipo de producción de video — se construyen 7 agentes pequeños, cada uno haciendo un trabajo, y se conectan entre sí. La diferencia con las soluciones cloud es que aquí el servidor está en su escritorio, consume 30 vatios, y sus datos no salen de su red local.

**Este es el poder real de la computación en el borde con IA.**
