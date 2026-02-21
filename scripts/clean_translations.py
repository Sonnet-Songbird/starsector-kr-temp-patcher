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

TRANSLATIONS = _resolve(_p['translations'])

with open(TRANSLATIONS, 'r', encoding='utf-8') as f:
    translations = json.load(f)

# Remove dangerous short words (single words used as IDs)
dangerous = {
    'bounty', 'cargo', 'contract', 'credits', 'crew', 'faction', 'fleet',
    'fuel', 'intel', 'market', 'mission', 'raid', 'salvage', 'ships',
    'survey', 'weapon', 'weapons',
    # Additional cautious removals - single lowercase words that could be keys
    'battle', 'combat', 'ship', 'fighter', 'drone', 'armor', 'shield', 'flux',
    'supply', 'supplies', 'station', 'planet', 'colony', 'system', 'star',
    'gate', 'sector', 'reputation', 'stability', 'patrol', 'mining', 'farming',
    'trade', 'research', 'science', 'technology', 'engineering', 'military',
    'civilian', 'police', 'memory', 'experience', 'knowledge', 'wisdom',
    'power', 'strength', 'weakness', 'resistance', 'immunity',
    # Short fragments that are incomplete sentences
    'unit', 'units', 'point', 'points', 'slot', 'slots',
    'day', 'days', 'hour', 'hours', 'year', 'years', 'cycle', 'cycles',
    'week', 'weeks', 'month', 'months', 'second', 'seconds', 'minute', 'minutes',
    # Single words that appear in game logic
    'aggressive', 'reckless', 'cautious', 'timid', 'steady',
    'officer', 'officers', 'marines', 'pirate', 'trader', 'explorer',
    'colony', 'colonies',
    # Very generic words that appear as identifiers
    'all', 'any', 'some', 'few', 'many', 'most', 'none', 'unknown', 'various',
    'multiple', 'type', 'name', 'location', 'distance', 'duration', 'range',
    'speed', 'damage', 'attack', 'defense', 'support', 'utility', 'passive',
    'active', 'toggle', 'cooldown', 'charge', 'energy',
    # Single words used in UI but also as identifiers
    'size', 'level', 'cost', 'value', 'price', 'quality', 'efficiency',
    'capacity', 'output', 'input', 'status', 'result', 'report', 'log',
    'note', 'info', 'detail', 'details', 'summary', 'overview', 'progress',
    # Additional game-specific terms that are used as keys
    'fleet', 'battle', 'engagement', 'skirmish', 'ambush', 'siege', 'blockade',
    'invasion', 'rebellion', 'revolt', 'riot', 'war', 'peace', 'truce',
    'alliance', 'treaty', 'agreement', 'negotiation', 'diplomacy',
    'occupation', 'liberation', 'annexation', 'secession', 'independence',
    'sovereignty', 'territory', 'border', 'empire', 'republic', 'democracy',
    'corporation', 'consortium', 'guild', 'union', 'collective', 'organization',
    'government', 'administration', 'intelligence', 'academy', 'university',
    'institute', 'laboratory',
}

# Also remove strings that are clearly game terms/IDs
def is_dangerous(s):
    # Single word (no spaces) that's in dangerous set
    if ' ' not in s and s.lower().rstrip('s') in dangerous:
        return True
    if s in dangerous:
        return True
    # Very short single words (<=6 chars) with no spaces
    if len(s) <= 6 and ' ' not in s and s[0].islower():
        return True
    # Strings that look like category/type identifiers
    if re.match(r'^[a-z][a-z_]*$', s):  # pure lowercase with underscore
        return True
    return False

removed = []
cleaned = {}
for en, ko in translations.items():
    if is_dangerous(en):
        removed.append(en)
    else:
        cleaned[en] = ko

print(f"Original: {len(translations)} translations")
print(f"Removed dangerous: {len(removed)}")
print(f"Cleaned: {len(cleaned)} translations")
print("\nSample removed:")
for s in sorted(removed)[:20]:
    print(f"  '{s}'")

with open(TRANSLATIONS, 'w', encoding='utf-8') as f:
    json.dump(cleaned, f, ensure_ascii=False, indent=2)

print(f"\nSaved {len(cleaned)} translations to {TRANSLATIONS}")
