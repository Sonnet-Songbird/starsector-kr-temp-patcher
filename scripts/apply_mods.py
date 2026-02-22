#!/usr/bin/env python3
"""
apply_mods.py - output/mods/ → game/mods/ 복사 (활성화된 모드만)

적용 전 .bak 백업 (game_mods/{id}.bak/ 이미 있으면 skip).
"""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from patch_utils import load_config, resolve_path


def main():
    cfg = load_config()
    paths = cfg['paths']
    game_mods = Path(resolve_path(paths['game_mods']))
    output_mods = Path(resolve_path(paths['output_mods']))
    mods = cfg.get('mods', [])

    enabled = [m for m in mods if m.get('enabled', True)]
    print(f"적용 대상 모드: {[m['id'] for m in enabled]}")

    for mod_cfg in enabled:
        mod_id = mod_cfg['id']
        src = output_mods / mod_id
        dst = game_mods / mod_id
        bak = game_mods / (mod_id + '.bak')

        print(f"\n[{mod_id}]")

        if not src.is_dir():
            print(f"  WARN: output/{mod_id} 없음 — 건너뜀")
            continue

        # 백업 (최초 1회)
        if dst.is_dir() and not bak.exists():
            shutil.copytree(str(dst), str(bak))
            print(f"  백업: {dst} → {bak}")
        elif bak.exists():
            print(f"  백업 이미 존재: {bak} (skip)")

        # 적용 (덮어쓰기, dirs_exist_ok=True로 Windows 파일 잠금 방지)
        shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
        print(f"  적용: {src} → {dst}")

    print("\napply_mods 완료.")


if __name__ == '__main__':
    main()
