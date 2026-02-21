#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
extract_obf_ui.py - starfarer_obf.jar에서 번역 가능한 UI 문자열만 정밀 추출

기존 extract_strings.py보다 훨씬 엄격한 필터 적용:
- Java 내부 문자열(디스크립터, 클래스명, 메서드명 등) 완전 제거
- 진짜 UI 텍스트(문장, 레이블, 툴팁)만 남김

출력: intermediate/ui_candidates.json
  {"문자열": "출처클래스", ...}  - 번역 대상 후보 (영→한 순서)
"""

from pathlib import Path
import json, os, re, struct, zipfile

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

JAR_PATH = os.path.join(GAME_CORE, 'starfarer_obf.jar')
OUT_FILE = os.path.join(INTERMEDIATE, 'ui_candidates.json')

MAGIC = b'\xca\xfe\xba\xbe'

# ─────────────────────────────────────────────────────
# 상수 풀 문자열 추출
# ─────────────────────────────────────────────────────
def get_strings(data: bytes) -> list:
    if data[:4] != MAGIC:
        return []
    try:
        count = struct.unpack_from('>H', data, 8)[0]
        result = []
        pos = 10; i = 1
        while i < count:
            tag = data[pos]; pos += 1
            if tag == 1:
                ln = struct.unpack_from('>H', data, pos)[0]; pos += 2
                raw = data[pos:pos+ln]; pos += ln
                try:
                    result.append(raw.decode('utf-8', errors='replace'))
                except:
                    pass
            elif tag in (5, 6): pos += 8; i += 1
            elif tag in (3, 4): pos += 4
            elif tag in (7, 8, 16, 19, 20): pos += 2
            elif tag in (9, 10, 11, 12, 17, 18): pos += 4
            elif tag == 15: pos += 3
            else: break
            i += 1
        return result
    except:
        return []

# ─────────────────────────────────────────────────────
# UI 문자열 판별 - 엄격한 필터
# ─────────────────────────────────────────────────────

# 완전 제외 패턴 (정규식)
RE_EXCLUDE = re.compile(
    # Java 타입 디스크립터
    r'^\(|^\[|^<|Ljava|Lcom/|Lfs/'
    # 클래스/패키지 경로
    r'|^com\.|^java\.|^fs\.|^org\.|^net\.|^sun\.'
    # 메서드/필드명 (camelCase 단일 단어)
    r'|^[a-z][a-zA-Z0-9]{2,30}$'
    # 특수 obfuscated 식별자
    r'|^[OoÒÓÔÕÖØõôöø0-9]{3,}$'
    # 순수 상수형
    r'|^[A-Z][A-Z_0-9]{2,}$'
    # 숫자로 시작
    r'|^\d'
    # 달러/퍼센트/언더스코어로 시작 (Java 내부)
    r'|^[\$_@#]'
    # 파일/URL 경로
    r'|[/\\\\](?!n)'  # \n 은 개행이므로 제외하지 않음
    r'|^https?:'
    # Java 내부 형식 문자열
    r'|;$|^\[L|^void$|^boolean$|^int$|^float$|^double$|^long$|^char$|^byte$|^short$'
    # 조각 식별자 (점 포함 짧은 것)
    r'|^\w+\.\w+$'
    # 순수 특수문자
    r'|^[^a-zA-Z\u0080-\uFFFF]+'
)

# 포함 필요 조건
def is_ui_string(s: str) -> bool:
    if not s or len(s) < 4 or len(s) > 600:
        return False
    # 한국어 이미 번역됨
    if any('\uAC00' <= c <= '\uD7A3' for c in s):
        return False
    # 알파벳 포함 필수
    if not any(c.isalpha() for c in s):
        return False
    # 제외 패턴
    if RE_EXCLUDE.search(s):
        return False
    # 공백 없으면 길이 15 이상이거나 점/쉼표/느낌표 등 포함
    if ' ' not in s:
        if len(s) < 15:
            return False
        if not any(c in s for c in '.,!?:;-()%'):
            return False
    # 제어문자 제외 (탭/개행 제외)
    if any(0 < ord(c) < 32 and c not in '\n\t\r' for c in s):
        return False
    # 대부분 ASCII (한글 번역 대상이므로)
    non_ascii = sum(1 for c in s if ord(c) > 127)
    if non_ascii > len(s) * 0.3:  # 30% 이상 비ASCII면 제외
        return False
    # obfuscated 문자 포함 제외 (O/0/Ò/Ó 등 연속)
    if re.search(r'[ÒÓÔÕÖØõôöø]{2,}', s):
        return False
    return True

# ─────────────────────────────────────────────────────
# 추가 휴리스틱: 실제 UI 텍스트 우선순위
# ─────────────────────────────────────────────────────
def ui_score(s: str) -> int:
    """높을수록 UI 텍스트일 가능성 높음"""
    score = 0
    # 공백 있음
    if ' ' in s:
        score += 3
    # 대문자로 시작
    if s[0].isupper():
        score += 2
    # 문장부호
    if any(c in s for c in '.,!?:;'):
        score += 1
    # %s 형식 문자열 (UI 포맷)
    if '%s' in s or '%d' in s or '%f' in s:
        score += 2
    # 너무 길면 감점 (400자 이상)
    if len(s) > 400:
        score -= 2
    return score


def main():
    # 기존 번역 로드
    existing = _load_all_translations()
    print(f"기존 번역: {len(existing)}개")

    # 스캔
    candidates = {}  # str → source_class
    with zipfile.ZipFile(JAR_PATH, 'r') as zf:
        entries = zf.infolist()
        print(f"JAR 항목: {len(entries)}개")
        for info in entries:
            if not info.filename.endswith('.class'):
                continue
            try:
                data = zf.read(info.filename)
            except:
                continue
            strings = get_strings(data)
            for s in strings:
                if s in existing:
                    continue
                if not is_ui_string(s):
                    continue
                if s not in candidates:
                    candidates[s] = info.filename

    print(f"후보 문자열: {len(candidates)}개")

    # 점수순 정렬
    sorted_cands = sorted(candidates.items(), key=lambda x: -ui_score(x[0]))

    os.makedirs(INTERMEDIATE, exist_ok=True)
    result = {s: src for s, src in sorted_cands}
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"저장: {OUT_FILE}")

    # 미리보기
    print("\n=== 상위 50개 후보 ===")
    for s, src in sorted_cands[:50]:
        short_src = src.split('/')[-1]
        print(f"  [{ui_score(s):2d}] {s!r:60s} ← {short_src}")


if __name__ == '__main__':
    main()
