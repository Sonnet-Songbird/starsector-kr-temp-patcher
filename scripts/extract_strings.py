#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
extract_strings.py - JAR에서 번역되지 않은 UI 문자열 추출

사용법:
    python extract_strings.py [--jar JAR경로] [--out OUTPUT.json] [--min-len N]

기본값:
    --jar: starfarer.api.jar, starfarer_obf.jar 둘 다 스캔
    --out: intermediate/untranslated.json
    --min-len: 4

출력:
    {"문자열": ["출처JAR:클래스경로", ...], ...}
"""

from pathlib import Path
import argparse, json, os, re, struct, zipfile

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

DEFAULT_JARS = [
    os.path.join(GAME_CORE, 'starfarer.api.jar'),
    os.path.join(GAME_CORE, 'starfarer_obf.jar'),
]
DEFAULT_OUT = os.path.join(INTERMEDIATE, 'untranslated.json')

# ─────────────────────────────────────────────────────
# Java Modified UTF-8 디코드
# ─────────────────────────────────────────────────────
def decode_java_utf8(raw: bytes) -> str:
    result = []
    i = 0
    while i < len(raw):
        b = raw[i]
        if b == 0:
            result.append('\x00'); i += 1
        elif b < 0x80:
            result.append(chr(b)); i += 1
        elif b < 0xC0:
            result.append('\uFFFD'); i += 1
        elif b < 0xE0:
            if i + 1 < len(raw):
                c = ((b & 0x1F) << 6) | (raw[i+1] & 0x3F)
                result.append(chr(c)); i += 2
            else:
                result.append('\uFFFD'); i += 1
        elif b < 0xF0:
            if i + 2 < len(raw):
                c = ((b & 0x0F) << 12) | ((raw[i+1] & 0x3F) << 6) | (raw[i+2] & 0x3F)
                result.append(chr(c)); i += 3
            else:
                result.append('\uFFFD'); i += 1
        else:
            if i + 5 < len(raw) and raw[i] == 0xED and raw[i+3] == 0xED:
                hi = ((raw[i+1] & 0x0F) << 6) | (raw[i+2] & 0x3F)
                lo = ((raw[i+4] & 0x0F) << 6) | (raw[i+5] & 0x3F)
                cp = 0x10000 + ((hi - 0xD800) << 10) + (lo - 0xDC00)
                result.append(chr(cp)); i += 6
            else:
                result.append('\uFFFD'); i += 1
    return ''.join(result)


# ─────────────────────────────────────────────────────
# 상수 풀에서 Utf8 문자열 추출
# ─────────────────────────────────────────────────────
def extract_strings_from_class(data: bytes) -> list:
    if data[:4] != b'\xca\xfe\xba\xbe':
        return []
    try:
        count = struct.unpack_from('>H', data, 8)[0]
        strings = []
        pos = 10
        i = 1
        while i < count:
            tag = data[pos]; pos += 1
            if tag == 1:
                length = struct.unpack_from('>H', data, pos)[0]; pos += 2
                raw = data[pos:pos+length]; pos += length
                try:
                    s = decode_java_utf8(raw)
                    strings.append(s)
                except Exception:
                    pass
            elif tag in (5, 6):
                pos += 8; i += 1  # Long/Double: 2슬롯
            elif tag in (3, 4):   pos += 4
            elif tag in (7, 8, 16, 19, 20): pos += 2
            elif tag in (9, 10, 11, 12, 17, 18): pos += 4
            elif tag == 15:       pos += 3
            else:
                return strings  # 알 수 없는 태그 → 중단
            i += 1
        return strings
    except Exception:
        return []


# ─────────────────────────────────────────────────────
# UI 문자열 판별 필터
# ─────────────────────────────────────────────────────
# 제외 패턴
EXCLUDE_PREFIXES = (
    'com.', 'java.', 'org.', 'net.', 'fs.', 'javax.',
    'sun.', 'jdk.', 'lwjgl.',
    'http', 'https', 'file:',
    'Ljava', 'Lcom', 'Lfs', 'Ljdk', '()',
)
EXCLUDE_REGEX = re.compile(
    r'^[A-Z_][A-Z_0-9]*$'              # 상수형 식별자 (UPPER_CASE)
    r'|^[a-z][a-zA-Z0-9]*\.[a-z]'      # 패키지/클래스 경로
    r'|[/\\]'                           # 파일 경로
    r'|^\$'                             # $ 시작 변수
    r'|^#'                              # 색상 코드 등
    r'|^\d'                             # 숫자 시작
    r'|^[a-z][a-zA-Z0-9]{0,15}$'       # 짧은 camelCase 식별자 (메서드명 등)
)
# 한국어 포함 → 이미 번역됨
HAS_KOREAN = re.compile(r'[\uAC00-\uD7A3]')

def is_ui_string(s: str, min_len: int) -> bool:
    if len(s) < min_len:
        return False
    if HAS_KOREAN.search(s):
        return False
    if s.startswith(EXCLUDE_PREFIXES):
        return False
    if EXCLUDE_REGEX.match(s):
        return False
    # 알파벳 포함 여부
    if not any(c.isalpha() for c in s):
        return False
    # 최소한 공백, 대문자, 특수문자 중 하나 포함 (순수 식별자 제외)
    has_space = ' ' in s
    has_punct = any(c in s for c in '.,!?:;-()')
    has_upper = any(c.isupper() for c in s)
    if not (has_space or has_punct or has_upper):
        return False
    # 제어문자 제외
    if any(ord(c) < 32 and c not in '\n\t' for c in s):
        return False
    return True


# ─────────────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────────────
def scan_jar(jar_path: str, translations: dict, min_len: int) -> dict:
    """JAR에서 번역 안 된 UI 문자열 추출. {문자열: [출처, ...]}"""
    results = {}
    jar_name = os.path.basename(jar_path)

    try:
        zf = zipfile.ZipFile(jar_path, 'r')
    except Exception as e:
        print(f"  Cannot open {jar_path}: {e}")
        return results

    with zf:
        for entry in zf.infolist():
            if not entry.filename.endswith('.class'):
                continue
            try:
                data = zf.read(entry.filename)
            except Exception:
                continue

            strings = extract_strings_from_class(data)
            for s in strings:
                if s in translations:
                    continue
                if not is_ui_string(s, min_len):
                    continue
                source = f"{jar_name}:{entry.filename}"
                if s not in results:
                    results[s] = []
                if source not in results[s]:
                    results[s].append(source)

    return results


def main():
    parser = argparse.ArgumentParser(description='Extract untranslated UI strings from JARs')
    parser.add_argument('--jar', action='append', help='JAR to scan (repeatable)')
    parser.add_argument('--out', default=DEFAULT_OUT, help='Output JSON file')
    parser.add_argument('--min-len', type=int, default=4, help='Minimum string length')
    parser.add_argument('--show', type=int, default=0,
                        help='Print N sample strings to stdout (0=all)')
    args = parser.parse_args()

    jars = args.jar if args.jar else DEFAULT_JARS

    # Load current translations
    translations = _load_all_translations()
    print(f"Loaded {len(translations)} existing translations")

    # Scan JARs
    all_results = {}
    for jar in jars:
        if not os.path.exists(jar):
            print(f"  SKIP (not found): {jar}")
            continue
        print(f"Scanning: {os.path.basename(jar)} ...")
        results = scan_jar(jar, translations, args.min_len)
        print(f"  Found {len(results)} untranslated strings")
        for s, sources in results.items():
            if s not in all_results:
                all_results[s] = []
            all_results[s].extend(sources)

    # Sort by string
    all_results = dict(sorted(all_results.items()))
    print(f"\nTotal unique untranslated strings: {len(all_results)}")

    # Save
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"Saved to: {args.out}")

    # Preview
    if args.show != 0:
        items = list(all_results.items())
        if args.show > 0:
            items = items[:args.show]
        print("\nSample strings:")
        for s, srcs in items:
            print(f"  {s!r:60s} ← {srcs[0]}")


if __name__ == '__main__':
    main()
