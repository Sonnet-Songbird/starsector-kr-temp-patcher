#!/usr/bin/env python3
"""
patch_mod_jar.py - 범용 모드 JAR 패처 (post_build 훅)

build_mods.py의 post_build 훅으로 호출. output/mods/{mod_id}/ 내 JAR을 in-place 패치.

사용법:
    python scripts/patch_mod_jar.py --mod <mod_id>

입력:
    output/mods/{mod_id}/{mod_jar}              (build_mods.py 복사본)
    patches/common.json                         (공통 번역 사전)
    patches/{mod_id}/translations.json          (모드 전용 번역, 공통보다 우선)
    patches/exclusions.json                     (전역 blocked_classes, blocked_strings)
    patches/{mod_id}/exclusions.json            (모드 전용 blocked_classes, blocked_strings — 선택적)

출력:
    output/mods/{mod_id}/{mod_jar}              (in-place 패치)

제외 규칙 병합 순서:
    전역 exclusions + 모드 exclusions → 합집합으로 적용
    (모드 전용 exclusions에는 그 모드에서만 번역 금지인 항목을 지정)

config.json 예시:
    {
      "id":      "Nexerelin",
      "enabled": true,
      "mod_jar": "jars/ExerelinCore.jar",        # string 또는 list 모두 지원
      "post_build": ["scripts/patch_mod_jar.py"]
    }
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from patch_utils import (load_config, load_exclusions, load_translations,
                          patch_jar, resolve_path)


def main():
    parser = argparse.ArgumentParser(description='모드 JAR 상수 풀 패치')
    parser.add_argument('--mod', required=True, help='모드 ID (config.json mods[].id)')
    args = parser.parse_args()
    mod_id = args.mod

    cfg = load_config()
    paths = cfg['paths']

    # mod 설정 찾기
    mod_cfg = next((m for m in cfg.get('mods', []) if m['id'] == mod_id), None)
    if mod_cfg is None:
        print(f"ERROR: config.json에 모드 '{mod_id}' 없음", file=sys.stderr)
        sys.exit(1)

    mod_jar = mod_cfg.get('mod_jar')
    if not mod_jar:
        print(f"  {mod_id}: mod_jar 미설정, 건너뜀")
        sys.exit(0)

    # string 또는 list 모두 지원
    jar_paths = [mod_jar] if isinstance(mod_jar, str) else list(mod_jar)

    output_mods = Path(resolve_path(paths['output_mods']))
    patches_dir = Path(resolve_path(paths['patches']))

    # 번역 사전 병합: common → 모드 전용 (모드 전용이 common보다 우선)
    translations = load_translations(paths)
    mod_trans_file = patches_dir / mod_id / 'translations.json'
    if mod_trans_file.exists():
        with open(mod_trans_file, encoding='utf-8') as f:
            mod_translations = json.load(f)
        if mod_translations:
            translations.update(mod_translations)
            common_count = len(translations) - len(mod_translations)
            print(f"  [{mod_id}] 번역 사전: common {common_count}개"
                  f" + 모드 전용 {len(mod_translations)}개 → 합계 {len(translations)}개")
        else:
            print(f"  [{mod_id}] 번역 사전: common {len(translations)}개 (모드 전용 비어있음)")
    else:
        print(f"  [{mod_id}] 번역 사전: common {len(translations)}개 (모드 전용 없음)")

    # 전역 + 모드 전용 exclusions 병합
    blocked_classes, blocked_strings, blocked_jar_strings = load_exclusions(paths, mod_id)
    jar_blocked = blocked_strings | blocked_jar_strings

    for jar_rel in jar_paths:
        jar_path = output_mods / mod_id / jar_rel
        if not jar_path.exists():
            print(f"  WARN: JAR 없음: {jar_path} — 건너뜀")
            continue

        print(f"  [{mod_id}/{jar_rel}] 패치 시작...")
        stats = patch_jar(
            jar_path, jar_path,
            translations, blocked_classes, jar_blocked,
            label=f"{mod_id}/{jar_rel}"
        )
        print(f"  [{mod_id}/{jar_rel}] 패치: {stats['patched']}/{stats['total']} 클래스"
              + (f", 오류: {stats['errors']}" if stats['errors'] else ""))

    print(f"  [{mod_id}] patch_mod_jar 완료.")


if __name__ == '__main__':
    main()
