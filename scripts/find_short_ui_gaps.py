#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
짧은 UI 레이블 위주 미번역 찾기 - 번역된 항목과 같은 범주
"""

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
            if not name.endswith('.class'): continue
            data = zf.read(name)
            if len(data) < 10: continue
            if struct.unpack_from('>I', data, 0)[0] != 0xCAFEBABE: continue
            count = struct.unpack_from('>H', data, 8)[0]
            pos = 10; i = 1
            while i < count and pos < len(data):
                tag = data[pos]; pos += 1
                if tag == 1:
                    length = struct.unpack_from('>H', data, pos)[0]; pos += 2
                    raw = data[pos:pos+length]; pos += length
                    try: strings.add(raw.decode('utf-8', errors='replace'))
                    except: pass
                elif tag in (5,6): pos += 8; i += 1
                elif tag in (3,4): pos += 4
                elif tag in (7,8,16,19,20): pos += 2
                elif tag in (9,10,11,12,17,18): pos += 4
                elif tag == 15: pos += 3
                else: break
                i += 1
    return strings

def is_ui_label(s):
    """짧고 깔끔한 UI 레이블만 선별"""
    s = s.strip()
    if not (2 <= len(s) <= 50): return False
    if not re.match(r'^[A-Za-z%\+\-\(]', s): return False
    # 기술 문자열 제외
    if re.search(r'\.(java|class|png|csv|json|wav|ogg|txt|xml)$', s, re.I): return False
    if re.match(r'^(com|org|java|javax|net|sun|fs)[\./]', s): return False
    if re.match(r'^[A-Z_][A-Z0-9_]{4,}$', s): return False  # ALL_CAPS
    if re.search(r'[{}\[\]\\]', s): return False
    if re.search(r'\\[ntr"\\]', s): return False
    if '//' in s or '\\' in s: return False
    if re.search(r'\$[a-zA-Z]', s): return False
    # 문장 형태 제외 (단순 레이블만)
    if re.search(r'\b(you|the|your|this|that|when|will|can|not|for|with|from|into|also|been|have|has|are|was|were|its|their|they)\b', s, re.I):
        return False
    # 좋은 패턴
    is_stat_mod = bool(re.match(r'^[\+\-]?\d+', s))
    is_label = s.endswith(':') or s.endswith('-')
    is_short_phrase = len(s.split()) <= 5 and bool(re.match(r'^[A-Z]', s))
    is_paren = s.startswith('(') and s.endswith(')')
    return is_stat_mod or is_label or is_short_phrase or is_paren

print("문자열 추출 중...")
all_strings = extract_utf8_strings(OBF_BAK) | extract_utf8_strings(API_BAK)

untrans_labels = [s.strip() for s in all_strings
                  if s.strip() not in trans and is_ui_label(s.strip())]
print(f"미번역 UI 레이블 후보: {len(untrans_labels)}개")

# 번역된 항목과의 첫 단어 매칭으로 카테고리 파악
trans_first_words = defaultdict(list)
for k in trans:
    w = k.split()[0] if ' ' in k else k
    trans_first_words[w.lower()].append(k)

# 카테고리별 그룹화
groups = defaultdict(list)
for s in untrans_labels:
    first = s.split()[0].lower().rstrip(':').rstrip('-')
    if first in trans_first_words:
        # 같은 첫 단어로 시작하는 번역 항목이 있음
        groups[f"'{first.title()}' 계열"].append(s)
    elif re.match(r'^[\+\-]\d+%', s):
        groups['%수식어'].append(s)
    elif re.match(r'^\d+%', s):
        groups['%수식어'].append(s)
    elif s.endswith(':'):
        groups['레이블(:)'].append(s)
    elif s.startswith('(') and s.endswith(')'):
        groups['괄호 레이블'].append(s)
    elif len(s.split()) <= 3:
        groups['짧은 레이블'].append(s)
    else:
        groups['기타 레이블'].append(s)

# 출력
output = []
for cat in sorted(groups, key=lambda c: -len(groups[c])):
    items = sorted(set(groups[cat]))
    if len(items) == 0: continue
    print(f"\n[{cat}] {len(items)}개:")
    shown = items[:25]
    for s in shown:
        # 같은 계열 번역 예시 1개 보여주기
        first = s.split()[0].lower().rstrip(':').rstrip('-')
        ex = trans_first_words.get(first, [])[:1]
        note = f"  (예: {repr(ex[0])} → {repr(trans[ex[0]][:30])})" if ex else ""
        print(f"  {repr(s)}{note}")
    output.extend(shown)

# 중복 제거
seen = set()
unique = [s for s in output if not (s in seen or seen.add(s))]
out_file = os.path.join(INTERMEDIATE, 'short_ui_gaps.json')
os.makedirs(INTERMEDIATE, exist_ok=True)
with open(out_file, 'w', encoding='utf-8') as f:
    json.dump(unique, f, ensure_ascii=False, indent=2)
print(f"\n총 {len(unique)}개 저장: short_ui_gaps.json")
