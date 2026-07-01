# /tutorial-docx — Generador de Tutoriales IT Profesionales en DOCX

Transforma el archivo de entrada en un tutorial técnico de nivel O'Reilly / Apress en formato `.docx`,
siguiendo la estructura y estética de los PDFs de referencia de Perplexity Computer.

**Archivo de entrada:** $ARGUMENTS

---

## Instrucciones de ejecución

### PASO 1 — Leer el archivo de entrada

Lee el archivo indicado en `$ARGUMENTS` con la herramienta Read. Si la ruta no tiene extensión o
la extensión no es `.md` o `.txt`, prueba añadiendo `.md`. Si el archivo no existe, informa al
usuario y detente.

### PASO 2 — Análisis profundo del contenido

Analiza el contenido completo y extrae:

- **Tema principal** y audiencia objetivo (principiantes, intermedios, avanzados)
- **Tecnologías y herramientas** mencionadas (comandos, versiones, plataformas)
- **Estructura natural**: secciones, subsecciones, bloques de código, tablas, listas
- **Flujo de aprendizaje**: ¿hay dependencias entre pasos? ¿Qué debe hacerse primero?
- **Lagunas de contenido**: ¿qué falta para que sea un tutorial completo y autocontenido?

### PASO 3 — Planificar la estructura del tutorial

Reorganiza el contenido en la siguiente jerarquía **OBLIGATORIA**, enriqueciéndolo con
secciones que falten:

```
PORTADA
  ├── Título principal
  ├── Subtítulo / producto
  ├── Línea de versión (JetPack | Ubuntu | CUDA | etc.)
  └── Bloque de especificaciones del sistema

TABLA DE CONTENIDOS
  └── Lista de Fases con descripción breve

FASE 1: Introducción y Conceptos Clave
  ├── Objetivo de esta fase (caja teal)
  ├── ¿Por qué es importante? (subsección con tabla comparativa si aplica)
  ├── Prerrequisitos (lista de viñetas)
  └── Glosario de conceptos clave (tabla: Término | Definición | Ejemplo)

FASE 2…N: [Contenido del archivo de entrada dividido en fases lógicas]
  Cada fase DEBE contener:
  ├── Objetivo de esta fase (caja teal)
  ├── Introducción breve (1-2 párrafos justificados)
  ├── Sub-secciones temáticas
  └── Pasos numerados, cada uno con:
      ├── Encabezado "Paso N: Título"
      ├── Párrafo explicativo (qué hace y por qué)
      ├── Bloque de código (si aplica)
      ├── Salida esperada (si aplica)
      └── Caja CONSEJO / NOTA / IMPORTANTE / ADVERTENCIA (cuando sea relevante)

FASE FINAL: Verificación y Validación
  ├── Script/secuencia de verificación completa
  ├── Tabla de resultados esperados
  └── Sección de solución de problemas comunes

APÉNDICE A: Referencia Rápida de Comandos
  └── Tabla: Comando | Descripción | Uso

APÉNDICE B: Solución de Problemas
  └── Tabla: Problema | Causa | Solución
```

**Reglas de enriquecimiento de contenido:**
- Si el archivo de entrada tiene secciones `##`, conviértelas en **Fases** numeradas
- Si tiene secciones `###`, conviértelas en **sub-secciones** o **Pasos** según contexto
- Añade siempre una **Fase 1 de introducción** si el archivo no la tiene
- Añade siempre la **Fase de verificación final** si no existe
- Añade siempre los **dos Apéndices** aunque sea con contenido básico
- Cada fase DEBE tener al menos un **objetivo** (texto breve de 1-3 líneas)
- Los bloques de código del original se preservan íntegros en bloques `code`
- Las tablas del original se mapean a tablas estilizadas
- Las listas del original se mapean a `bullets`
- Los `> blockquote` se mapean a cajas `callout` (tipo NOTA por defecto)
- Detecta y marca como IMPORTANTE/ADVERTENCIA/ATENCION los avisos críticos

### PASO 4 — Generar el script Python

Escribe un script Python completo que:

1. Importe el builder desde su ubicación fija:
   ```python
   import sys
   sys.path.insert(0, '/home/sergiok/.claude')
   from tutorial_docx_builder import generate_tutorial_docx
   ```

2. Defina el diccionario `content` con TODO el contenido del tutorial enriquecido.
   - Usa siempre **español perfecto** con tildes (á, é, í, ó, ú), eñes (ñ), signos de
     apertura (¿, ¡) y demás caracteres especiales del español.
   - El título, subtítulo, objetivos, cuerpos de texto, etiquetas de cajas y
     encabezados de tabla deben estar en español formal y profesional.
   - Los comandos y código fuente se dejan en su idioma original (inglés/bash/etc.).
   - Nunca uses palabras como "lorem ipsum" ni contenido de relleno; todo el texto
     debe ser técnicamente preciso y educativamente útil.

3. Construya el `content` dict completo siguiendo exactamente este esquema:

```python
content = {
    "title":    "Título del Tutorial en Español",
    "subtitle": "Plataforma / Producto Principal",
    "version":  "Versión X.Y | Sistema Operativo | Componente",
    "date":     "Mes YYYY",   # Usar fecha actual: Abril 2026
    "specs": {                # dict ordenado con especificaciones relevantes
        "Hardware":    "...",
        "OS":          "...",
        "Kernel":      "...",
        "CUDA":        "...",
        # añadir las que correspondan según el tema
    },
    "chapters": [
        {
            "number":      1,
            "title":       "Nombre de la Fase (sin 'Fase N:' — eso lo pone el builder)",
            "description": "Una línea que aparece en el TOC describiendo esta fase",
            "label":       "Fase",
            "toc_label":   "Fase 1",
            "objective":   "Texto del objetivo: qué aprenderá el lector y para qué sirve esta fase.",
            "sections": [
                # --- Cuerpo de texto ---
                {"type": "body", "content": "Párrafo explicativo en español profesional..."},

                # --- Sub-sección temática ---
                {"type": "subsection", "title": "Título de Sub-sección"},

                # --- Paso numerado ---
                {
                    "type":   "step",
                    "number": "1",
                    "title":  "Verificar el entorno de desarrollo",
                    "body":   "Descripción clara de qué hace este paso y por qué es necesario."
                },

                # --- Bloque de código ---
                {"type": "code", "content": "sudo comando --opcion\n# Comentario explicativo\nresultado"},

                # --- Salida esperada ---
                {"type": "output", "content": "Salida\nEsperada\nDel comando", "label": "Salida esperada:"},

                # --- Caja de aviso ---
                # callout_type: IMPORTANTE | NOTA | CONSEJO | ADVERTENCIA | ATENCIÓN
                {"type": "callout", "callout_type": "IMPORTANTE", "content": "Texto del aviso crítico."},

                # --- Tabla ---
                {
                    "type":    "table",
                    "headers": ["Columna 1", "Columna 2", "Columna 3"],
                    "rows":    [["valor a", "valor b", "valor c"]],
                    "caption": "Tabla N — Descripción (opcional)"
                },

                # --- Lista de viñetas ---
                {"type": "bullets", "items": ["Elemento 1", "Elemento 2"], "numbered": False},

                # --- Lista numerada ---
                {"type": "bullets", "items": ["Primer paso", "Segundo paso"], "numbered": True},
            ]
        },
        # ... más capítulos
    ],
    "appendices": [
        {
            "letter": "A",
            "title":  "Referencia Rápida de Comandos",
            "sections": [
                {
                    "type":    "table",
                    "headers": ["Comando", "Descripción", "Cuándo usarlo"],
                    "rows":    [["comando", "Qué hace", "Situación de uso"]]
                }
            ]
        },
        {
            "letter": "B",
            "title":  "Solución de Problemas Comunes",
            "sections": [
                {
                    "type":    "table",
                    "headers": ["Problema", "Causa probable", "Solución"],
                    "rows":    [["Error X", "Causa Y", "Ejecutar Z"]]
                }
            ]
        }
    ]
}
```

4. Determina la **ruta de salida** del `.docx`:
   - Misma carpeta que el archivo de entrada
   - Mismo nombre de archivo pero con extensión `.docx`
   - Ejemplo: `/ruta/al/archivo.md` → `/ruta/al/archivo.docx`

5. Llama a `generate_tutorial_docx(content, output_path)` al final del script.

### PASO 5 — Ejecutar el script

- Guarda el script Python generado en `/tmp/gen_tutorial_docx.py`
- Ejecútalo con: `python3 /tmp/gen_tutorial_docx.py`
- Si hay errores de Python, analiza el traceback, corrige el script y vuelve a ejecutar
- Máximo 3 intentos de corrección antes de informar al usuario del problema específico

### PASO 6 — Confirmar resultado

Informa al usuario:
- Ruta completa del archivo `.docx` generado
- Número de fases/capítulos
- Número de páginas estimadas (aproximado: contar secciones × 0.8)
- Qué contenido se enriqueció o añadió respecto al original

---

## Estándares de calidad obligatorios

### Idioma
- **Todo el texto narrativo en español perfecto**: tildes, ñ, signos ¿¡, mayúsculas correctas
- Tono: **formal pero accesible**, como un libro técnico de O'Reilly en español
- Verbos en imperativo para los pasos: "Ejecute", "Verifique", "Configure" (tratamiento de usted)
  o "Ejecuta", "Verifica", "Configura" (tuteo) — elige uno y mantenlo coherente en todo el documento
- Sin anglicismos innecesarios: usa "directorio" en vez de "folder", "archivo" en vez de "file",
  "ejecutar" en vez de "correr", "parámetro" en vez de "flag" cuando sea posible

### Contenido técnico
- Cada bloque de código va precedido de un párrafo que explica QUÉ hace y POR QUÉ
- Siempre que haya un comando, mostrar también la salida esperada
- Las cajas de aviso se usan estratégicamente: no más de 2-3 por fase
- Las tablas comparativas ("Con X vs Sin X", "Modo A vs Modo B") añaden valor enorme — úsalas
- Los apéndices deben ser funcionales: referencia rápida real, no placeholder

### Estructura
- Mínimo 3 fases, máximo 12
- Cada fase tiene entre 3 y 15 pasos
- La Fase 1 siempre es "Introducción / Conceptos Clave / Requisitos Previos"
- La última fase siempre es "Verificación, Validación y Solución de Problemas"
- Los apéndices son obligatorios

---

## Ejemplo de uso

```
/tutorial-docx /ruta/al/tutorial.md
/tutorial-docx /home/sergiok/Desktop/JETSON-CONFIG/Tutorial/qwen3_install_cpp.md
```
