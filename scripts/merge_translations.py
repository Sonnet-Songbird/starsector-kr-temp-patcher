#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
import json, os

SCRIPT_DIR = Path(__file__).parent.parent

def _resolve(p):
    if isinstance(p, str) and (p.startswith('./') or p.startswith('../') or p == '.'):
        return str((SCRIPT_DIR / p).resolve())
    return p

with open(SCRIPT_DIR / 'config.json', encoding='utf-8') as _f:
    _cfg = json.load(_f)
_p = _cfg['paths']

TRANSLATIONS = _resolve(_p['translations'])
INTERMEDIATE = str(SCRIPT_DIR / 'intermediate')

# Load base translations from data files
translation_map_path = os.path.join(INTERMEDIATE, 'translation_map.json')
with open(translation_map_path, 'r', encoding='utf-8') as f:
    base = json.load(f)

# Load manually crafted translations
with open(TRANSLATIONS, 'r', encoding='utf-8') as f:
    manual = json.load(f)

# Merge: manual overrides base
merged = {**base, **manual}

print(f"Base translations: {len(base)}")
print(f"Manual translations: {len(manual)}")
print(f"Merged total: {len(merged)}")

# Save merged back to common.json (TRANSLATIONS)
with open(TRANSLATIONS, 'w', encoding='utf-8') as f:
    json.dump(merged, f, ensure_ascii=False, indent=2)

print(f"Saved to {TRANSLATIONS}")
