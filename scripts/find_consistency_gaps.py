#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
이미 번역된 항목과 일관성을 기준으로 미번역 UI 문자열 찾기
- 번역된 문자열의 단어 패턴과 매칭되는 미번역 항목 우선 선정
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

def is_display_text(s):
    s = s.strip()
    if len(s) < 3 or len(s) > 80: return False
    if not re.match(r'^[A-Za-z%\+\-\(]', s): return False
    # 클래스/패키지 경로
    if re.search(r'\.(java|class|png|csv|json|wav|ogg|mp3|txt|xml|properties)$', s, re.I): return False
    if re.match(r'^(com|org|java|javax|net|sun|fs)\b', s): return False
    # 순수 기술 문자열
    if re.match(r'^[A-Z_][A-Z0-9_]{3,}$', s): return False  # ALL_CAPS constant
    if re.match(r'^[a-z][a-zA-Z0-9]{0,2}$', s): return False  # 2자 이하 식별자
    if re.search(r'[{}\[\]]', s): return False
    if re.search(r'\\[ntr]', s): return False
    if '//' in s or '\\' in s: return False
    if re.match(r'^[0-9\.\-\+]+$', s): return False
    # 변수 참조
    if re.match(r'^[a-z][a-z][A-Z]', s): return False  # camelCase
    if re.search(r'\$[a-zA-Z]', s): return False
    # 좋은 패턴: 공백 있는 자연어, 콜론으로 끝나는 레이블, %, +/- 수식어
    has_space = ' ' in s
    is_label = s.endswith(':') or s.endswith(':')
    is_modifier = bool(re.match(r'^[\+\-]?\d+%', s)) or bool(re.match(r'^\d+%', s))
    is_natural = bool(re.match(r'^[A-Z][a-z]', s)) and has_space
    is_short_ui = len(s) <= 30 and bool(re.match(r'^[A-Z][a-z]', s))
    return has_space or is_label or is_modifier or is_natural or is_short_ui

print("JAR에서 문자열 추출 중...")
all_strings = extract_utf8_strings(OBF_BAK) | extract_utf8_strings(API_BAK)
print(f"총 {len(all_strings)}개 추출")

# 표시용 문자열 필터
display = {s.strip() for s in all_strings if is_display_text(s.strip())}
untrans = {s for s in display if s not in trans}
print(f"표시용 문자열: {len(display)}개, 미번역: {len(untrans)}개")

# ── 번역된 문자열에서 단어 패턴 추출 ──────────────────────────────
def words(s):
    return re.findall(r'[a-zA-Z]{3,}', s.lower())

# 번역된 항목의 단어 집합
trans_words = defaultdict(set)  # word -> set of translated strings containing it
for k in trans:
    for w in words(k):
        trans_words[w].add(k)

# 공통 접두어 그룹 (번역 완료)
trans_prefixes = defaultdict(list)
for k in trans:
    ws = words(k)
    if ws:
        trans_prefixes[ws[0]].append(k)

# ── 미번역 항목 점수화 ───────────────────────────────────────────
scored = []
for s in untrans:
    ws = words(s)
    if not ws: continue
    score = 0
    matched_trans = set()
    # 각 단어가 번역된 항목에 몇 개 있나
    for w in ws:
        if w in trans_words:
            score += len(trans_words[w])
            matched_trans |= trans_words[w]
    # 같은 첫 단어를 가진 번역 항목 수
    prefix_bonus = len(trans_prefixes.get(ws[0], []))
    score += prefix_bonus * 2
    if score > 0:
        # 가장 유사한 번역 항목 찾기
        best_match = None
        best_overlap = 0
        for tm in matched_trans:
            overlap = len(set(words(s)) & set(words(tm)))
            if overlap > best_overlap:
                best_overlap = overlap
                best_match = tm
        scored.append((score, best_overlap, s, best_match))

scored.sort(reverse=True)
print(f"연관 미번역: {len(scored)}개")

# ── 카테고리별 그룹화 ────────────────────────────────────────────
categories = {
    '전투/전함': ['combat', 'battle', 'ship', 'fleet', 'weapon', 'fighter', 'hull', 'armor', 'shield', 'damage', 'range', 'beam', 'missile', 'turret', 'wing', 'bay', 'burn'],
    '함대/장교': ['officer', 'crew', 'command', 'captain', 'admiral', 'skill', 'level', 'point', 'deploy', 'reinforce'],
    '플럭스/제원': ['flux', 'vent', 'dissipation', 'overload', 'speed', 'acceleration', 'turn', 'rate', 'peak', 'cargo', 'fuel', 'supply', 'ordnance', 'capacity', 'mass', 'upkeep'],
    '식민지/경제': ['colony', 'planet', 'market', 'trade', 'income', 'profit', 'expense', 'growth', 'stability', 'hazard', 'admin', 'governor', 'industry', 'production', 'demand', 'supply', 'export', 'import', 'price', 'accessibility'],
    '세력/인텔': ['faction', 'intel', 'contact', 'bounty', 'mission', 'hegemony', 'luddic', 'pirate', 'persean', 'sindrian', 'commission', 'relation', 'reputation', 'smuggle'],
    '항법/지도': ['nav', 'jump', 'gate', 'relay', 'beacon', 'sensor', 'survey', 'scan', 'system', 'star', 'orbit', 'planet', 'moon', 'debris', 'derelict'],
    '전투 상태': ['disabled', 'overloaded', 'retreat', 'assist', 'engage', 'deploy', 'recover', 'readiness', 'repair', 'damage', 'emp', 'malfunction'],
}

cat_results = defaultdict(list)
others = []
top_scored = [(s, bm, sc) for sc, bo, s, bm in scored if sc >= 5][:400]

for s, bm, sc in top_scored:
    ws_set = set(words(s))
    matched_cat = None
    best_cnt = 0
    for cat, kws in categories.items():
        cnt = len(ws_set & set(kws))
        if cnt > best_cnt:
            best_cnt = cnt
            matched_cat = cat
    if matched_cat and best_cnt > 0:
        cat_results[matched_cat].append((sc, s, bm))
    else:
        others.append((sc, s, bm))

# 결과 출력
output_items = []
print("\n" + "="*70)
print("카테고리별 연관 미번역 항목 (기존 번역과 일관성 우선)")
print("="*70)

for cat, items in sorted(cat_results.items()):
    items.sort(reverse=True)
    top = items[:20]
    if not top: continue
    print(f"\n[{cat}] {len(items)}개:")
    for sc, s, bm in top:
        note = f'  ← "{bm}"' if bm else ''
        print(f"  {repr(s)}{note}")
        output_items.append(s)

if others:
    print(f"\n[기타] {len(others)}개:")
    for sc, s, bm in others[:20]:
        note = f'  ← "{bm}"' if bm else ''
        print(f"  {repr(s)}{note}")
        output_items.append(s)

# 중복 제거 후 저장
seen = set()
unique = []
for s in output_items:
    if s not in seen:
        seen.add(s)
        unique.append(s)

out_file = os.path.join(INTERMEDIATE, 'consistency_gaps.json')
os.makedirs(INTERMEDIATE, exist_ok=True)
with open(out_file, 'w', encoding='utf-8') as f:
    json.dump(unique, f, ensure_ascii=False, indent=2)
print(f"\n총 {len(unique)}개 저장: consistency_gaps.json")
