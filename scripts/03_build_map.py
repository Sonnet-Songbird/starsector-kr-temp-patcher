#!/usr/bin/env python3
"""
03_build_map.py - 번역 매핑 추출
기존 모드의 데이터 파일에서 영어→한국어 번역 매핑 구축

Sources:
  - data/strings/strings.json (영어→한국어 대응)
  - data/strings/tooltips.json
  - data/characters/skills/skill_data.csv
  - data/strings/descriptions.csv

Output: intermediate/translation_map.json
"""

from pathlib import Path
import re, json, csv, os, sys

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
INTERMEDIATE = str(SCRIPT_DIR / 'intermediate')

GAME_BASE = GAME_CORE
MOD_BASE  = os.path.join(GAME_MODS, 'starsectorkorean')
OUT_FILE  = os.path.join(INTERMEDIATE, 'translation_map.json')


def strip_comments(text):
    """Remove # comment lines from Starsector JSON"""
    lines = []
    for line in text.split('\n'):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        lines.append(line)
    return '\n'.join(lines)


def load_starsector_json(filepath):
    """Load a Starsector JSON file (with # comments and trailing commas)"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    content = re.sub(r'^\s*#[^\n]*\n', '\n', content, flags=re.MULTILINE)
    content = re.sub(r',(\s*[}\]])', r'\1', content)
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"JSON parse error in {filepath}: {e}", file=sys.stderr)
        return {}


def flatten_json(obj, prefix=''):
    """Flatten nested JSON to {key: value} for leaf string values"""
    result = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_key = f"{prefix}.{k}" if prefix else k
            result.update(flatten_json(v, new_key))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_key = f"{prefix}[{i}]"
            result.update(flatten_json(v, new_key))
    elif isinstance(obj, str):
        result[prefix] = obj
    return result


def build_string_map(game_file, mod_file):
    """Build English→Korean mapping from game+mod JSON pair"""
    game_data = load_starsector_json(game_file)
    mod_data  = load_starsector_json(mod_file)

    game_flat = flatten_json(game_data)
    mod_flat  = flatten_json(mod_data)

    mapping = {}
    for key in game_flat:
        if key not in mod_flat:
            continue
        en = game_flat[key].strip()
        ko = mod_flat[key].strip()
        if not en or not ko:
            continue
        if en == ko:
            continue
        if not re.search(r'[\uAC00-\uD7A3]', ko):
            continue
        mapping[en] = ko

    return mapping


def build_csv_map(game_csv, mod_csv, name_col_game=1, name_col_mod=1):
    """Build English→Korean mapping from CSV files matching by id (col 0)"""
    def read_csv(filepath):
        rows = {}
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or row[0].strip().startswith('#') or not row[0].strip():
                    continue
                row_id = row[0].strip()
                rows[row_id] = row
        return rows

    game_rows = read_csv(game_csv)
    mod_rows  = read_csv(mod_csv)

    mapping = {}
    for row_id in game_rows:
        if row_id not in mod_rows:
            continue
        g_row = game_rows[row_id]
        m_row = mod_rows[row_id]

        max_col = min(len(g_row), len(m_row))
        for col in range(1, max_col):
            en = g_row[col].strip() if col < len(g_row) else ''
            ko = m_row[col].strip() if col < len(m_row) else ''
            if not en or not ko or en == ko:
                continue
            if not re.search(r'[\uAC00-\uD7A3]', ko):
                continue
            if len(en) >= 3:
                mapping[en] = ko

    return mapping


def main():
    os.makedirs(INTERMEDIATE, exist_ok=True)

    translation_map = {}
    stats = {}

    # 1. strings.json
    game_str = f'{GAME_BASE}/data/strings/strings.json'
    mod_str  = f'{MOD_BASE}/data/strings/strings.json'
    if os.path.exists(game_str) and os.path.exists(mod_str):
        m = build_string_map(game_str, mod_str)
        translation_map.update(m)
        stats['strings.json'] = len(m)
        print(f"strings.json: {len(m)} translations")

    # 2. tooltips.json
    game_tt = f'{GAME_BASE}/data/strings/tooltips.json'
    mod_tt  = f'{MOD_BASE}/data/strings/tooltips.json'
    if os.path.exists(game_tt) and os.path.exists(mod_tt):
        m = build_string_map(game_tt, mod_tt)
        translation_map.update(m)
        stats['tooltips.json'] = len(m)
        print(f"tooltips.json: {len(m)} translations")

    # 3. skill_data.csv
    game_sk = f'{GAME_BASE}/data/characters/skills/skill_data.csv'
    mod_sk  = f'{MOD_BASE}/data/characters/skills/skill_data.csv'
    if os.path.exists(game_sk) and os.path.exists(mod_sk):
        m = build_csv_map(game_sk, mod_sk)
        translation_map.update(m)
        stats['skill_data.csv'] = len(m)
        print(f"skill_data.csv: {len(m)} translations")

    # 4. descriptions.csv
    game_desc = f'{GAME_BASE}/data/strings/descriptions.csv'
    mod_desc  = f'{MOD_BASE}/data/strings/descriptions.csv'
    if os.path.exists(game_desc) and os.path.exists(mod_desc):
        m = build_csv_map(game_desc, mod_desc)
        translation_map.update(m)
        stats['descriptions.csv'] = len(m)
        print(f"descriptions.csv: {len(m)} translations")

    # 5. Scan all other CSV files in mod that override game CSVs
    for dirpath, dirnames, filenames in os.walk(MOD_BASE + '/data'):
        for fname in filenames:
            if not fname.endswith('.csv'):
                continue
            mod_path  = os.path.join(dirpath, fname)
            game_path = mod_path.replace(MOD_BASE, GAME_BASE)
            if not os.path.exists(game_path):
                continue
            key = fname
            if key in stats:
                continue
            m = build_csv_map(game_path, mod_path)
            if m:
                translation_map.update(m)
                stats[key] = len(m)
                print(f"{fname}: {len(m)} translations")

    print(f"\nTotal translation pairs: {len(translation_map)}")

    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(translation_map, f, ensure_ascii=False, indent=2)

    print(f"Written to: {OUT_FILE}")

    sample = list(translation_map.items())[:10]
    print("\nSample translations:")
    for en, ko in sample:
        print(f"  {repr(en[:50])} → {repr(ko[:50])}")


if __name__ == '__main__':
    main()
