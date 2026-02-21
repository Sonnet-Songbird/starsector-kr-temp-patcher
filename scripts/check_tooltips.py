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
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    keys = re.findall(r'"([^"]+)"\s*:', content)
    return set(keys)

# Check tooltips
game_keys = extract_keys(os.path.join(GAME_CORE, 'data/strings/tooltips.json'))
mod_keys  = extract_keys(os.path.join(GAME_MODS, 'starsectorkorean/data/strings/tooltips.json'))
game_only = game_keys - mod_keys
print(f"tooltips.json - Game: {len(game_keys)}, Mod: {len(mod_keys)}, Missing in mod: {len(game_only)}")
for k in sorted(game_only)[:10]:
    print(f"  MISSING: {k}")
