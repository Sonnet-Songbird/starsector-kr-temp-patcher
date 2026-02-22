#!/usr/bin/env python3
"""
06_patch_obf.py - starfarer_obf.jar 번역 패치 (인메모리)

사용법:
    python 06_patch_obf.py [--no-restore]

입력:
    ../starsector-core/starfarer_obf.jar.bak   (영어 원본 백업)
    ./patches/common.json + ./patches/obf_jar.json

출력:
    ./output/starsector-core/starfarer_obf.jar  (패치본)

옵션:
    --no-restore    .bak → live JAR 복원 단계 건너뜀 (기본: 복원 후 패치)
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from patch_utils import load_config, load_exclusions, load_translations, patch_jar, resolve_path


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--no-restore', action='store_true',
                        default=os.environ.get('STARSECTOR_NO_RESTORE') == '1')
    args, _ = parser.parse_known_args()
    restore = not args.no_restore

    paths = load_config()['paths']
    game_core = resolve_path(paths['game_core'])
    bak_jar  = os.path.join(game_core, 'starfarer_obf.jar.bak')
    live_jar = os.path.join(game_core, 'starfarer_obf.jar')
    out_jar  = os.path.join(resolve_path(paths['output_core']), 'starfarer_obf.jar')

    if not os.path.exists(bak_jar):
        print(f"ERROR: {bak_jar} not found")
        print("게임 업데이트 전에 백업을 먼저 생성하세요:")
        print("  cp starsector-core/starfarer_obf.jar starsector-core/starfarer_obf.jar.bak")
        sys.exit(1)

    if restore:
        print(f"[복원] starfarer_obf.jar.bak → starfarer_obf.jar")
        shutil.copy2(bak_jar, live_jar)
    else:
        print("[복원 건너뜀] --no-restore")

    translations = load_translations(paths, 'obf_trans')
    blocked_classes, blocked_strings, blocked_jar_strings = load_exclusions(paths)
    jar_blocked = blocked_strings | blocked_jar_strings
    print(f"Loaded {len(translations)} translations (common + obf)")

    os.makedirs(os.path.dirname(out_jar), exist_ok=True)
    stats = patch_jar(bak_jar, out_jar, translations, blocked_classes, jar_blocked, "obf")

    print(f"\nProcessed {stats['total']} class files")
    print(f"  Patched:   {stats['patched']}")
    print(f"  Errors:    {stats['errors']}")
    print(f"  Unchanged: {stats['total'] - stats['patched'] - stats['errors']}")
    print(f"\nOutput: {out_jar}")
    print(f"Size: {os.path.getsize(out_jar):,} bytes")


if __name__ == '__main__':
    main()
