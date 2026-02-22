#!/usr/bin/env python3
"""
build_mods.py - config.json의 mods 배열을 기반으로 모드 빌드

흐름 (모드별):
  1. 복원 (기본값): game_mods/{id}.bak/ → game_mods/{id}/ (이중 패치 방지)
  2. 원본 모드 복사: game_mods/{id}/ → output/mods/{id}/
  3. 번역 사전 적용: patches/{id}/translations.json → 출력 디렉토리 텍스트 파일
     (비어있으면 skip)
  4. 파일 오버레이: patches/{id}/data/, patches/{id}/graphics/ → output/{id}/
  5. post_build 스크립트 실행

옵션:
  --no-restore    .bak → live 복원 단계 건너뜀. live 디렉토리를 그대로 소스로 사용.

CSV 번역 규칙:
  - 셀 단위 정확 일치
  - 스킵 컬럼: CSV_SKIP_COLUMNS 집합에 포함된 컬럼 헤더

JSON 번역 규칙:
  - 재귀적 string 값 교체 (키는 건드리지 않음)
  - mod_info.json은 번역 제외
"""

import argparse
import csv
import io
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from patch_utils import load_config, load_exclusions_file, resolve_path

_SCRIPT_ROOT = Path(__file__).parent.parent  # scripts/ → kr_work/

# JSON 값 번역 시 건너뛸 키 (전역 기본값).
# 이 키 아래 값은 코드 식별자로 간주하여 번역하지 않음.
# 모드별 추가 키는 patches/{mod_id}/exclusions.json → "blocked_json_keys" 에 등록.
#
# CSV_SKIP_COLUMNS 와 유사하나, JSON은 중첩 구조이므로 명확하게 식별자인 키만 포함.
# (예: "options" 는 JSON에서 사용자 표시 텍스트일 수 있으므로 제외)
BLOCKED_JSON_KEYS = {
    # 프로그래밍 식별자
    'id', 'factionId', 'faction', 'system', 'tags',
    # Java 클래스/스크립트 경로
    'className', 'class', 'plugin', 'script', 'ai', 'effectPlugin', 'implementation',
    # 파일 경로/에셋 ID
    'icon', 'image', 'sprite', 'sound', 'sound_id', 'spritePath', 'iconPath',
}

# CSV에서 번역하지 않을 컬럼 헤더 (식별자/인덱스 컬럼)
CSV_SKIP_COLUMNS = {
    # 기본 식별자
    'id', 'system id', 'type', 'sprite', 'tags', 'tier', 'rarity',
    'hints', 'turret covers', 'fighter bays', 'defense id', 'base value',
    'order', 'reqPoints', 'reqPointsPerExtraSkill', 'combat officer', 'admiral',
    'is player npc', 'ship id', 'wing id', 'weapon id', 'hullmod id',
    'sub id', 'tech/manufacturer', 'source',
    # 이벤트/상태 식별자 (reports.csv 등에서 key 구성에 사용)
    'event_type', 'event_stage', 'trigger',
    # 세력/시스템 ID (프로그래밍 식별자)
    'faction', 'system',
    # Java 클래스/스크립트 경로
    'plugin', 'script', 'ai', 'effectPlugin', 'class',
    # 파일 경로/에셋 ID
    'icon', 'image', 'sound_id', 'channels', 'spritePath', 'iconPath',
    # 기타 기술적 컬럼
    'implementation notes', 'uiTags', 'sortOrder',
}


def _load_json_lazy(text: str):
    """
    Starsector 비표준 JSON 파서 (3단계 시도).

    1. 표준 json.loads
    2. # 주석 + 후행 쉼표 제거
    3. 추가로 unquoted 키 자동 인용 (tips.json 등 대응)
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 단계 2: # 주석 + 후행 쉼표
    cleaned = re.sub(r'(?m)#[^\n]*', '', text)
    cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 단계 3: unquoted 키 자동 인용 (예: tips:[ → "tips":[)
    # 문자열 리터럴 안이 아닌 위치의 bareword key 만 처리
    cleaned2 = re.sub(r'(?<!["\w])([a-zA-Z_][a-zA-Z0-9_]*)(\s*:)(?!\s*:)', r'"\1"\2', cleaned)
    return json.loads(cleaned2)


def translate_json_value(obj, translations: dict,
                          blocked_json_keys: set = None, _parent_key: str = None):
    """
    JSON 객체를 재귀적으로 순회하며 string 값 교체.

    blocked_json_keys 에 속하는 키 아래의 값은 코드 식별자로 간주하여 번역 건너뜀.
    예: "specializations": ["saboteur"] → "saboteur" 번역 안 함
    """
    if isinstance(obj, str):
        if blocked_json_keys and _parent_key in blocked_json_keys:
            return obj  # 코드 식별자 키 — 번역 건너뜀
        return translations.get(obj, obj)
    if isinstance(obj, dict):
        return {k: translate_json_value(v, translations,
                                        blocked_json_keys=blocked_json_keys, _parent_key=k)
                for k, v in obj.items()}
    if isinstance(obj, list):
        # 리스트 항목은 부모 키를 계속 전달 (예: "specializations": ["saboteur"])
        return [translate_json_value(item, translations,
                                     blocked_json_keys=blocked_json_keys, _parent_key=_parent_key)
                for item in obj]
    return obj


def translate_json_file(filepath: Path, translations: dict,
                         blocked_json_keys: set = None) -> bool:
    """JSON 파일에 번역 적용. 변경 있으면 True."""
    try:
        text = filepath.read_text(encoding='utf-8')
        obj = _load_json_lazy(text)
    except Exception as e:
        print(f"    JSON 읽기 실패 {filepath.name}: {e}")
        return False

    new_obj = translate_json_value(obj, translations, blocked_json_keys=blocked_json_keys)
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


def apply_translations_to_dir(mod_dir: Path, translations: dict,
                               blocked_json_keys: set = None):
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
            if translate_json_file(fpath, translations, blocked_json_keys=blocked_json_keys):
                json_changed += 1
        elif fpath.suffix == '.csv':
            if translate_csv_file(fpath, translations):
                csv_changed += 1

    print(f"  번역 적용: JSON {json_changed}개, CSV {csv_changed}개 파일 변경")


def _load_mod_blocked_json_keys(patch_dir: Path) -> set:
    """patches/{mod_id}/exclusions.json에서 blocked_json_keys 로드.

    이 키 아래 JSON 값은 코드 식별자로 간주하여 번역하지 않음.
    전역 BLOCKED_JSON_KEYS 와 합집합으로 적용됨.
    """
    excl_file = patch_dir / 'exclusions.json'
    if excl_file.exists():
        with open(excl_file, encoding='utf-8') as f:
            excl = json.load(f)
        return set(excl.get('blocked_json_keys', []))
    return set()


def build_mod(mod_cfg: dict, paths: dict, python_cmd: str,
              blocked_strings: set = None, restore: bool = True):
    mod_id = mod_cfg['id']
    game_mods = Path(resolve_path(paths['game_mods']))
    patches = Path(resolve_path(paths['patches']))
    output_mods = Path(resolve_path(paths['output_mods']))

    patch_dir = patches / mod_id
    dst = output_mods / mod_id
    bak = game_mods / (mod_id + '.bak')
    src = game_mods / mod_id

    print(f"\n[{mod_id}]")

    # 1. 복원: .bak → live (기본값, 이중 패치 방지)
    # dirs_exist_ok=True로 삭제 없이 덮어쓰기 — Windows 파일 잠금(WinError 32) 방지
    if restore and bak.is_dir():
        shutil.copytree(str(bak), str(src), dirs_exist_ok=True)
        print(f"  복원: {mod_id}.bak → {mod_id}")
    elif restore:
        print(f"  복원 건너뜀: {mod_id}.bak 없음")
    else:
        print(f"  복원 건너뜀: --no-restore")

    if not src.is_dir():
        print(f"  WARN: 원본 모드 없음: {src} — 건너뜀")
        return

    # 2. 원본 모드 → output
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    print(f"  원본 복사: {mod_id} → {dst}")

    # 3. 번역 사전 적용 (translations.json 비어있으면 skip)
    trans_file = patch_dir / 'translations.json'
    if trans_file.exists():
        try:
            with open(trans_file, encoding='utf-8') as f:
                mod_translations = json.load(f)
            if mod_translations:
                # 전역 + 모드별 blocked_strings 합산
                _, mod_bs, _ = load_exclusions_file(patch_dir / 'exclusions.json')
                mod_blocked = (blocked_strings or set()) | mod_bs
                if mod_blocked:
                    before = len(mod_translations)
                    mod_translations = {k: v for k, v in mod_translations.items()
                                        if k not in mod_blocked}
                    removed = before - len(mod_translations)
                    if removed:
                        print(f"  제외: blocked_strings {removed}개")
                # 전역 + 모드별 blocked_json_keys 합산
                mod_blocked_json_keys = BLOCKED_JSON_KEYS | _load_mod_blocked_json_keys(patch_dir)
                print(f"  번역 사전 {len(mod_translations)}개 항목 적용 중...")
                apply_translations_to_dir(dst, mod_translations,
                                          blocked_json_keys=mod_blocked_json_keys)
            else:
                print(f"  번역 사전: 비어있음 (skip)")
        except Exception as e:
            print(f"  WARN: translations.json 읽기 실패: {e}")

    # 4. 파일 오버레이
    overlaid = 0
    for sub in ['data', 'graphics']:
        p = patch_dir / sub
        if p.is_dir():
            shutil.copytree(str(p), str(dst / sub), dirs_exist_ok=True)
            overlaid += sum(1 for _ in p.rglob('*') if _.is_file())
    if overlaid:
        print(f"  오버레이: {overlaid}개 파일")

    # 5. post_build 스크립트
    for script_rel in mod_cfg.get('post_build', []):
        script = _SCRIPT_ROOT / script_rel
        cmd = [python_cmd, str(script), '--mod', mod_id]
        print(f"  post_build: {script_rel}")
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode != 0:
            print(f"  ERROR: {script_rel} 실패 (exit {result.returncode})", file=sys.stderr)
            sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--no-restore', action='store_true',
                        default=os.environ.get('STARSECTOR_NO_RESTORE') == '1')
    args, _ = parser.parse_known_args()
    restore = not args.no_restore

    cfg = load_config()
    paths = cfg['paths']
    python_cmd = paths.get('python', 'python')
    mods = cfg.get('mods', [])

    output_mods = Path(resolve_path(paths['output_mods']))
    output_mods.mkdir(parents=True, exist_ok=True)

    # 전역 blocked_strings 로드
    _, blocked_strings, _ = load_exclusions_file(resolve_path(paths.get('exclusions', '')))

    enabled = [m for m in mods if m.get('enabled', True)]
    print(f"빌드 대상 모드: {[m['id'] for m in enabled]}")

    for mod_cfg in enabled:
        build_mod(mod_cfg, paths, python_cmd, blocked_strings, restore=restore)

    print("\nbuild_mods 완료.")


if __name__ == '__main__':
    main()
