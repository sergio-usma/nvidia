#!/usr/bin/env python3
"""
INNOVALABS — Scout de Tendencias (Fase 1)
==========================================
Extrae tendencias de Google Trends para Colombia, enriquece con contexto
semántico (queries relacionados) y emite un JSON a stdout para n8n.

Contrato de salida (stdout):
{
  "tema": "string — tendencia principal seleccionada",
  "contexto": "string — descripción contextual derivada de queries relacionados",
  "fecha": "YYYY-MM-DD",
  "meta": {
    "region": "colombia",
    "todas_tendencias": ["t1", "t2", ...],
    "queries_relacionados": ["q1", "q2", ...],
    "metodo_seleccion": "trending_searches | fallback_interest"
  }
}

Uso:
  python3 scout_trends.py                    # Modo normal
  python3 scout_trends.py --dry-run          # Test sin llamar a Google
  python3 scout_trends.py --categoria 3      # Forzar categoría (ej: 3=Negocios)
  python3 scout_trends.py --excluir "futbol,reggaeton"  # Filtrar temas

Exit codes:
  0 = OK (JSON emitido a stdout)
  1 = Error recuperable (JSON de error emitido a stderr)
  2 = Error fatal (sin output)

Target: NVIDIA Jetson AGX Orin (aarch64) / Ubuntu 22.04 / Python 3.10+
Consumo RAM estimado: < 100 MB
"""

import json
import os
import sys
import time
import random
import logging
import argparse
from datetime import datetime, timedelta
from typing import Optional

# ─────────────────────────────────────────────
# Configuración
# ─────────────────────────────────────────────

REGION = "colombia"                    # Región para trending_searches
GEO = "CO"                            # Código ISO para interest/queries
IDIOMA = "es"                          # Host language
TIMEZONE_OFFSET = -300                 # UTC-5 (Colombia)
MAX_RETRIES = 3                        # Reintentos ante errores HTTP
RETRY_BASE_DELAY = 5                   # Segundos base entre reintentos
REQUEST_DELAY = (1.5, 3.0)            # Rango de delay entre requests (anti-throttle)

# Categorías temáticas preferidas (para filtrado opcional)
# https://github.com/pat310/google-trends-api/wiki/Google-Trends-Categories
CATEGORIAS_PREFERIDAS = {
    0: "Todas",
    3: "Negocios y finanzas",
    5: "Ciencia",
    7: "Salud",
    16: "Noticias",
    20: "Deportes",
    22: "Entretenimiento",
    31: "Tecnología",
    71: "Alimentación",
    174: "Medio ambiente",
}

# Temas a excluir por defecto (ruido recurrente)
EXCLUSIONES_DEFAULT = [
    # Agregar aquí términos que aparecen constantemente
    # y no generan buenas historias
]

# ─────────────────────────────────────────────
# Logging (solo a stderr, stdout reservado para JSON)
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SCOUT] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("scout")


# ─────────────────────────────────────────────
# Utilidades
# ─────────────────────────────────────────────

def delay_request():
    """Pausa aleatoria entre requests para evitar throttling de Google."""
    wait = random.uniform(*REQUEST_DELAY)
    log.debug(f"Esperando {wait:.1f}s antes del siguiente request...")
    time.sleep(wait)


class SuppressPytrendsStdout:
    """
    Context manager que redirige stdout a /dev/null.
    pytrends imprime mensajes de proxy/error a stdout (bug conocido),
    lo que contamina el JSON que n8n espera en stdout.
    """
    def __enter__(self):
        self._real_stdout = sys.stdout
        self._devnull = open(os.devnull, "w")
        sys.stdout = self._devnull
        return self

    def __exit__(self, *args):
        sys.stdout = self._real_stdout
        self._devnull.close()


def retry_with_backoff(func, description: str = "request"):
    """Ejecuta una función con reintentos exponenciales. Suprime stdout de pytrends."""
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with SuppressPytrendsStdout():
                return func()
        except Exception as e:
            last_error = e
            wait = RETRY_BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 2)
            log.warning(
                f"Intento {attempt}/{MAX_RETRIES} de {description} falló: {e}. "
                f"Reintentando en {wait:.0f}s..."
            )
            time.sleep(wait)
    raise last_error


def limpiar_texto(texto: str) -> str:
    """Limpia y normaliza texto para el JSON de salida."""
    if not texto:
        return ""
    return " ".join(texto.strip().split())


def filtrar_tendencias(tendencias: list, exclusiones: list) -> list:
    """Filtra tendencias excluyendo términos no deseados."""
    if not exclusiones:
        return tendencias
    exclusiones_lower = [e.lower().strip() for e in exclusiones]
    return [
        t for t in tendencias
        if not any(exc in t.lower() for exc in exclusiones_lower)
    ]


# ─────────────────────────────────────────────
# Extracción de tendencias
# ─────────────────────────────────────────────

def obtener_tendencias_diarias(pytrends_client) -> list:
    """
    Obtiene las búsquedas en tendencia del día para Colombia.
    Retorna lista de strings ordenada por relevancia.
    """
    log.info(f"Consultando trending_searches para región: {REGION}")

    def _fetch():
        df = pytrends_client.trending_searches(pn=REGION)
        return df

    df = retry_with_backoff(_fetch, "trending_searches")

    if df is None or df.empty:
        log.warning("trending_searches retornó vacío")
        return []

    # La columna 0 contiene los términos de tendencia
    tendencias = df[0].tolist()
    log.info(f"Tendencias obtenidas: {len(tendencias)} términos")
    return tendencias


def obtener_queries_relacionados(pytrends_client, tema: str) -> dict:
    """
    Obtiene queries relacionados a un tema para enriquecer el contexto.
    Retorna dict con listas 'top' y 'rising'.
    """
    log.info(f"Consultando related_queries para: '{tema}'")
    delay_request()

    def _fetch():
        pytrends_client.build_payload(
            kw_list=[tema],
            geo=GEO,
            timeframe="now 7-d",  # Última semana
        )
        return pytrends_client.related_queries()

    try:
        result = retry_with_backoff(_fetch, "related_queries")
    except Exception as e:
        log.warning(f"No se pudieron obtener queries relacionados: {e}")
        return {"top": [], "rising": []}

    queries = {"top": [], "rising": []}

    if result and tema in result:
        data = result[tema]

        if data.get("top") is not None and not data["top"].empty:
            queries["top"] = data["top"]["query"].head(10).tolist()

        if data.get("rising") is not None and not data["rising"].empty:
            queries["rising"] = data["rising"]["query"].head(10).tolist()

    log.info(
        f"Queries relacionados — top: {len(queries['top'])}, "
        f"rising: {len(queries['rising'])}"
    )
    return queries


def obtener_interes_temporal(pytrends_client, tema: str) -> Optional[str]:
    """
    Obtiene la tendencia temporal del tema (subiendo/bajando/estable).
    Retorna una descripción textual del comportamiento.
    """
    log.info(f"Consultando interest_over_time para: '{tema}'")
    delay_request()

    def _fetch():
        pytrends_client.build_payload(
            kw_list=[tema],
            geo=GEO,
            timeframe="today 1-m",  # Último mes
        )
        return pytrends_client.interest_over_time()

    try:
        df = retry_with_backoff(_fetch, "interest_over_time")
    except Exception as e:
        log.warning(f"No se pudo obtener interés temporal: {e}")
        return None

    if df is None or df.empty or tema not in df.columns:
        return None

    valores = df[tema].values
    if len(valores) < 4:
        return None

    # Comparar la media de la última semana vs las 3 semanas anteriores
    reciente = valores[-7:].mean() if len(valores) >= 7 else valores[-3:].mean()
    anterior = valores[:-7].mean() if len(valores) >= 7 else valores[:-3].mean()

    if anterior == 0:
        return "emergente (sin historial previo significativo)"

    cambio = ((reciente - anterior) / anterior) * 100

    if cambio > 50:
        return f"en fuerte ascenso (+{cambio:.0f}% vs semanas anteriores)"
    elif cambio > 15:
        return f"en ascenso (+{cambio:.0f}% vs semanas anteriores)"
    elif cambio < -30:
        return f"en descenso ({cambio:.0f}% vs semanas anteriores)"
    elif cambio < -10:
        return f"en leve descenso ({cambio:.0f}% vs semanas anteriores)"
    else:
        return "estable (interés sostenido)"


# ─────────────────────────────────────────────
# Construcción de contexto
# ─────────────────────────────────────────────

def construir_contexto(
    tema: str,
    queries: dict,
    tendencia_temporal: Optional[str],
    todas_tendencias: list,
) -> str:
    """
    Construye un párrafo de contexto enriquecido para el agente Estratega.
    """
    partes = []

    # Encabezado
    partes.append(
        f"'{tema}' es una tendencia actual en Colombia detectada "
        f"el {datetime.now().strftime('%d de %B de %Y')}."
    )

    # Tendencia temporal
    if tendencia_temporal:
        partes.append(f"El interés de búsqueda está {tendencia_temporal}.")

    # Queries relacionados (top)
    if queries.get("top"):
        top_str = ", ".join(queries["top"][:5])
        partes.append(
            f"Las búsquedas más frecuentes relacionadas incluyen: {top_str}."
        )

    # Queries emergentes (rising)
    if queries.get("rising"):
        rising_str = ", ".join(queries["rising"][:5])
        partes.append(
            f"Las búsquedas emergentes asociadas son: {rising_str}."
        )

    # Contexto de co-tendencias
    otras = [t for t in todas_tendencias[:10] if t.lower() != tema.lower()]
    if otras:
        otras_str = ", ".join(otras[:5])
        partes.append(
            f"Otras tendencias simultáneas en el país: {otras_str}."
        )

    return " ".join(partes)


# ─────────────────────────────────────────────
# Selección de tema
# ─────────────────────────────────────────────

def seleccionar_tema(tendencias: list, exclusiones: list) -> Optional[str]:
    """
    Selecciona el mejor tema de la lista de tendencias.

    Estrategia:
    - Filtra exclusiones
    - Prefiere temas con >= 2 palabras (más específicos, mejores historias)
    - Si todos son de 1 palabra, toma el primero (más relevante por ranking)
    """
    filtradas = filtrar_tendencias(tendencias, exclusiones)

    if not filtradas:
        log.warning("No quedan tendencias después del filtrado")
        return tendencias[0] if tendencias else None

    # Preferir temas multi-palabra (más contexto narrativo)
    multi_palabra = [t for t in filtradas if len(t.split()) >= 2]
    if multi_palabra:
        seleccion = multi_palabra[0]
        log.info(f"Tema seleccionado (multi-palabra): '{seleccion}'")
        return seleccion

    seleccion = filtradas[0]
    log.info(f"Tema seleccionado (top ranking): '{seleccion}'")
    return seleccion


# ─────────────────────────────────────────────
# Modo fallback (si trending_searches falla)
# ─────────────────────────────────────────────

TEMAS_FALLBACK = [
    "inteligencia artificial",
    "cambio climático Colombia",
    "emprendimiento digital",
    "biodiversidad amazónica",
    "energías renovables",
    "educación rural",
    "migración latinoamericana",
    "seguridad alimentaria",
    "transformación digital",
    "salud mental jóvenes",
    "economía circular",
    "turismo sostenible Colombia",
    "derechos digitales",
    "agricultura urbana",
    "innovación social",
]


def tema_fallback() -> tuple:
    """
    Retorna un tema aleatorio de la lista de fallback
    cuando Google Trends no está disponible.
    """
    tema = random.choice(TEMAS_FALLBACK)
    contexto = (
        f"'{tema}' es un tema de relevancia social contemporánea en Colombia. "
        f"Seleccionado como tema alternativo ante la indisponibilidad temporal "
        f"de Google Trends. Este tema permite generar narrativas con impacto "
        f"social y reflexión ética."
    )
    log.info(f"Usando tema fallback: '{tema}'")
    return tema, contexto


# ─────────────────────────────────────────────
# Modo dry-run (testing)
# ─────────────────────────────────────────────

def generar_dry_run() -> dict:
    """Genera un JSON de prueba sin hacer requests a Google."""
    log.info("Modo dry-run activado — generando datos de prueba")
    return {
        "tema": "inteligencia artificial en la educación",
        "contexto": (
            "'Inteligencia artificial en la educación' es un tema de prueba "
            "generado en modo dry-run. Las búsquedas relacionadas incluyen: "
            "ChatGPT en colegios, tutores IA, aprendizaje personalizado. "
            "Otras tendencias simultáneas: reforma educativa, STEM Colombia."
        ),
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "meta": {
            "region": REGION,
            "todas_tendencias": [
                "inteligencia artificial en la educación",
                "reforma educativa",
                "STEM Colombia",
            ],
            "queries_relacionados": [
                "ChatGPT en colegios",
                "tutores IA",
                "aprendizaje personalizado",
            ],
            "metodo_seleccion": "dry_run",
        },
    }


# ─────────────────────────────────────────────
# Punto de entrada principal
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="INNOVALABS Scout — Extractor de tendencias para Colombia"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generar datos de prueba sin consultar Google Trends",
    )
    parser.add_argument(
        "--categoria",
        type=int,
        default=0,
        help=f"Categoría de Google Trends (0=todas). Opciones: {CATEGORIAS_PREFERIDAS}",
    )
    parser.add_argument(
        "--excluir",
        type=str,
        default="",
        help="Lista de términos a excluir, separados por coma",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Activar logging detallado (DEBUG)",
    )
    args = parser.parse_args()

    if args.verbose:
        log.setLevel(logging.DEBUG)

    # ── Dry-run ──
    if args.dry_run:
        resultado = generar_dry_run()
        print(json.dumps(resultado, ensure_ascii=False))
        return 0

    # ── Preparar exclusiones ──
    exclusiones = EXCLUSIONES_DEFAULT.copy()
    if args.excluir:
        exclusiones.extend([e.strip() for e in args.excluir.split(",") if e.strip()])

    # ── Importar pytrends ──
    try:
        from pytrends.request import TrendReq
    except ImportError:
        log.error(
            "pytrends no está instalado. Ejecuta: pip install pytrends"
        )
        # Usar fallback en lugar de fallar
        tema, contexto = tema_fallback()
        resultado = {
            "tema": tema,
            "contexto": contexto,
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "meta": {
                "region": REGION,
                "todas_tendencias": [tema],
                "queries_relacionados": [],
                "metodo_seleccion": "fallback_no_pytrends",
            },
        }
        print(json.dumps(resultado, ensure_ascii=False))
        return 0

    # ── Inicializar cliente ──
    # NOTA: pytrends imprime mensajes de proxy a stdout (bug conocido).
    # Redirigimos stdout temporalmente a /dev/null durante la inicialización
    # para evitar contaminar el JSON de salida que n8n espera.
    log.info("Inicializando cliente de Google Trends...")
    try:
        with SuppressPytrendsStdout():
            pytrends = TrendReq(
                hl=IDIOMA,
                tz=TIMEZONE_OFFSET,
                timeout=(10, 30),  # (connect_timeout, read_timeout)
                retries=2,
                backoff_factor=0.5,
            )
    except Exception as e:
        log.error(f"Error inicializando TrendReq: {e}")
        tema, contexto = tema_fallback()
        resultado = {
            "tema": tema,
            "contexto": contexto,
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "meta": {
                "region": REGION,
                "todas_tendencias": [tema],
                "queries_relacionados": [],
                "metodo_seleccion": "fallback_init_error",
            },
        }
        print(json.dumps(resultado, ensure_ascii=False))
        return 0

    # ── Fase A: Obtener tendencias diarias ──
    try:
        tendencias = obtener_tendencias_diarias(pytrends)
    except Exception as e:
        log.error(f"Error obteniendo tendencias: {e}")
        tendencias = []

    metodo = "trending_searches"
    contexto_fallback = None

    # ── Fase B: Seleccionar tema ──
    if tendencias:
        tema = seleccionar_tema(tendencias, exclusiones)
        if not tema:
            tema, contexto_fallback = tema_fallback()
            metodo = "fallback_filtrado_vacio"
    else:
        log.warning("Sin tendencias disponibles, usando fallback")
        tema, contexto_fallback = tema_fallback()
        tendencias = [tema]
        metodo = "fallback_sin_tendencias"

    # ── Fase C: Enriquecer contexto ──
    if metodo == "trending_searches":
        # Obtener queries relacionados
        queries = obtener_queries_relacionados(pytrends, tema)

        # Obtener tendencia temporal
        tendencia_temporal = obtener_interes_temporal(pytrends, tema)

        # Construir contexto enriquecido
        contexto = construir_contexto(tema, queries, tendencia_temporal, tendencias)

        queries_list = queries.get("top", []) + queries.get("rising", [])
    else:
        # En modo fallback, el contexto ya fue generado
        if contexto_fallback is not None:
            contexto = contexto_fallback
        else:
            contexto = f"'{tema}' es un tema de relevancia actual en Colombia."
        queries_list = []

    # ── Fase D: Emitir resultado ──
    resultado = {
        "tema": limpiar_texto(tema),
        "contexto": limpiar_texto(contexto),
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "meta": {
            "region": REGION,
            "todas_tendencias": tendencias[:20],
            "queries_relacionados": queries_list[:15],
            "metodo_seleccion": metodo,
        },
    }

    # Validación final
    if not resultado["tema"]:
        log.error("Resultado vacío después de todo el procesamiento")
        tema, contexto = tema_fallback()
        resultado["tema"] = tema
        resultado["contexto"] = contexto
        resultado["meta"]["metodo_seleccion"] = "fallback_validacion_final"

    # JSON a stdout (esto es lo que n8n captura)
    print(json.dumps(resultado, ensure_ascii=False))

    log.info(f"Scout completado. Tema: '{resultado['tema']}' [{metodo}]")
    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        log.info("Interrumpido por usuario")
        sys.exit(2)
    except Exception as e:
        log.critical(f"Error fatal no manejado: {e}", exc_info=True)
        # Emitir JSON de error para que n8n pueda procesarlo
        error_output = {
            "tema": "",
            "contexto": "",
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "meta": {
                "region": REGION,
                "todas_tendencias": [],
                "queries_relacionados": [],
                "metodo_seleccion": f"error_fatal: {str(e)[:200]}",
            },
        }
        print(json.dumps(error_output, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
