#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lint_markdown.py — Revisión ortotipográfica y de estilo para capítulos del eBook Jetson.

Uso:
    python book/lint_markdown.py                    # revisa todos los capítulos
    python book/lint_markdown.py <archivo.md>       # revisa un archivo específico
    python book/lint_markdown.py --fix              # aplica correcciones automáticas
"""

import sys
import re
from pathlib import Path

BOOK_DIR = Path(__file__).parent

BOOK_CHAPTERS = [
    'prologo/prologo.md',
    'introduccion/introduccion.md',
    'parte-a/00-parte-a/parte-a.md',
    'parte-a/capitulo-01-inicio-rapido/capitulo-01-inicio-rapido.md',
    'parte-a/capitulo-02-primer-arranque/capitulo-02-primer-arranque.md',
    'parte-a/capitulo-03-configuracion-base/capitulo-03-configuracion-base.md',
    'parte-a/capitulo-04-memoria-almacenamiento/capitulo-04-memoria-almacenamiento.md',
    'parte-a/capitulo-05-rendimiento/capitulo-05-rendimiento.md',
    'parte-a/capitulo-06-shell-entorno/capitulo-06-shell-entorno.md',
    'parte-a/capitulo-07-red/capitulo-07-red.md',
    'parte-a/capitulo-08-acceso-remoto/capitulo-08-acceso-remoto.md',
    'parte-a/capitulo-09-docker/capitulo-09-docker.md',
    'parte-a/capitulo-10-motores-inferencia/capitulo-10-motores-inferencia.md',
    'parte-a/capitulo-11-stack-agentico/capitulo-11-stack-agentico.md',
    'parte-a/capitulo-11a-openclaw/capitulo-11a-openclaw.md',
    'parte-a/capitulo-11b-nemoclaw/capitulo-11b-nemoclaw.md',
    'parte-a/capitulo-11c-open-webui/capitulo-11c-open-webui.md',
    'parte-a/capitulo-11d-tool-calling/capitulo-11d-tool-calling.md',
    'parte-a/capitulo-12-computer-vision/capitulo-12-computer-vision.md',
    'parte-a/capitulo-13-tts-stt/capitulo-13-tts-stt.md',
    'parte-a/capitulo-14-imagen-video/capitulo-14-imagen-video.md',
    'parte-a/capitulo-15-n8n/capitulo-15-n8n.md',
    'parte-a/capitulo-16-benchmarking/capitulo-16-benchmarking.md',
    'parte-a/capitulo-17-produccion/capitulo-17-produccion.md',
    'parte-a/capitulo-18-troubleshooting/capitulo-18-troubleshooting.md',
    'parte-b/00-parte-b/parte-b.md',
    'parte-b/capitulo-19-python-vscode/capitulo-19-python-vscode.md',
    'parte-b/capitulo-20-jetson-containers/capitulo-20-jetson-containers.md',
    'parte-b/capitulo-21-pdf-podcast/capitulo-21-pdf-podcast.md',
    'parte-b/capitulo-22-transcripcion-reuniones/capitulo-22-transcripcion-reuniones.md',
    'parte-b/capitulo-23-agencia-turismo/capitulo-23-agencia-turismo.md',
    'parte-b/capitulo-24-embudo-ventas/capitulo-24-embudo-ventas.md',
    'parte-b/capitulo-25-linkedin/capitulo-25-linkedin.md',
    'parte-b/capitulo-26-asistente-voz/capitulo-26-asistente-voz.md',
    'parte-b/capitulo-27-rag/capitulo-27-rag.md',
    'parte-b/capitulo-28-microservicios-saas/capitulo-28-microservicios-saas.md',
    'parte-c/00-parte-c/parte-c.md',
    'parte-c/capstone-01-agencia-ia/capstone-01-agencia-ia.md',
    'parte-c/capstone-02-automatizacion-video/capstone-02-automatizacion-video.md',
    'parte-c/conclusiones/conclusiones.md',
    'glosario/glosario.md',
    'parte-a/appendix/appendix.md',
]

# Anglicismos y términos a vigilar (sugerencia, no error automático)
ANGLICISMS = {
    r'\blinkear\b': 'vincular',
    r'\bpushear\b': 'publicar / enviar',
    r'\bpullear\b': 'descargar / traer',
    r'\bclonar\b': 'clonar (OK en contexto Docker/Git)',
    r'\bforwardear\b': 'reenviar / redirigir',
    r'\bdebuggear\b': 'depurar',
    r'\btesteando\b': 'probando / verificando',
    r'\bimplementar\b': 'implementar (OK — ya es español)',
}

# Verbos tuteantes que deben ser de usted
TUTEO_PATTERNS = [
    (r'\btienes\b', 'tiene (usted)'),
    (r'\bdebes\b', 'debe (usted)'),
    (r'\bpuedes\b', 'puede (usted)'),
    (r'\bhaces\b', 'hace (usted)'),
    (r'\bescribes\b', 'escribe (usted)'),
    (r'\bejecutas\b', 'ejecuta (usted)'),
    (r'\binstala\b\s+(?!el|la|los|las|un|una)', None),  # OK - imperativo usted
]

# Callouts mal formados
CALLOUT_FIXES = [
    # Normalizar a > **TIPO:** texto
    (re.compile(r'^>\s*\*\*(NOTA|CONSEJO|ADVERTENCIA|IMPORTANTE|ATENCIÓN)\*\*\s+(.+)', re.IGNORECASE),
     lambda m: f'> **{m.group(1).upper()}:** {m.group(2)}'),
]

# Etiquetas de verificación normalizadas
VERIFICATION_TAGS = [
    '[VERIFIED ON JP 7.2]',
    '[NEEDS VERIFICATION]',
    '[TESTED ON JP 6.2]',
]

# Pendientes explícitos
PLACEHOLDER_PATTERN = re.compile(r'\[(?:pendiente|TBD|TODO|FIXME|por completar|por definir)\]', re.IGNORECASE)


class Finding:
    def __init__(self, file, line_num, rule, description, original=None, suggestion=None, auto_fixable=False):
        self.file = file
        self.line_num = line_num
        self.rule = rule
        self.description = description
        self.original = original
        self.suggestion = suggestion
        self.auto_fixable = auto_fixable

    def __str__(self):
        loc = f'{self.file}:{self.line_num}'
        fix_marker = ' [AUTO-FIX]' if self.auto_fixable else ''
        s = f'  [{self.rule}]{fix_marker} {loc} — {self.description}'
        if self.suggestion:
            s += f'\n    → Sugerencia: {self.suggestion}'
        return s


def lint_file(path, apply_fixes=False):
    """Revisa un archivo MD y retorna lista de Finding."""
    text = Path(path).read_text(encoding='utf-8')
    lines = text.split('\n')
    findings = []
    in_code_block = False
    fixed_lines = list(lines)

    rel = str(path)

    for ln, line in enumerate(lines, 1):
        # Rastrear bloques de código — capturar estado ANTES del toggle para R02
        was_in_code = in_code_block
        is_fence_line = line.strip().startswith('```')
        if is_fence_line:
            in_code_block = not in_code_block

        # R02 — Code fence sin lenguaje (solo APERTURA: was_in_code=False, in_code_block=True)
        # Aplicar ANTES del continue para poder detectar fences de apertura sin lenguaje
        if is_fence_line and not was_in_code and in_code_block:
            m_fence = re.match(r'^```\s*$', line)
            if m_fence:
                fixed = '```bash'
                findings.append(Finding(rel, ln, 'R02', 'Code fence sin lenguaje (asume bash)',
                                        original=line, suggestion=fixed, auto_fixable=True))
                if apply_fixes:
                    fixed_lines[ln - 1] = fixed

        # No aplicar reglas de prosa dentro de bloques de código
        if in_code_block:
            continue

        # R01 — Doble espacio
        if '  ' in line and not line.startswith('|'):
            fixed = re.sub(r'  +', ' ', line)
            findings.append(Finding(rel, ln, 'R01', 'Doble espacio detectado',
                                    original=line.rstrip(), suggestion=fixed.rstrip(),
                                    auto_fixable=True))
            if apply_fixes:
                fixed_lines[ln - 1] = fixed

        # R03 — Callout mal formado (sin dos puntos tras el label)
        m_callout = re.match(r'^>\s*\*\*(NOTA|CONSEJO|ADVERTENCIA|IMPORTANTE|ATENCIÓN)\*\*\s+(?!:)(.+)', line, re.IGNORECASE)
        if m_callout:
            fixed = f'> **{m_callout.group(1).upper()}:** {m_callout.group(2)}'
            findings.append(Finding(rel, ln, 'R03', f'Callout {m_callout.group(1)} sin dos puntos',
                                    original=line, suggestion=fixed, auto_fixable=True))
            if apply_fixes:
                fixed_lines[ln - 1] = fixed

        # R04 — Placeholder no reemplazado
        if PLACEHOLDER_PATTERN.search(line):
            findings.append(Finding(rel, ln, 'R04', 'Texto placeholder no reemplazado',
                                    original=line.strip()))

        # R05 — Tuteo (verbos en segunda persona singular)
        if not line.startswith('#') and not line.startswith('>'):
            for pattern, suggestion in TUTEO_PATTERNS[:6]:  # skip last (OK)
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(Finding(rel, ln, 'R05',
                                            f'Posible tuteo: "{re.search(pattern, line, re.IGNORECASE).group(0)}"',
                                            original=line.strip(), suggestion=suggestion))

        # R06 — Anglicismos marcados
        for pattern, sugerencia in ANGLICISMS.items():
            m_angl = re.search(pattern, line, re.IGNORECASE)
            if m_angl and 'OK' not in sugerencia:
                findings.append(Finding(rel, ln, 'R06',
                                        f'Posible anglicismo: "{m_angl.group(0)}"',
                                        suggestion=sugerencia))

        # R07 — Mayúscula incorrecta tras punto (simplificado)
        m_dot = re.search(r'\.\s+([a-záéíóúñü])', line)
        if m_dot and not line.startswith('|') and not line.startswith('>'):
            findings.append(Finding(rel, ln, 'R07',
                                    f'Posible minúscula tras punto: "...{m_dot.group(0)}"',
                                    original=line.strip()))

        # R08 — Comillas tipográficas incorrectas (usar « » o " ")
        if '"' in line and not line.startswith('```') and not in_code_block:
            findings.append(Finding(rel, ln, 'R08',
                                    'Comillas rectas detectadas — considere «comillas angulares» o "tipográficas"',
                                    original=line.strip()))

        # R09 — [VERIFIED] tag malformado
        if '[VERIFIED' in line.upper() or '[NEEDS' in line.upper() or '[TESTED' in line.upper():
            found_valid = any(tag in line for tag in VERIFICATION_TAGS)
            if not found_valid:
                findings.append(Finding(rel, ln, 'R09',
                                        'Etiqueta de verificación con formato no estándar',
                                        original=line.strip(),
                                        suggestion='Use: [VERIFIED ON JP 7.2] | [NEEDS VERIFICATION] | [TESTED ON JP 6.2]'))

    if apply_fixes and findings:
        fixed_text = '\n'.join(fixed_lines)
        Path(path).write_text(fixed_text, encoding='utf-8')

    return findings


def run_lint(target_paths, apply_fixes=False):
    """Ejecuta el linter sobre una lista de paths."""
    total_findings = 0
    files_with_issues = 0
    auto_fixed = 0

    for path in target_paths:
        p = Path(path)
        if not p.exists():
            print(f'  [AVISO] No encontrado: {path}')
            continue

        findings = lint_file(p, apply_fixes=apply_fixes)
        if findings:
            files_with_issues += 1
            total_findings += len(findings)
            print(f'\n{p.name} ({len(findings)} hallazgos):')
            for f in findings:
                print(f)
                if f.auto_fixable and apply_fixes:
                    auto_fixed += 1

    print(f'\n{"="*60}')
    print(f'Archivos con hallazgos: {files_with_issues}')
    print(f'Total de hallazgos:     {total_findings}')
    if apply_fixes:
        print(f'Correcciones aplicadas: {auto_fixed}')
    print(f'{"="*60}')

    return total_findings


if __name__ == '__main__':
    apply_fixes = '--fix' in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith('--')]

    if args:
        paths = args
    else:
        paths = [str(BOOK_DIR / rel) for rel in BOOK_CHAPTERS]

    print(f'Revisando {len(paths)} archivos{"  [MODO FIX ACTIVADO]" if apply_fixes else ""}...')
    total = run_lint(paths, apply_fixes=apply_fixes)
    sys.exit(0 if total == 0 else 1)
