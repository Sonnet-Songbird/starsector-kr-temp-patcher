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

# Filter to really useful UI strings
# - Has space or punctuation
# - Not a pure fragment (doesn't START with space)
# - Not just a short word
# - Length >= 4

good = {}
fragment = {}
for s, info in ui.items():
    # Skip fragments that start with space
    if s.startswith(' ') or s.startswith('\n'):
        fragment[s] = info
        continue
    # Skip strings ending with space only (pure prefix)
    if s.endswith(' ') and len(s.split()) <= 2:
        fragment[s] = info
        continue
    # Skip IDs with underscores
    if '_' in s and ' ' not in s:
        continue
    # Skip slash paths
    if '/' in s:
        continue
    # Must have at least one space or be a complete word >= 5 chars
    has_space = ' ' in s
    if not has_space and len(s) < 5:
        continue
    good[s] = info

print(f"Good UI strings: {len(good)}")
print(f"Fragments: {len(fragment)}")
print("\nTop 30 good UI strings (by frequency):")
sorted_good = sorted(good.items(), key=lambda x: -x[1]['count'])
for s, info in sorted_good[:30]:
    print(f"  [{info['count']}x] {repr(s[:80])}")
