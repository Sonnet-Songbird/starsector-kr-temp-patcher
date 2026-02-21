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

# Conservative filter: only keep strings that are CLEARLY display strings
def is_safe_to_translate(s):
    # Multi-word strings (contain spaces) are generally safe
    if ' ' in s:
        # But skip short fragments (2 words or less where first is an article)
        words = s.split()
        if len(words) == 1:
            return False  # shouldn't happen
        return True

    # Single-word strings: only keep capitalized ones that are clearly labels
    # and that aren't game-logic identifiers

    # Must start with uppercase
    if not s[0].isupper():
        return False

    # Contains special chars that indicate it's a display string
    if '%s' in s or '.' in s or '!' in s or '?' in s or ':' in s:
        return True

    # Known safe UI strings (capitalized single words that are clearly display)
    safe_single_words = {
        'Continue', 'Disengage', 'Leave', 'Cancel', 'Accept', 'Decline',
        'Confirm', 'Close', 'Done', 'Back', 'Next', 'Previous', 'Return',
        'Exit', 'Save', 'Load', 'Quit', 'Yes', 'No', 'OK',
        'Elite', 'Unavailable', 'Available', 'Enabled', 'Disabled',
        'Hostile', 'Neutral', 'Friendly', 'Allied', 'Welcoming',
        'Suspicious', 'Inhospitable', 'Vengeful', 'Habitable', 'Decivilized',
        'Irradiated', 'Ancient', 'Bombardment', 'Terraforming',
        'Hyperspace', 'Hyper', 'Flagship', 'Escort', 'Picket', 'Assault',
        'Reserve', 'Support', 'Intercept', 'Defend', 'Capture', 'Retreat',
        'Hold', 'Engage', 'Pursue', 'Flank', 'Harass', 'Scout', 'Patrol',
        'Dock', 'Undock', 'Anchor', 'Approach', 'Withdraw', 'Advance',
        'Warning', 'Error', 'Notice', 'Alert', 'Help', 'Guide',
        'Production', 'Commerce', 'Defense', 'Police', 'Logistics',
        'Deployment', 'Command', 'Refit', 'Salvage', 'Survey',
        'Smuggle', 'Trade', 'Research', 'Development', 'Agriculture',
        'Starport', 'Spaceport', 'Waystation', 'Nebula', 'Battlefield',
        'Mayday', 'Deployed', 'Recovered', 'Disabled', 'Destroyed',
        'Retreated', 'Escaped', 'Captured', 'Scuttled', 'Mothballed',
        'Repaired', 'Restored', 'Modified', 'Upgraded', 'Installed',
        'Removed', 'Added', 'Deleted', 'Created', 'Assigned', 'Transferred',
        'Promoted', 'Demoted', 'Recruited', 'Dismissed', 'Hired', 'Fired',
        'Killed', 'Survived', 'Wounded', 'Healed', 'Completed', 'Failed',
        'Expired', 'Abandoned', 'Pending', 'Unknown', 'Various', 'Multiple',
        'Domestic', 'Sold', 'Bought', 'Stolen', 'Confiscated',
        'Lost', 'Gained', 'Spent', 'Earned', 'Awarded', 'Forfeited',
        'Commerce', 'Administration', 'Terraforming', 'Groundswell',
        'Venting', 'Overload', 'Overloaded',
        'Hegemony', 'Pirates',
    }

    if s in safe_single_words:
        return True

    # Capitalized single words >= 8 chars (likely proper names or long labels)
    if len(s) >= 8 and s[0].isupper():
        return True

    return False

safe = {}
removed = []
for en, ko in translations.items():
    if is_safe_to_translate(en):
        safe[en] = ko
    else:
        removed.append(en)

print(f"Original: {len(translations)}")
print(f"Safe to translate: {len(safe)}")
print(f"Removed as potentially unsafe: {len(removed)}")

# Show what's removed
print("\nSample removed (first 30):")
for s in sorted(removed)[:30]:
    print(f"  {repr(s)}")

# Show what's kept
print("\nSample kept (multi-word, first 20):")
multi = [(k, v) for k, v in safe.items() if ' ' in k][:20]
for k, v in multi:
    print(f"  {repr(k[:60])} → {repr(v[:50])}")

with open(TRANSLATIONS, 'w', encoding='utf-8') as f:
    json.dump(safe, f, ensure_ascii=False, indent=2)

print(f"\nSaved {len(safe)} safe translations")
