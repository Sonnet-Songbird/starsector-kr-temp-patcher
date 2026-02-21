#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
verify_cr.py — 한글화 적용 상태 spot-check 검증

체크 항목:
  1. api JAR CRPluginImpl — '전투 준비도 ' 포함 여부
  2. api JAR CRPluginImpl — '오작동 위험: ' 포함 여부
  3. obf JAR              — 한국어 문자열 1개 이상 존재 여부
  4. missions forlornhope — '인빈서블' 포함 여부

--status 플래그: 각 JAR가 한국어/영어 어느 쪽인지 요약 출력
"""

import json
import struct
import sys
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent


def _resolve(p, base=SCRIPT_DIR):
    if isinstance(p, str) and (p.startswith('./') or p.startswith('../') or p == '.'):
        return str((base / p).resolve())
    return p


with open(SCRIPT_DIR / 'config.json', encoding='utf-8') as _f:
    _cfg = json.load(_f)
_p = _cfg['paths']

GAME_CORE = Path(_resolve(_p['game_core']))
GAME_MODS = Path(_resolve(_p['game_mods']))
API_JAR   = GAME_CORE / 'starfarer.api.jar'
OBF_JAR   = GAME_CORE / 'starfarer_obf.jar'

# forlornhope MissionDefinition.java는 출력 모드 또는 게임 모드에서 확인
OUTPUT_MODS = Path(_resolve(_p['output_mods']))
FORLORN_JAVA = OUTPUT_MODS / 'starsectorkorean/data/missions/forlornhope/MissionDefinition.java'
if not FORLORN_JAVA.exists():
    FORLORN_JAVA = GAME_MODS / 'starsectorkorean/data/missions/forlornhope/MissionDefinition.java'

KO_RANGE_START = 0xAC00
KO_RANGE_END   = 0xD7A3


def iter_utf8_strings(data):
    """Java .class 상수 풀에서 모든 CONSTANT_Utf8 문자열을 반환."""
    count = struct.unpack_from('>H', data, 8)[0]
    pos = 10
    i = 1
    while i < count:
        tag = data[pos]; pos += 1
        if tag == 1:
            length = struct.unpack_from('>H', data, pos)[0]; pos += 2
            raw = data[pos:pos+length]; pos += length
            try:
                yield raw.decode('utf-8', errors='replace')
            except Exception:
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
        i += 1


def has_korean(text):
    return any(KO_RANGE_START <= ord(c) <= KO_RANGE_END for c in text)


def check_api_jar():
    """api JAR에서 CRPluginImpl 스트링 확인."""
    results = {"전투 준비도 ": False, "오작동 위험: ": False}
    target = "com/fs/starfarer/api/impl/combat/CRPluginImpl.class"
    if not API_JAR.exists():
        return results, f"파일 없음: {API_JAR}"
    try:
        with zipfile.ZipFile(API_JAR) as z:
            data = z.read(target)
    except KeyError:
        return results, f"클래스 없음: {target}"

    for text in iter_utf8_strings(data):
        for key in results:
            if key in text:
                results[key] = True
    return results, None


def check_obf_jar():
    """obf JAR 전체에서 한국어 문자열 존재 확인 (첫 발견 시 즉시 반환)."""
    if not OBF_JAR.exists():
        return False, f"파일 없음: {OBF_JAR}"
    with zipfile.ZipFile(OBF_JAR) as z:
        for name in z.namelist():
            if not name.endswith('.class'):
                continue
            try:
                data = z.read(name)
            except Exception:
                continue
            for text in iter_utf8_strings(data):
                if has_korean(text):
                    return True, None
    return False, "한국어 문자열 없음"


def check_forlornhope():
    """forlornhope 미션 MissionDefinition.java에서 '인빈서블' 확인."""
    if not FORLORN_JAVA.exists():
        return False, f"파일 없음: {FORLORN_JAVA}"
    content = FORLORN_JAVA.read_text(encoding='utf-8', errors='replace')
    if '인빈서블' in content:
        return True, None
    return False, "'인빈서블' 문자열 없음"


def run_checks():
    """4개 체크 실행, 결과 목록 반환."""
    checks = []

    # 체크 1, 2: api JAR CRPluginImpl
    api_results, api_err = check_api_jar()
    for key, found in api_results.items():
        label = f"api JAR CRPluginImpl '{key.strip()}'"
        if api_err:
            checks.append((label, False, api_err))
        else:
            checks.append((label, found, None if found else f"'{key}' 없음"))

    # 체크 3: obf JAR 한국어
    ok, err = check_obf_jar()
    checks.append(("obf JAR 한국어 문자열", ok, err))

    # 체크 4: forlornhope
    ok, err = check_forlornhope()
    checks.append(("forlornhope '인빈서블'", ok, err))

    return checks


def print_status():
    """각 JAR가 한국어/영어 어느 쪽인지 빠른 요약."""
    print("=== 적용 상태 ===")

    api_results, api_err = check_api_jar()
    if api_err:
        print(f"  api JAR : ERROR ({api_err})")
    elif any(api_results.values()):
        print(f"  api JAR : 한국어 적용됨")
    else:
        print(f"  api JAR : 영어 (미적용)")

    ok, err = check_obf_jar()
    if err and "파일 없음" in err:
        print(f"  obf JAR : ERROR ({err})")
    elif ok:
        print(f"  obf JAR : 한국어 적용됨")
    else:
        print(f"  obf JAR : 영어 (미적용)")

    ok, err = check_forlornhope()
    if err and "파일 없음" in err:
        print(f"  missions: ERROR ({err})")
    elif ok:
        print(f"  missions: 한국어 적용됨")
    else:
        print(f"  missions: 영어 (미적용)")


def main():
    status_mode = "--status" in sys.argv

    if status_mode:
        print_status()
        return

    print("=== 한글화 검증 ===\n")
    checks = run_checks()
    passed = 0
    failed = 0

    for label, ok, err in checks:
        status = "PASS" if ok else "FAIL"
        detail = f" — {err}" if err else ""
        print(f"  [{status}] {label}{detail}")
        if ok:
            passed += 1
        else:
            failed += 1

    print(f"\n결과: {passed}/{passed+failed} 통과", end="")
    if failed == 0:
        print(" — 모두 정상")
    else:
        print(f" — {failed}개 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
