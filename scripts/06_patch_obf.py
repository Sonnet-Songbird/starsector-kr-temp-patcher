#!/usr/bin/env python
"""
06_patch_obf.py - starfarer_obf.jar 번역 패치 (인메모리)

사용법:
    python 06_patch_obf.py

입력:
    ../starsector-core/starfarer_obf.jar.bak   (영어 원본 백업)
    ./patches/common.json + ./patches/obf_jar.json

출력:
    ./output/starsector-core/starfarer_obf.jar  (패치본)
"""

import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from patch_utils import patch_jar  # noqa: E402


def _resolve(p, base):
    if isinstance(p, str) and (p.startswith('./') or p.startswith('../') or p == '.'):
        return str((base / p).resolve())
    return p


def _load_exclusions(paths, base):
    excl_file = _resolve(paths.get('exclusions', ''), base)
    if excl_file and os.path.exists(excl_file):
        with open(excl_file, encoding='utf-8') as f:
            excl = json.load(f)
        return set(excl.get('blocked_classes', [])), set(excl.get('blocked_strings', []))
    return set(), set()


def main():
    with open(SCRIPT_DIR / 'config.json', encoding='utf-8') as f:
        paths = json.load(f)['paths']

    base = SCRIPT_DIR
    bak_jar = os.path.join(_resolve(paths['game_core'], base), 'starfarer_obf.jar.bak')
    out_jar = os.path.join(_resolve(paths['output_core'], base), 'starfarer_obf.jar')

    if not os.path.exists(bak_jar):
        print(f"ERROR: {bak_jar} not found")
        print("게임 업데이트 전에 백업을 먼저 생성하세요:")
        print("  cp starsector-core/starfarer_obf.jar starsector-core/starfarer_obf.jar.bak")
        sys.exit(1)

    # translations 병합: common + obf_trans
    translations = {}
    for key in ('translations', 'obf_trans'):
        p = _resolve(paths.get(key, ''), base)
        if p and os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                translations.update(json.load(f))
        elif key == 'translations':
            print(f"ERROR: Translation file not found: {p}")
            sys.exit(1)

    blocked_classes, blocked_strings = _load_exclusions(paths, base)
    print(f"Loaded {len(translations)} translations (common + obf)")

    os.makedirs(os.path.dirname(out_jar), exist_ok=True)

    stats = patch_jar(bak_jar, out_jar, translations, blocked_classes, blocked_strings, "obf")

    print(f"\nProcessed {stats['total']} class files")
    print(f"  Patched:  {stats['patched']}")
    print(f"  Errors:   {stats['errors']}")
    print(f"  Unchanged: {stats['total'] - stats['patched'] - stats['errors']}")
    print(f"\nOutput: {out_jar}")
    print(f"Size: {os.path.getsize(out_jar):,} bytes")


if __name__ == '__main__':
    main()
