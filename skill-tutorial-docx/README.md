# Skill `/tutorial-docx` para Claude Code

Transforma cualquier archivo Markdown o texto plano en un tutorial IT profesional en `.docx`,
con la calidad y estructura de los libros técnicos de **O'Reilly / Apress**, en **español perfecto**.

## Instalación

```bash
cd skill-tutorial-docx/
chmod +x install.sh
bash install.sh
```

El instalador:
- Verifica Python 3 y pip
- Instala `python-docx` automáticamente
- Copia los archivos a `~/.claude/` y `~/.claude/commands/`
- Ejecuta una prueba de verificación

## Uso

Dentro de una sesión de **Claude Code**:

```
/tutorial-docx /ruta/al/archivo.md
/tutorial-docx /ruta/al/archivo.txt
```

El archivo `.docx` se genera en la misma carpeta que el archivo de entrada.

## Qué genera

| Elemento | Descripción |
|----------|-------------|
| Portada | Fondo teal oscuro, título, subtítulo, bloque de specs del sistema |
| Tabla de contenidos | Fases numeradas con descripción breve |
| Fases / Capítulos | Encabezado grande + objetivo + cuerpo estructurado |
| Pasos numerados | "Paso N: Título" con prefijo en color teal |
| Bloques de código | Fondo oscuro, monoespacio, comentarios en verde |
| Salidas esperadas | Bloque diferenciado para resultados de comandos |
| Cajas de aviso | IMPORTANTE · NOTA · CONSEJO · ADVERTENCIA · ATENCIÓN |
| Tablas estilizadas | Header teal oscuro + filas alternas |
| Apéndices | Referencia rápida de comandos + solución de problemas |
| Encabezado/pie | Título del doc · versión · número de página automático |

## Desinstalación

```bash
bash uninstall.sh
```

## Archivos del paquete

```
skill-tutorial-docx/
├── install.sh                  # Instalador principal
├── uninstall.sh                # Desinstalador
├── requirements.txt            # Dependencias Python
├── tutorial_docx_builder.py   # Módulo Python con el motor de estilos DOCX
├── tutorial-docx.md           # Skill de Claude Code (comando /tutorial-docx)
└── README.md                  # Este archivo
```

## Requisitos

- Python 3.8+
- pip3
- [Claude Code CLI](https://claude.ai/code)
- `python-docx >= 1.1.0` (instalado automáticamente)

## Paleta de colores

Derivada del análisis de los PDFs de referencia generados por Perplexity Computer:

| Token | Hex | Uso |
|-------|-----|-----|
| `TEAL_COVER` | `#0F3D3D` | Fondo de portada |
| `TEAL_ACCENT` | `#1D9CB8` | Encabezados, prefijo "Paso N:" |
| `TEAL_TBL_HDR` | `#1A5A6A` | Fila de encabezado de tablas |
| `CODE_BG` | `#1A2233` | Fondo de bloques de código |
| `CODE_FG` | `#E8EAF0` | Texto de código |
| `CODE_COMMENT` | `#7EC8A0` | Comentarios en código |
