# INNOVALABS — Autonomous Literature Factory
## Documentación del Workflow n8n v1.0

> **Target:** NVIDIA Jetson AGX Orin (aarch64, 64GB RAM)  
> **OS:** Ubuntu 22.04.5 LTS / Jetpack 6.2.2 / CUDA 12.6  
> **Orquestador:** n8n (local)  
> **Cola de estados:** Google Sheets API

---

## Mapa de Nodos (21 nodos totales)

```
FLUJO PRINCIPAL (19 nodos)
══════════════════════════

⏰ Cron 6h
  │
  ▼
🔍 Scout — Extraer Tendencias          ← FASE 1: Ingestión
  │
  ▼
⚙️ Parsear Scout Output
  │
  ▼
📋 Sheets — Append Queue
  │
  ▼
📖 Sheets — Leer PENDING               ← FASE 2: Ideación
  │
  ▼
🔀 ¿Hay Pendientes? ──FALSE──▶ ⛔ No Hay Pendientes (fin)
  │TRUE
  ▼
🔒 Sheets — Lock PROCESSING
  │
  ▼
🧠 Estratega — Moraleja (GLM-4.7)
  │
  ▼
⚙️ Parsear Estrategia
  │
  ▼
📐 Arquitecto — Blueprint (DeepSeek-R1)
  │
  ▼
⚙️ Parsear Blueprint
  │
  ▼
📝 Compilar Prompt del Escritor         ← FASE 3: Escritura
  │
  ▼
✍️ Escritor — Qwen3.5-27B (llama-cli)   ⚠️ NODO PESADO (~18GB, 15-30 min)
  │
  ▼
📄 Leer Historia Raw
  │
  ▼
🔎 Editor — Nemotron-3-Nano            ← FASE 4: Pulido
  │
  ▼
⚙️ Componer Markdown Final
  │
  ▼
💾 Guardar Historia .md
  │
  ▼
✅ Sheets — COMPLETED
  │
  ▼
📊 Log de Resumen (fin)


SUB-FLUJO DE ERRORES (6 nodos)
═══════════════════════════════

🚨 Error Trigger
  │
  ▼
⚙️ Diagnosticar Error
  │
  ▼
❌ Sheets — FAILED
  │
  ▼
🔀 ¿Es OOM?
  │TRUE              │FALSE
  ▼                  ▼
🔄 Reiniciar Ollama  📋 Log Error Genérico
```

---

## Detalle por Fase

### FASE 1 — Ingestión (Scout & Queue)

| Nodo | Tipo n8n | Función |
|------|----------|---------|
| ⏰ Cron 6h | `scheduleTrigger` | Dispara cada 6h. Cron: `0 */6 * * *` |
| 🔍 Scout | `executeCommand` | Ejecuta `scout_trends.py`. Timeout: 120s |
| ⚙️ Parsear Scout | `code` | Valida JSON de stdout, genera ID único |
| 📋 Sheets Append | `googleSheets` | Inserta fila con estado `PENDING` |

**Contrato de datos del Scout:**
```json
{
  "tema": "string — tendencia principal detectada",
  "contexto": "string — descripción contextual",
  "fecha": "YYYY-MM-DD"
}
```

**Columnas de Google Sheets (Queue_Historias):**

| Columna | Tipo | Descripción |
|---------|------|-------------|
| ID | string | Identificador único (`H-{timestamp}`) |
| Fecha | date | Fecha de captura |
| Tema | string | Tendencia extraída |
| Contexto | string | Contexto ampliado |
| Estado | enum | `PENDING` / `PROCESSING` / `COMPLETED` / `FAILED` / `FAILED_OOM` |
| Path_Archivo | string | Ruta del .md generado |
| Moraleja | string | Moraleja derivada |
| Blueprint_JSON | string | JSON completo de los 12 pasos |
| Error_Log | string | Mensaje de error si falló |

---

### FASE 2 — Ideación (Agentes Estratega + Arquitecto)

| Nodo | Modelo | RAM Est. | Temperatura | Contexto |
|------|--------|----------|-------------|----------|
| 🧠 Estratega | `glm-4.7-flash` | ~4 GB | 0.7 | 4096 |
| 📐 Arquitecto | `deepseek-r1:8b` | ~6 GB | 0.6 | 8192 |

**Secuencia de carga en VRAM:**
1. Ollama carga `glm-4.7-flash` → inferencia → se mantiene en caché
2. Ollama carga `deepseek-r1:8b` → si no hay espacio, desaloja GLM automáticamente
3. Ambos nodos tienen timeout de 600s para absorber latencia de carga

**Salida del Estratega (JSON):**
```json
{
  "moraleja": "La verdadera riqueza se mide en los puentes que construimos, no en los muros.",
  "conflicto": "Un arquitecto exitoso descubre que su obra maestra destruirá un barrio histórico.",
  "escenario": "Ciudad latinoamericana contemporánea, entre rascacielos y calles coloniales.",
  "tema_original": "gentrificación",
  "tono_sugerido": "reflexivo con toques de realismo mágico"
}
```

**Salida del Arquitecto (JSON array, 12 pasos):**
```json
[
  {
    "paso": 1,
    "nombre_campbell": "El Mundo Ordinario",
    "titulo_capitulo": "Cristal y Concreto",
    "resumen": "Presentamos a Martín, arquitecto de renombre...",
    "personajes": ["Martín", "Lucía (su esposa)"],
    "emocion": "rutina confortable"
  },
  "... (12 objetos total)"
]
```

**Nota sobre DeepSeek-R1:** Este modelo genera tags `<think>...</think>` con su cadena de razonamiento. El nodo "Parsear Blueprint" los elimina automáticamente con regex antes de extraer el JSON.

---

### FASE 3 — Escritura (Nodo Pesado)

| Parámetro llama-cli | Valor | Justificación |
|---------------------|-------|---------------|
| `-m` | `unsloth_Qwen3.5-27B-...Q4_K_XL.gguf` | Modelo cuantizado Q4 para caber en 64GB |
| `-ngl 999` | Todas las capas | Offload completo a GPU (CUDA 12.6) |
| `-c 8192` | Ventana de contexto | Permite historias largas |
| `-n 8000` | Max tokens salida | Techo de generación |
| `--temp 0.8` | Creatividad alta | Prosa literaria requiere variedad |
| `--repeat-penalty 1.1` | Anti-repetición | Evita bucles en generación larga |
| `/no_think` | Inyectado en prompt | Desactiva CoT interno de Qwen3.5 |

**⚠️ RESTRICCIONES CRÍTICAS:**
- Este nodo consume ~18 GB de los 62 GB disponibles
- Tiempo de ejecución estimado: 15-30 minutos
- Bloquea el hilo principal de n8n durante toda la generación
- `maxConcurrency: 1` en settings globales es OBLIGATORIO
- Timeout del nodo: 1800s (30 min)

**Validación post-generación:**
- El nodo "Leer Historia Raw" verifica que el archivo tenga > 500 caracteres
- Si la historia es demasiado corta, lanza error (capturado por Error Trigger)

---

### FASE 4 — Pulido y Despliegue

| Nodo | Modelo | RAM Est. | Temperatura |
|------|--------|----------|-------------|
| 🔎 Editor | `nemotron-3-nano` | ~5 GB | 0.3 |

**Reglas del Editor:**
- ✅ Corregir ortografía, gramática, puntuación
- ✅ Mejorar formato de diálogos (guiones largos —)
- ✅ Eliminar repeticiones
- ❌ NO alterar argumento, personajes ni eventos
- ❌ NO añadir escenas ni metadatos

**Formato del archivo final (.md):**
```markdown
---
title: "Historia H-1710432000000"
fecha_generacion: 2026-03-14
tema: "gentrificación"
moraleja: "La verdadera riqueza se mide en los puentes..."
escenario: "Ciudad latinoamericana contemporánea"
palabras: 4200
agente_escritor: Qwen3.5-27B-UD-Q4
agente_editor: nemotron-3-nano
---

[Contenido de la historia aquí]
```

**Almacenamiento:** `/var/opt/innovalabs/historias/Historia_[ID].md`

---

## Sub-flujo de Errores

El Error Trigger captura fallos de **cualquier** nodo del flujo principal.

**Clasificación automática:**
- `FAILED_OOM` → mensaje contiene "out of memory", "oom" o "killed"
- `FAILED` → cualquier otro error

**Recuperación OOM:**
1. Actualiza Google Sheets con estado `FAILED_OOM`
2. Ejecuta `docker restart ollama`
3. Espera 10s para estabilización
4. El item queda en la cola y puede ser re-procesado en el siguiente ciclo

**Requisito:** n8n debe tener acceso al socket de Docker para poder reiniciar Ollama.

---

## Configuración Previa al Import

### 1. Google Sheets

Crear un spreadsheet con una hoja llamada exactamente `Queue_Historias` y estas columnas en la fila 1:

```
ID | Fecha | Tema | Contexto | Estado | Path_Archivo | Moraleja | Blueprint_JSON | Error_Log
```

Copiar el ID del spreadsheet (de la URL) y reemplazar **todos** los `={{/* REEMPLAZAR CON TU SPREADSHEET ID */}}` en el JSON (hay 6 ocurrencias).

### 2. Credenciales en n8n

- **Google Sheets OAuth2:** Configurar en Settings → Credentials → Google Sheets
- Asegurar que la service account tenga permisos de lectura/escritura en el spreadsheet

### 3. Directorios en el host

```bash
# Directorio de scripts
sudo mkdir -p /opt/innovalabs/scripts
# Directorio de historias
sudo mkdir -p /var/opt/innovalabs/historias
# Permisos para el usuario de n8n
sudo chown -R $USER:$USER /opt/innovalabs /var/opt/innovalabs
```

### 4. Verificar servicios

```bash
# Ollama respondiendo
curl http://localhost:11434/api/tags

# Modelos disponibles (deben estar descargados)
ollama list
# Esperados: glm-4.7-flash, deepseek-r1:8b, nemotron-3-nano

# llama-cli accesible
which llama-cli
# Modelo GGUF presente
ls ~/.cache/llama.cpp/unsloth_Qwen3.5-27B-GGUF_Qwen3.5-27B-UD-Q4_K_XL.gguf
```

### 5. Importar el workflow

```bash
# Opción A: Via CLI de n8n
n8n import:workflow --input=INNOVALABS_Literature_Factory_v1.0.json

# Opción B: Via UI
# → Settings → Import from File → seleccionar el JSON
```

---

## Métricas de Recursos por Ciclo

| Fase | Duración Est. | RAM Pico | GPU |
|------|--------------|----------|-----|
| Scout | 10-30s | < 100 MB | No |
| Estratega | 30-120s | ~4 GB | Sí (Ollama) |
| Arquitecto | 60-180s | ~6 GB | Sí (Ollama) |
| Escritor | 15-30 min | ~18 GB | Sí (CUDA) |
| Editor | 60-180s | ~5 GB | Sí (Ollama) |
| **Total ciclo** | **~20-35 min** | **18 GB pico** | — |

**Producción estimada:** ~4 historias/día (cada 6h) × 365 = **~1,460 historias/año**

---

## Próximos Pasos Recomendados

1. **`scout_trends.py`** — Script de extracción de tendencias (Fase 1)
2. **`docker-compose.yml`** — Stack de servicios (n8n + Ollama)
3. **Retry automático** — Nodo que re-encola items `FAILED` tras X minutos
4. **Dashboard** — Workflow secundario que genera stats desde Google Sheets
5. **Notificaciones** — Integrar Telegram/Discord para alertas de error y completados
