#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
import os, re, json

SCRIPT_DIR = Path(__file__).parent.parent

def _resolve(p):
    if isinstance(p, str) and (p.startswith('./') or p.startswith('../') or p == '.'):
        return str((SCRIPT_DIR / p).resolve())
    return p

with open(SCRIPT_DIR / 'config.json', encoding='utf-8') as _f:
    _cfg = json.load(_f)
_p = _cfg['paths']

NEW_SRC = str(SCRIPT_DIR / 'api_src')

# Check how short single-word strings are used in the code
dangerous_words = ['memory', 'battle', 'fleet', 'crew', 'credits', 'mission',
                   'contract', 'bounty', 'survey', 'salvage', 'patrol', 'raid',
                   'ship', 'ships', 'fighter', 'drone', 'weapon', 'weapons',
                   'armor', 'shield', 'flux', 'supply', 'fuel', 'cargo',
                   'reputation', 'faction', 'planet', 'colony', 'market',
                   'station', 'system', 'star', 'gate', 'sector', 'intel',
                   'combat', 'stability', 'unit', 'units', 'point', 'points',
                   'slot', 'slots', 'day', 'days', 'hour', 'hours', 'year', 'years']

# Find unsafe usages
unsafe_patterns = [
    r'\.equals\s*\(\s*"{}"\s*\)',
    r'\.equalsIgnoreCase\s*\(\s*"{}"\s*\)',
    r'\.get\s*\(\s*"{}"\s*\)',
    r'\.put\s*\(\s*"{}"\s*,',
    r'\.containsKey\s*\(\s*"{}"\s*\)',
    r'return\s+"{}"\s*;',
    r'case\s+"{}"\s*:',
]

dangerous = set()

for word in dangerous_words:
    for root, dirs, files in os.walk(NEW_SRC):
        if word in dangerous:
            break
        for fname in files:
            if not fname.endswith('.java'):
                continue
            path = os.path.join(root, fname)
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            for pat_template in unsafe_patterns:
                pat = pat_template.format(re.escape(word))
                if re.search(pat, content):
                    dangerous.add(word)
                    print(f"DANGEROUS: '{word}' used as ID/key in {fname}")
                    break
            if word in dangerous:
                break

print(f"\nDangerous short words (should NOT be translated): {len(dangerous)}")
for w in sorted(dangerous):
    print(f"  '{w}'")
