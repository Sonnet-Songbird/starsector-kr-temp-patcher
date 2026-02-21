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

# Further clean: remove rules.csv style entries and other non-JAR content
def is_valid_java_string(s):
    # Java string literals don't contain actual newlines (those would be \n in source)
    # But the decompiler outputs them as actual \n in the text
    # Skip entries that look like rules.csv option lists
    if ':' in s and not s.endswith(':') and not s.startswith('$'):
        # Could be "key:value" format from rules.csv
        # But also could be "Faction: %s" display text
        # Keep if it looks like display text (starts with uppercase/letter)
        first = s.strip()
        if first and first[0] in '0123456789#':
            return False  # Starts with digit/hash = rules.csv entry

    # Skip multiline entries (real Java strings on one line, not multi-line)
    if '\n' in s:
        return False

    # Skip very long strings (> 500 chars) - unlikely to appear as Java literals
    if len(s) > 500:
        return False

    # Skip empty strings
    if not s.strip():
        return False

    return True

cleaned = {k: v for k, v in translations.items() if is_valid_java_string(k)}
removed_count = len(translations) - len(cleaned)
print(f"Original: {len(translations)}")
print(f"Removed invalid: {removed_count}")
print(f"Final valid: {len(cleaned)}")

with open(TRANSLATIONS, 'w', encoding='utf-8') as f:
    json.dump(cleaned, f, ensure_ascii=False, indent=2)

print(f"Saved {TRANSLATIONS}")
