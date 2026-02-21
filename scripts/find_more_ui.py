#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path
import json, os, re, zipfile, struct
from collections import defaultdict

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
TRANSLATIONS = _resolve(_p['translations'])
OUTPUT_MODS  = _resolve(_p['output_mods'])
INTERMEDIATE = str(SCRIPT_DIR / 'intermediate')

def _load_all_translations():
    merged = {}
    for key in ['translations', 'api_trans', 'obf_trans']:
        p = _resolve(_p.get(key, ''))
        if p and os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                merged.update(json.load(f))
    return merged

OBF_BAK = os.path.join(GAME_CORE, 'starfarer_obf.jar.bak')
API_BAK = os.path.join(GAME_CORE, 'starfarer.api.jar.bak')

trans = _load_all_translations()

def extract_utf8_strings(jar_path):
    strings = set()
    with zipfile.ZipFile(jar_path, 'r') as zf:
        for name in zf.namelist():
            if not name.endswith('.class'):
                continue
            data = zf.read(name)
            if len(data) < 10:
                continue
            if struct.unpack_from('>I', data, 0)[0] != 0xCAFEBABE:
                continue
            count = struct.unpack_from('>H', data, 8)[0]
            pos = 10
            i = 1
            while i < count and pos < len(data):
                tag = data[pos]; pos += 1
                if tag == 1:
                    length = struct.unpack_from('>H', data, pos)[0]; pos += 2
                    raw = data[pos:pos + length]; pos += length
                    try:
                        strings.add(raw.decode('utf-8', errors='replace'))
                    except:
                        pass
                elif tag in (5, 6):
                    pos += 8; i += 1
                elif tag in (3, 4):
                    pos += 4
                elif tag in (7, 8, 16, 19, 20):
                    pos += 2
                elif tag in (9, 10, 11, 12, 17, 18):
                    pos += 4
                elif tag == 15:
                    pos += 3
                else:
                    break
                i += 1
    return strings

def has_korean(s):
    return any(0xAC00 <= ord(c) <= 0xD7A3 for c in s)

def is_clean_label(s):
    if not (4 <= len(s) <= 45): return False
    if not re.match(r'^[A-Z][a-z]', s): return False
    if ' ' not in s: return False
    if re.search(r'[_\$\[{(\\]', s): return False
    if re.search(r'\.(java|class|png|csv|json)$', s): return False
    # camelCase 연속
    if re.match(r'^[A-Z][a-zA-Z]{2,}[A-Z][a-zA-Z]', s) and ' ' not in s[:8]:
        return False
    return True

print("추출 중...")
all_strings = extract_utf8_strings(OBF_BAK) | extract_utf8_strings(API_BAK)
untrans_all = {s.strip() for s in all_strings
               if s.strip() not in trans and not has_korean(s.strip())}

good_labels = [s for s in untrans_all if is_clean_label(s)]
print(f"깔끔한 미번역 레이블: {len(good_labels)}개")

trans_kr = {k: v for k, v in trans.items() if has_korean(v) and len(k) <= 45}

kw = {
    "항법/탐색":  ['nav', 'jump', 'gate', 'relay', 'beacon', 'sensor', 'comm'],
    "식민지 상태": ['colony', 'stability', 'hazard', 'growth', 'admin', 'governor', 'crisis'],
    "경제/무역":  ['trade', 'export', 'import', 'market', 'income', 'profit', 'price'],
    "함선 제원":  ['speed', 'range', 'damage', 'armor', 'hull', 'shield', 'weapon',
                   'peak', 'burn', 'flux', 'crew', 'cargo', 'fuel', 'supply',
                   'ordnance', 'flight'],
    "인텔/임무":  ['intel', 'mission', 'bounty', 'contract', 'report',
                   'contact', 'location', 'deliver'],
    "전투/작전":  ['combat', 'battle', 'attack', 'defend', 'engage', 'fleet',
                   'deploy', 'reinforce', 'assault', 'raid', 'blockade'],
    "헐모드":     ['hullmod', 'installed', 'capacitor', 'vent', 'integrated'],
}

results = {}
for cat, words in kw.items():
    matches = sorted(set(
        s for s in good_labels
        if any(w in s.lower() for w in words)
    ))
    if matches:
        results[cat] = matches

for cat, items in results.items():
    print(f"\n[{cat}] {len(items)}개:")
    for s in items[:20]:
        sim = next(((k, v) for k, v in trans_kr.items()
                    if any(w in k.lower() for w in re.findall(r'[a-z]{4,}', s.lower()))), None)
        note = f"  ← {repr(sim[0])}" if sim else ""
        print(f"  {repr(s)}{note}")

all_found = sorted(set(s for items in results.values() for s in items))
out_file = os.path.join(INTERMEDIATE, 'more_labels.json')
os.makedirs(INTERMEDIATE, exist_ok=True)
with open(out_file, 'w', encoding='utf-8') as f:
    json.dump(all_found, f, ensure_ascii=False, indent=2)
print(f"\n총 {len(all_found)}개 저장: more_labels.json")
