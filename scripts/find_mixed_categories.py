#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
find_mixed_categories.py
번역된 것과 미번역이 혼재하는 카테고리 찾기
"""

from pathlib import Path
import json, os, re, zipfile, struct, sys
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

OBF_BAK  = os.path.join(GAME_CORE, 'starfarer_obf.jar.bak')
API_BAK  = os.path.join(GAME_CORE, 'starfarer.api.jar.bak')
OUT_FILE = os.path.join(INTERMEDIATE, 'mixed_categories.json')

trans = _load_all_translations()

def extract_utf8_strings(jar_path):
    strings = []
    try:
        with zipfile.ZipFile(jar_path, 'r') as zf:
            for name in zf.namelist():
                if not name.endswith('.class'):
                    continue
                data = zf.read(name)
                if len(data) < 10:
                    continue
                magic = struct.unpack_from('>I', data, 0)[0]
                if magic != 0xCAFEBABE:
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
                            s = raw.decode('utf-8', errors='replace')
                            strings.append(s)
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
    except Exception as e:
        print(f"오류: {e}", file=sys.stderr)
    return strings

def is_display_text(s):
    s = s.strip()
    if len(s) < 4:
        return False
    has_space = ' ' in s
    has_punct = any(c in s for c in '.,!?:;()-+%')
    if not (has_space or has_punct):
        return False
    if s.startswith('/') or '\\\\' in s:
        return False
    if 'http' in s or '.com' in s:
        return False
    if re.match(r'^[A-Z][A-Z0-9_\\s]+$', s):
        return False
    if not re.search(r'[a-zA-Z\uAC00-\uD7A3]', s):
        return False
    if not re.match(r'^[\\s"%+\\-\\[(\\.\\d]*[A-Za-z]', s):
        return False
    return True

def has_korean(s):
    return any(0xAC00 <= ord(c) <= 0xD7A3 for c in s)

print("JAR 문자열 추출 중...", file=sys.stderr)
obf_strings = set(s for s in extract_utf8_strings(OBF_BAK) if is_display_text(s))
api_strings = set(s for s in extract_utf8_strings(API_BAK) if is_display_text(s))
all_strings = obf_strings | api_strings

translated_set = {s for s in all_strings if s in trans}
untranslated_set = {s for s in all_strings if s not in trans and not has_korean(s)}

print(f"전체 표시 문자열: {len(all_strings)}", file=sys.stderr)
print(f"번역됨: {len(translated_set)}", file=sys.stderr)
print(f"미번역: {len(untranslated_set)}", file=sys.stderr)

# ─── 카테고리별 분석 ───────────────────────────────────────────────

# 1. % 포함 수식어 (짧은 스탯 텍스트)
pct_untrans = sorted([s for s in untranslated_set if '%' in s and len(s) < 100])
pct_trans = {s: trans[s] for s in translated_set if '%' in s and len(s) < 100}

# 2. +/- 숫자 시작
bonus_untrans = sorted([s for s in untranslated_set if re.match(r'^[+\-]\d', s)])
bonus_trans = {s: trans[s] for s in translated_set if re.match(r'^[+\-]\d', s)}

# 3. 짧은 UI 레이블 (≤35자, 대문자 시작)
label_untrans = sorted([s for s in untranslated_set
                        if re.match(r'^[A-Z]', s) and 4 <= len(s) <= 35 and ' ' in s])
label_trans = {s: trans[s] for s in translated_set
               if re.match(r'^[A-Z]', s) and 4 <= len(s) <= 35 and ' ' in s}

# 4. 공통 단어 기반 그룹 (번역됨과 같은 단어 공유하는 미번역)
word_to_trans = defaultdict(list)
for s, kr in trans.items():
    if not has_korean(kr):
        continue
    for w in re.findall(r'[a-zA-Z]{4,}', s.lower()):
        word_to_trans[w].append(s)

mixed = defaultdict(lambda: {"translated": [], "untranslated": []})
for s in untranslated_set:
    for w in re.findall(r'[a-zA-Z]{4,}', s.lower()):
        if w in word_to_trans:
            # 어느 카테고리에 속하는지 추론
            sample = word_to_trans[w][0] if word_to_trans[w] else ""
            mixed[w]["untranslated"].append(s)
            mixed[w]["translated"] = word_to_trans[w][:5]
            break

# ─── 출력 ─────────────────────────────────────────────────────────
result = {
    "pct_untranslated": pct_untrans,
    "pct_translated_sample": list(pct_trans.items())[:50],
    "bonus_untranslated": bonus_untrans,
    "bonus_translated_sample": list(bonus_trans.items())[:50],
    "label_untranslated": label_untrans,
    "label_translated_sample": list(label_trans.items())[:50],
    "all_untranslated_display": sorted(untranslated_set),
    "stats": {
        "total_display": len(all_strings),
        "translated": len(translated_set),
        "untranslated": len(untranslated_set),
        "pct_untranslated": len(pct_untrans),
        "bonus_untranslated": len(bonus_untrans),
        "label_untranslated": len(label_untrans)
    }
}

os.makedirs(INTERMEDIATE, exist_ok=True)
with open(OUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n=== 결과 ===")
print(f"% 수식어 미번역: {len(pct_untrans)}개")
print(f"+/-숫자 미번역: {len(bonus_untrans)}개")
print(f"짧은 레이블 미번역: {len(label_untrans)}개")
print(f"저장: {OUT_FILE}")
