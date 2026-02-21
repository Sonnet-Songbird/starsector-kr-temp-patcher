#!/usr/bin/env python3
"""
apply_mods.py - output/mods/ → game/mods/ 복사 (활성화된 모드만)

적용 전 .bak 백업 (game_mods/{id}.bak/ 이미 있으면 skip).
"""

import json
import os
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent


def _resolve(p, base=SCRIPT_DIR):
    if isinstance(p, str) and (p.startswith('./') or p.startswith('../') or p == '.'):
        return str((base / p).resolve())
    return p


def main():
    with open(SCRIPT_DIR / 'config.json', encoding='utf-8') as f:
        cfg = json.load(f)

    paths = cfg['paths']
    game_mods = Path(_resolve(paths['game_mods']))
    output_mods = Path(_resolve(paths['output_mods']))
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

        # 적용 (덮어쓰기)
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(str(src), str(dst))
        print(f"  적용: {src} → {dst}")

    print("\napply_mods 완료.")


if __name__ == '__main__':
    main()
