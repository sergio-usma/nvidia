#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
renumber_sections.py — Corrige la numeración de secciones en todos los capítulos.

Los archivos .md tienen prefijos de sección que no coinciden con el número
de capítulo actual (p.ej. cap-10 usa 12.X en lugar de 10.X). Este script
reemplaza solo los prefijos en líneas de heading (##, ###, ####), respetando
code blocks.

Uso:
    python book/renumber_sections.py --dry-run   # muestra cambios sin aplicar
    python book/renumber_sections.py              # aplica cambios
"""

import sys
import re
from pathlib import Path

BOOK_DIR = Path(__file__).parent

# Mapeo: clave del directorio → (prefijo_viejo, prefijo_nuevo)
# None = sin cambio
RENUMBER_MAP = {
    'capitulo-01':  ('0',   '1'),
    'capitulo-02':  ('1',   '2'),
    'capitulo-03':  ('2',   '3'),
    'capitulo-04':  None,            # 4.X ya correcto
    'capitulo-05':  ('3',   '5'),
    'capitulo-06':  ('5',   '6'),
    'capitulo-07':  ('6',   '7'),
    'capitulo-08':  ('7',   '8'),
    'capitulo-09':  ('8',   '9'),
    'capitulo-10':  ('12',  '10'),
    'capitulo-11':  ('13',  '11'),
    'capitulo-11a': ('13A', '11A'),
    'capitulo-11b': ('13B', '11B'),
    'capitulo-11c': ('13C', '11C'),
    'capitulo-11d': ('13D', '11D'),
    'capitulo-12':  ('28',  '12'),
    'capitulo-13':  ('29',  '13'),
    'capitulo-14':  ('19',  '14'),
    'capitulo-15':  ('27',  '15'),
    'capitulo-16':  ('14',  '16'),
    'capitulo-17':  ('15',  '17'),
    'capitulo-18':  ('16',  '18'),
    'capitulo-19':  ('17',  '19'),
    'capitulo-20':  ('18',  '20'),
    'capitulo-21':  ('19',  '21'),
    'capitulo-22':  ('20',  '22'),
    'capitulo-23':  ('21',  '23'),
    'capitulo-24':  ('22',  '24'),
    'capitulo-25':  ('23',  '25'),
    'capitulo-26':  ('24',  '26'),
    'capitulo-27':  ('25',  '27'),
    'capitulo-28':  ('30',  '28'),
    'capstone-01':  ('31',  'C1'),
    'capstone-02':  ('32',  'C2'),
}


def _chapter_key(md_path: Path) -> str | None:
    """Extrae la clave de capítulo del nombre del directorio padre."""
    parent = md_path.parent.name
    for key in RENUMBER_MAP:
        if key in parent:
            return key
    return None


def _heading_re(old: str) -> re.Pattern:
    """Regex que captura solo headings con el prefijo viejo."""
    return re.compile(
        r'^(#{1,4}\s+)' + re.escape(old) + r'(\.\d)',
        re.IGNORECASE
    )


def renumber_file(md_path: Path, dry_run: bool = False) -> int:
    """Renumera las secciones de un archivo .md. Retorna el número de reemplazos."""
    key = _chapter_key(md_path)
    if key is None or RENUMBER_MAP[key] is None:
        return 0

    old, new = RENUMBER_MAP[key]
    pattern = _heading_re(old)
    replacement = r'\g<1>' + new + r'\g<2>'

    text = md_path.read_text(encoding='utf-8')
    lines = text.split('\n')
    new_lines = []
    changes = 0
    in_code_block = False

    for line in lines:
        # Rastrear bloques de código para no tocar su contenido
        stripped = line.strip()
        if stripped.startswith('```'):
            in_code_block = not in_code_block

        if not in_code_block and pattern.match(line):
            new_line = pattern.sub(replacement, line)
            if new_line != line:
                changes += 1
                if dry_run:
                    print(f'  - {line.rstrip()}')
                    print(f'  + {new_line.rstrip()}')
            new_lines.append(new_line)
        else:
            new_lines.append(line)

    if changes and not dry_run:
        md_path.write_text('\n'.join(new_lines), encoding='utf-8')

    return changes


def main():
    dry_run = '--dry-run' in sys.argv

    if dry_run:
        print('MODO DRY-RUN — sin cambios reales\n')

    all_md = sorted(BOOK_DIR.rglob('*.md'))
    total_changes = 0
    total_files = 0

    for md_path in all_md:
        # Ignorar archivos fuera de los capítulos conocidos
        key = _chapter_key(md_path)
        if key is None:
            continue

        if dry_run:
            mapping = RENUMBER_MAP.get(key)
            if mapping:
                old, new = mapping
                print(f'\n[{key}] {md_path.name}: {old}.X → {new}.X')

        changes = renumber_file(md_path, dry_run=dry_run)
        if changes:
            total_files += 1
            total_changes += changes
            if not dry_run:
                print(f'  ✓ {md_path.name}: {changes} reemplazos')

    print(f'\n{"DRY-RUN " if dry_run else ""}Total: {total_changes} reemplazos en {total_files} archivos.')


if __name__ == '__main__':
    main()
