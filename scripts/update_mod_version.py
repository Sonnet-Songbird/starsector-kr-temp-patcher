#!/usr/bin/env python3
"""
update_mod_version.py - 게임 버전 자동 감지 및 mod_info.json 업데이트

starfarer_obf.jar의 com/fs/starfarer/Version.class에서 버전 문자열을 읽어
output/mods/{mod_id}/mod_info.json의 gameVersion 필드를 자동으로 갱신한다.

사용법:
    python update_mod_version.py [--mod <mod_id>]
    기본값: starsectorkorean
"""

import argparse
import json
import os
import re
import sys
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent


def _resolve(p, base=SCRIPT_DIR):
    if isinstance(p, str) and (p.startswith('./') or p.startswith('../') or p == '.'):
        return str((base / p).resolve())
    return p


def detect_game_version(jar_path: str) -> str:
    """
    starfarer_obf.jar에서 com/fs/starfarer/Version.class를 열어
    상수 풀의 CONSTANT_Utf8 항목 중 버전 문자열을 반환한다.
    """
    target = 'com/fs/starfarer/Version.class'
    version_re = re.compile(rb'0\.\d+[a-zA-Z]+(?:-RC\d+)?')

    with zipfile.ZipFile(jar_path, 'r') as zf:
        if target not in zf.namelist():
            raise FileNotFoundError(f"{target} not found in {jar_path}")
        data = zf.read(target)

    for m in version_re.finditer(data):
        candidate = m.group(0)
        start = m.start()
        # CONSTANT_Utf8 검증: tag=1, length big-endian 2바이트
        if start >= 3:
            tag = data[start - 3]
            length = (data[start - 2] << 8) | data[start - 1]
            if tag == 1 and length == len(candidate):
                return candidate.decode('ascii')

    raise ValueError(f"Version string not found in {target}")


def update_mod_info(mod_info_path: str, version: str) -> bool:
    """mod_info.json의 gameVersion 필드를 업데이트한다. 변경 없으면 False 반환."""
    with open(mod_info_path, encoding='utf-8') as f:
        mod_info = json.load(f)

    if mod_info.get('gameVersion') == version:
        return False

    mod_info['gameVersion'] = version

    with open(mod_info_path, 'w', encoding='utf-8') as f:
        json.dump(mod_info, f, indent='\t', ensure_ascii=False)
        f.write('\n')

    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mod', default='starsectorkorean', help='모드 ID')
    args = parser.parse_args()
    mod_id = args.mod

    with open(SCRIPT_DIR / 'config.json', encoding='utf-8') as f:
        paths = json.load(f)['paths']

    game_core = _resolve(paths['game_core'])
    output_mods = _resolve(paths['output_mods'])

    # 버전 감지: 라이브 JAR → .bak 순서로 시도
    version = None
    for jar_name in ('starfarer_obf.jar', 'starfarer_obf.jar.bak'):
        jar_path = os.path.join(game_core, jar_name)
        if os.path.exists(jar_path):
            try:
                version = detect_game_version(jar_path)
                break
            except (FileNotFoundError, ValueError):
                continue

    if version is None:
        print("WARNING: 게임 버전을 감지할 수 없습니다. mod_info.json 업데이트를 건너뜁니다.", file=sys.stderr)
        return

    print(f"감지된 게임 버전: {version}")

    mod_info_path = os.path.join(output_mods, mod_id, 'mod_info.json')
    if not os.path.exists(mod_info_path):
        print(f"ERROR: mod_info.json 없음: {mod_info_path}", file=sys.stderr)
        sys.exit(1)

    changed = update_mod_info(mod_info_path, version)
    if changed:
        print(f"mod_info.json 업데이트 완료: gameVersion = {version}")
    else:
        print(f"mod_info.json 변경 없음 (이미 {version})")


if __name__ == '__main__':
    main()
