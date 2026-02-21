#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
import json, os, re

SCRIPT_DIR = Path(__file__).parent.parent

def _resolve(p):
    if isinstance(p, str) and (p.startswith('./') or p.startswith('../') or p == '.'):
        return str((SCRIPT_DIR / p).resolve())
    return p

with open(SCRIPT_DIR / 'config.json', encoding='utf-8') as _f:
    _cfg = json.load(_f)
_p = _cfg['paths']

INTERMEDIATE = str(SCRIPT_DIR / 'intermediate')

with open(os.path.join(INTERMEDIATE, 'untranslated.json'), 'r', encoding='utf-8') as f:
    data = json.load(f)

ui = data['ui_strings']

good = {}
for s, info in ui.items():
    if s.startswith(' ') or s.startswith('\n'):
        continue
    if s.endswith(' ') and len(s.split()) <= 2:
        continue
    if '_' in s and ' ' not in s:
        continue
    if '/' in s:
        continue
    if ' ' not in s and len(s) < 5:
        continue
    good[s] = info

def score(item):
    s, info = item
    word_count = len(s.split())
    return info['count'] * min(word_count, 5)

sorted_good = sorted(good.items(), key=lambda x: -score(x))

# Output all for review
out = []
for s, info in sorted_good[:300]:
    out.append({'en': s, 'count': info['count'], 'context': info['sample_line'][:100]})

out_file = os.path.join(INTERMEDIATE, 'strings_to_translate.json')
os.makedirs(INTERMEDIATE, exist_ok=True)
with open(out_file, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print(f"Wrote {len(out)} strings to strings_to_translate.json")
