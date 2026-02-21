#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
import re, json, os

SCRIPT_DIR = Path(__file__).parent.parent

def _resolve(p):
    if isinstance(p, str) and (p.startswith('./') or p.startswith('../') or p == '.'):
        return str((SCRIPT_DIR / p).resolve())
    return p

with open(SCRIPT_DIR / 'config.json', encoding='utf-8') as _f:
    _cfg = json.load(_f)
_p = _cfg['paths']

GAME_CORE = _resolve(_p['game_core'])
GAME_MODS = _resolve(_p['game_mods'])

def extract_keys(filepath):
    """Extract all string keys from a Starsector JSON file (with comments)"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    # Find all "key":"value" patterns
    keys = re.findall(r'"([^"]+)"\s*:', content)
    return set(keys)

game_keys = extract_keys(os.path.join(GAME_CORE, 'data/strings/strings.json'))
mod_keys  = extract_keys(os.path.join(GAME_MODS, 'starsectorkorean/data/strings/strings.json'))

game_only = game_keys - mod_keys
mod_only  = mod_keys - game_keys

print(f"Game strings.json keys: {len(game_keys)}")
print(f"Mod strings.json keys: {len(mod_keys)}")
print(f"In game but not mod: {len(game_only)}")
for k in sorted(game_only)[:10]:
    print(f"  MISSING: {k}")
print(f"In mod but not game: {len(mod_only)}")
for k in sorted(mod_only)[:5]:
    print(f"  EXTRA: {k}")
