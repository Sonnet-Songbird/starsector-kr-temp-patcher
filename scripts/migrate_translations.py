#!/usr/bin/env python3
"""
migrate_translations.py - final_translations.json 분리 마이그레이션 (일회성)

intermediate/final_translations.json (16,190개) 를 세 파일로 분리:
  patches/common.json    - 양쪽 JAR 모두 or 어느 쪽에도 없는 것
  patches/api_jar.json   - api JAR 전용 문자열
  patches/obf_jar.json   - obf JAR 전용 문자열

실행: python scripts/migrate_translations.py
"""

import json
import os
import struct
import sys
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent


def _resolve(p, base):
    if isinstance(p, str) and (p.startswith('./') or p.startswith('../') or p == '.'):
        return str((base / p).resolve())
    return p


def extract_jar_strings(jar_path: str) -> set:
    """JAR에서 모든 CONSTANT_Utf8 문자열 추출."""
    strings = set()
    try:
        with zipfile.ZipFile(jar_path, 'r') as z:
            for name in z.namelist():
                if not name.endswith('.class'):
                    continue
                try:
                    data = z.read(name)
                    if data[:4] != b'\xca\xfe\xba\xbe':
                        continue
                    count = struct.unpack_from('>H', data, 8)[0]
                    pos = 10
                    i = 1
                    while i < count:
                        tag = data[pos]; pos += 1
                        if tag == 1:
                            length = struct.unpack_from('>H', data, pos)[0]; pos += 2
                            raw = data[pos:pos+length]; pos += length
                            try:
                                strings.add(raw.decode('utf-8', errors='replace'))
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
                except Exception:
                    pass
    except Exception as e:
        print(f"  JAR 읽기 오류 {jar_path}: {e}", file=sys.stderr)
    return strings


def main():
    with open(SCRIPT_DIR / 'config.json', encoding='utf-8') as f:
        cfg = json.load(f)
    paths = cfg['paths']
    base = SCRIPT_DIR

    game_core = _resolve(paths['game_core'], base)
    patches_dir = _resolve(paths['patches'], base)

    # 입력: 기존 final_translations.json
    src_trans = str(SCRIPT_DIR / 'intermediate' / 'final_translations.json')
    if not os.path.exists(src_trans):
        print(f"ERROR: {src_trans} 없음", file=sys.stderr)
        sys.exit(1)

    with open(src_trans, encoding='utf-8') as f:
        translations = json.load(f)
    print(f"입력 번역 쌍: {len(translations)}개")

    # JAR 문자열 추출 (.bak 우선, 없으면 라이브)
    def load_jar_strings(jar_name):
        for suffix in (jar_name + '.bak', jar_name):
            path = os.path.join(game_core, suffix)
            if os.path.exists(path):
                print(f"  {suffix} 추출 중...")
                s = extract_jar_strings(path)
                print(f"  → {len(s)}개 문자열")
                return s
        print(f"  WARNING: {jar_name} 및 .bak 모두 없음", file=sys.stderr)
        return set()

    print("\napi JAR 문자열 추출...")
    api_strings = load_jar_strings('starfarer.api.jar')
    print("obf JAR 문자열 추출...")
    obf_strings = load_jar_strings('starfarer_obf.jar')

    # 분류
    common = {}
    api_only = {}
    obf_only = {}

    for key, val in translations.items():
        in_api = key in api_strings
        in_obf = key in obf_strings

        if in_api and not in_obf:
            api_only[key] = val
        elif in_obf and not in_api:
            obf_only[key] = val
        else:
            # 양쪽 모두 또는 어느 쪽에도 없음 → common
            common[key] = val

    print(f"\n=== 분류 결과 ===")
    print(f"  common.json  : {len(common):,}개 (양쪽 모두 {len([k for k in translations if k in api_strings and k in obf_strings]):,} + 어느 쪽도 아님 {len([k for k in translations if k not in api_strings and k not in obf_strings]):,})")
    print(f"  api_jar.json : {len(api_only):,}개")
    print(f"  obf_jar.json : {len(obf_only):,}개")
    print(f"  합계         : {len(common)+len(api_only)+len(obf_only):,}개 (원본: {len(translations):,}개)")

    # 출력
    os.makedirs(patches_dir, exist_ok=True)

    out_common = _resolve(paths['translations'], base)
    out_api = _resolve(paths['api_trans'], base)
    out_obf = _resolve(paths['obf_trans'], base)

    for path, data in [(out_common, common), (out_api, api_only), (out_obf, obf_only)]:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=None, separators=(',', ':'))
        print(f"  저장: {path} ({len(data):,}개)")

    print("\n마이그레이션 완료.")
    print("이후 intermediate/final_translations.json 삭제 가능:")
    print(f"  del {src_trans}")


if __name__ == '__main__':
    main()
