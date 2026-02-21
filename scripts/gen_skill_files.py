#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
import re, os, json

SCRIPT_DIR = Path(__file__).parent.parent

def _resolve(p):
    if isinstance(p, str) and (p.startswith('./') or p.startswith('../') or p == '.'):
        return str((SCRIPT_DIR / p).resolve())
    return p

with open(SCRIPT_DIR / 'config.json', encoding='utf-8') as _f:
    _cfg = json.load(_f)
_p = _cfg['paths']

GAME_CORE    = _resolve(_p['game_core'])
GAME_MODS    = _resolve(_p['game_mods'])
PATCHES      = _resolve(_p['patches'])
TRANSLATIONS = _resolve(_p['translations'])
OUTPUT_MODS  = _resolve(_p['output_mods'])
INTERMEDIATE = str(SCRIPT_DIR / 'intermediate')

GAME_SKILLS = os.path.join(GAME_CORE, 'data/characters/skills')
MOD_SKILLS  = os.path.join(PATCHES, 'starsectorkorean/data/characters/skills')
OUT_SKILLS  = os.path.join(PATCHES, 'starsectorkorean/data/characters/skills')

# Korean scopeStr translations for CUSTOM scope skills
CUSTOM_SCOPE_KO = {
    'best_of_the_best': '함대',
    'neural_link': '신경 인터페이스 헐모드가 장착된 함선',
}

def read_skill_file(path):
    """Extract key fields from a skill file"""
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # Extract fields
    result = {}

    # id
    m = re.search(r'"id"\s*:\s*"([^"]+)"', content)
    if m: result['id'] = m.group(1)

    # governingAptitude
    m = re.search(r'"governingAptitude"\s*:\s*"([^"]+)"', content)
    if m: result['governingAptitude'] = m.group(1)

    # compressHullmods
    m = re.search(r'"compressHullmods"\s*:\s*(true|false)', content)
    if m: result['compressHullmods'] = m.group(1)

    # elite
    m = re.search(r'"elite"\s*:\s*(true|false)', content)
    if m: result['elite'] = m.group(1)

    # scope (handle both quoted and unquoted)
    m = re.search(r'(?:^|[^#])\s*"scope"\s*:\s*([A-Z_"]+[A-Z_])', content, re.MULTILINE)
    if m:
        scope_val = m.group(1).strip('"')
        result['scope'] = scope_val

    # scope2
    m = re.search(r'(?:^|[^#])\s*"scope2"\s*:\s*([A-Z_"]+[A-Z_])', content, re.MULTILINE)
    if m:
        scope2_val = m.group(1).strip('"')
        result['scope2'] = scope2_val

    # scopeStr (English)
    m = re.search(r'(?:^|[^#])\s*"scopeStr"\s*:\s*"([^"]+)"', content, re.MULTILINE)
    if m: result['scopeStr_en'] = m.group(1)

    return result


def generate_skill_file(skill_id, fields, korean_scope=None):
    """Generate the mod's skill file content"""
    lines = ['{']

    if 'id' in fields:
        lines.append(f'\t"id":"{fields["id"]}",')

    if 'governingAptitude' in fields:
        lines.append(f'\t"governingAptitude":"{fields["governingAptitude"]}",')

    if 'compressHullmods' in fields:
        lines.append(f'\t"compressHullmods":{fields["compressHullmods"]},')

    if 'elite' in fields:
        lines.append(f'\t"elite":{fields["elite"]},')

    # Scope
    if 'scope' in fields:
        scope_val = fields['scope']
        if korean_scope and fields.get('scope') == 'CUSTOM':
            lines.append(f'\t"scope":CUSTOM,')
            lines.append(f'\t"scopeStr":"{korean_scope}",')
        else:
            # Keep original scope
            if scope_val in ('PILOTED_SHIP', 'ALL_SHIPS', 'ALL_COMBAT_SHIPS',
                             'FLEET', 'ALL_OUTPOSTS', 'GOVERNED_OUTPOST',
                             'SHIP_FIGHTERS', 'ALL_FIGHTERS'):
                lines.append(f'\t"scope":"{scope_val}",')
            else:
                lines.append(f'\t"scope":{scope_val},')

    if 'scope2' in fields and not korean_scope:
        scope2 = fields['scope2']
        if scope2 in ('PILOTED_SHIP', 'ALL_SHIPS', 'ALL_COMBAT_SHIPS',
                      'FLEET', 'ALL_OUTPOSTS', 'GOVERNED_OUTPOST',
                      'SHIP_FIGHTERS', 'SHIP_FIGHTERS', 'CUSTOM'):
            lines.append(f'\t"scope2":"{scope2}",')
        else:
            lines.append(f'\t"scope2":{scope2},')

    # Comment indicating effectGroups are inherited from game
    lines.append('\t# effectGroups는 기본 게임 파일에서 상속됨')
    lines.append('}')

    return '\n'.join(lines) + '\n'


# Process each missing skill
os.makedirs(OUT_SKILLS, exist_ok=True)
created = 0

for fname in os.listdir(GAME_SKILLS):
    if not fname.endswith('.skill'):
        continue

    skill_id = fname[:-6]
    mod_path = os.path.join(MOD_SKILLS, fname)

    # Skip if already in patches
    if os.path.exists(mod_path):
        continue

    game_path = os.path.join(GAME_SKILLS, fname)
    fields = read_skill_file(game_path)

    # Get Korean scope if applicable
    korean_scope = CUSTOM_SCOPE_KO.get(skill_id)

    content = generate_skill_file(skill_id, fields, korean_scope)

    out_path = os.path.join(OUT_SKILLS, fname)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(content)

    created += 1
    if korean_scope:
        print(f"  Created (CUSTOM): {fname} → scopeStr: {korean_scope}")

print(f"\nTotal skill files created: {created}")
print(f"Output: {OUT_SKILLS}")
