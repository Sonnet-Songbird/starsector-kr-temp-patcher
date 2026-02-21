#!/usr/bin/env python3
"""
build_mods.py - config.json의 mods 배열을 기반으로 모드 빌드

흐름 (모드별):
  1. 원본 모드 복사: game_mods/{id}/ → output/mods/{id}/
  2. 번역 사전 적용: patches/{id}/translations.json → 출력 디렉토리 텍스트 파일
     (비어있으면 skip)
  3. 파일 오버레이: patches/{id}/data/, patches/{id}/graphics/ → output/{id}/
  4. post_build 스크립트 실행

CSV 번역 규칙:
  - 셀 단위 정확 일치
  - 스킵 컬럼: CSV_SKIP_COLUMNS 집합에 포함된 컬럼 헤더

JSON 번역 규칙:
  - 재귀적 string 값 교체 (키는 건드리지 않음)
  - mod_info.json은 번역 제외
"""

import csv
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent

# CSV에서 번역하지 않을 컬럼 헤더 (식별자/인덱스 컬럼)
CSV_SKIP_COLUMNS = {
    'id', 'system id', 'type', 'sprite', 'tags', 'tier', 'rarity',
    'hints', 'turret covers', 'fighter bays', 'defense id', 'base value',
    'order', 'reqPoints', 'reqPointsPerExtraSkill', 'combat officer', 'admiral',
    'is player npc', 'ship id', 'wing id', 'weapon id', 'hullmod id',
    'sub id', 'tech/manufacturer', 'source',
}


def _resolve(p, base=SCRIPT_DIR):
    if isinstance(p, str) and (p.startswith('./') or p.startswith('../') or p == '.'):
        return str((base / p).resolve())
    return p


def translate_json_value(obj, translations: dict):
    """JSON 객체를 재귀적으로 순회하며 string 값 교체."""
    if isinstance(obj, str):
        return translations.get(obj, obj)
    if isinstance(obj, dict):
        return {k: translate_json_value(v, translations) for k, v in obj.items()}
    if isinstance(obj, list):
        return [translate_json_value(item, translations) for item in obj]
    return obj


def translate_json_file(filepath: Path, translations: dict) -> bool:
    """JSON 파일에 번역 적용. 변경 있으면 True."""
    try:
        text = filepath.read_text(encoding='utf-8')
        obj = json.loads(text)
    except Exception as e:
        print(f"    JSON 읽기 실패 {filepath.name}: {e}")
        return False

    new_obj = translate_json_value(obj, translations)
    if new_obj == obj:
        return False

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(new_obj, f, ensure_ascii=False, indent=2)
    return True


def translate_csv_file(filepath: Path, translations: dict) -> bool:
    """CSV 파일에 번역 적용. 변경 있으면 True."""
    try:
        text = filepath.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        try:
            text = filepath.read_text(encoding='utf-8-sig')
        except Exception as e:
            print(f"    CSV 읽기 실패 {filepath.name}: {e}")
            return False

    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return False

    headers = rows[0]
    # 번역 가능한 컬럼 인덱스 (첫 번째 컬럼은 항상 스킵, skip 목록에 없는 컬럼만)
    translatable_cols = set()
    for i, h in enumerate(headers):
        if i == 0:
            continue  # 첫 번째 컬럼은 항상 스킵 (보통 id)
        if h.strip().lower() not in {c.lower() for c in CSV_SKIP_COLUMNS}:
            translatable_cols.add(i)

    changed = False
    new_rows = [headers]
    for row in rows[1:]:
        new_row = list(row)
        for i in translatable_cols:
            if i < len(new_row):
                cell = new_row[i]
                if cell in translations:
                    new_row[i] = translations[cell]
                    changed = True
        new_rows.append(new_row)

    if not changed:
        return False

    out = io.StringIO()
    writer = csv.writer(out, lineterminator='\n')
    writer.writerows(new_rows)
    filepath.write_text(out.getvalue(), encoding='utf-8')
    return True


def apply_translations_to_dir(mod_dir: Path, translations: dict):
    """모드 출력 디렉토리의 모든 텍스트 파일에 번역 적용."""
    if not translations:
        return

    json_changed = 0
    csv_changed = 0
    for fpath in mod_dir.rglob('*'):
        if not fpath.is_file():
            continue
        if fpath.name == 'mod_info.json':
            continue

        if fpath.suffix == '.json':
            if translate_json_file(fpath, translations):
                json_changed += 1
        elif fpath.suffix == '.csv':
            if translate_csv_file(fpath, translations):
                csv_changed += 1

    print(f"  번역 적용: JSON {json_changed}개, CSV {csv_changed}개 파일 변경")


def _load_blocked_strings(paths) -> set:
    """patches/exclusions.json에서 blocked_strings 로드."""
    excl_file = _resolve(paths.get('exclusions', ''))
    if excl_file and os.path.exists(excl_file):
        with open(excl_file, encoding='utf-8') as f:
            excl = json.load(f)
        return set(excl.get('blocked_strings', []))
    return set()


def build_mod(mod_cfg: dict, paths: dict, python_cmd: str, blocked_strings: set = None):
    mod_id = mod_cfg['id']
    game_mods = Path(_resolve(paths['game_mods']))
    patches = Path(_resolve(paths['patches']))
    output_mods = Path(_resolve(paths['output_mods']))

    src = game_mods / mod_id
    patch_dir = patches / mod_id
    dst = output_mods / mod_id

    print(f"\n[{mod_id}]")

    if not src.is_dir():
        print(f"  WARN: 원본 모드 없음: {src} — 건너뜀")
        return

    # 1. 원본 모드 → output
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    print(f"  원본 복사: {src} → {dst}")

    # 2. 번역 사전 적용 (translations.json 비어있으면 skip)
    trans_file = patch_dir / 'translations.json'
    if trans_file.exists():
        try:
            with open(trans_file, encoding='utf-8') as f:
                mod_translations = json.load(f)
            if mod_translations:
                if blocked_strings:
                    before = len(mod_translations)
                    mod_translations = {k: v for k, v in mod_translations.items()
                                        if k not in blocked_strings}
                    removed = before - len(mod_translations)
                    if removed:
                        print(f"  제외: blocked_strings {removed}개")
                print(f"  번역 사전 {len(mod_translations)}개 항목 적용 중...")
                apply_translations_to_dir(dst, mod_translations)
            else:
                print(f"  번역 사전: 비어있음 (skip)")
        except Exception as e:
            print(f"  WARN: translations.json 읽기 실패: {e}")

    # 3. 파일 오버레이
    overlaid = 0
    for sub in ['data', 'graphics']:
        p = patch_dir / sub
        if p.is_dir():
            shutil.copytree(str(p), str(dst / sub), dirs_exist_ok=True)
            overlaid += sum(1 for _ in p.rglob('*') if _.is_file())
    if overlaid:
        print(f"  오버레이: {overlaid}개 파일")

    # 4. post_build 스크립트
    for script_rel in mod_cfg.get('post_build', []):
        script = SCRIPT_DIR / script_rel
        cmd = [python_cmd, str(script), '--mod', mod_id]
        print(f"  post_build: {script_rel}")
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode != 0:
            print(f"  ERROR: {script_rel} 실패 (exit {result.returncode})", file=sys.stderr)
            sys.exit(result.returncode)


def main():
    with open(SCRIPT_DIR / 'config.json', encoding='utf-8') as f:
        cfg = json.load(f)

    paths = cfg['paths']
    python_cmd = paths.get('python', 'python')
    mods = cfg.get('mods', [])

    output_mods = Path(_resolve(paths['output_mods']))
    output_mods.mkdir(parents=True, exist_ok=True)

    blocked_strings = _load_blocked_strings(paths)

    enabled = [m for m in mods if m.get('enabled', True)]
    print(f"빌드 대상 모드: {[m['id'] for m in enabled]}")

    for mod_cfg in enabled:
        build_mod(mod_cfg, paths, python_cmd, blocked_strings)

    print("\nbuild_mods 완료.")


if __name__ == '__main__':
    main()
