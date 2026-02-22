#!/usr/bin/env python3
"""
extract_mod_strings.py - 범용 모드 번역 후보 추출기 (분석 도구, 수동 실행)

모드 JAR + 데이터 파일에서 번역 후보를 추출해 intermediate/{mod_id}_candidates.json 출력.

사용법:
    python scripts/extract_mod_strings.py --mod Nexerelin [--skip-jar]

단계:
    1. CFR으로 JAR 디컴파일 → intermediate/{mod_id}_src/
    2. .java 파일 regex 스캔 → 문자열 리터럴 추출
    3. 데이터 파일(strings.json, CSV) 스캔
    4. 필터:
        - len < 4 이고 공백 없음 → 제외 (ID 가능성)
        - 이미 common.json 또는 patches/{mod_id}/translations.json에 있음 → 제외
        - 순수 숫자, URL, 파일경로 패턴 → 제외

출력:
    intermediate/{mod_id}_candidates.json   { "English text": null, ... }
"""

import argparse
import csv
import io
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))


def _resolve(p, base=SCRIPT_DIR):
    if isinstance(p, str) and (p.startswith('./') or p.startswith('../') or p == '.'):
        return str((base / p).resolve())
    return p


# ──────────────────────────────────────────────────────────────────────────────
# 필터 규칙
# ──────────────────────────────────────────────────────────────────────────────

_RE_PURE_NUMBER = re.compile(r'^[\d\s\.,\-+%]+$')
_RE_URL = re.compile(r'^https?://')
_RE_PATH = re.compile(r'^[\w\-./\\]+\.(png|jpg|ogg|wav|json|csv|ini|txt|class|java)$', re.I)
_RE_CLASS_PATH = re.compile(r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$')  # com.example.Foo
_RE_SHORT_ID = re.compile(r'^[A-Za-z_][A-Za-z0-9_\-]*$')  # single-word no spaces


def _is_candidate(s: str, existing: set) -> bool:
    """번역 후보 여부 판별."""
    if not s or not s.strip():
        return False
    s = s.strip()

    # 이미 번역됨
    if s in existing:
        return False

    # 순수 숫자/수식
    if _RE_PURE_NUMBER.match(s):
        return False

    # URL
    if _RE_URL.match(s):
        return False

    # 파일 경로 패턴
    if _RE_PATH.match(s):
        return False

    # Java 패키지 경로 (com.example.Foo)
    if _RE_CLASS_PATH.match(s):
        return False

    # 길이 < 4 이고 공백 없음 → ID 가능성 높음
    if len(s) < 4 and ' ' not in s:
        return False

    # 한국어 이미 포함 (이미 번역된 것)
    if any('\uAC00' <= c <= '\uD7A3' for c in s):
        return False

    return True


# ──────────────────────────────────────────────────────────────────────────────
# Java 소스 스캔
# ──────────────────────────────────────────────────────────────────────────────

_RE_STRING_LITERAL = re.compile(r'"((?:[^"\\]|\\.)*)"')


def extract_from_java_sources(src_dir: Path, existing: set) -> set:
    """디컴파일된 .java 파일에서 문자열 리터럴 추출."""
    candidates = set()
    java_files = list(src_dir.rglob('*.java'))
    print(f"  Java 소스 스캔: {len(java_files)}개 파일")

    for jf in java_files:
        try:
            text = jf.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        for m in _RE_STRING_LITERAL.finditer(text):
            raw = m.group(1)
            # 이스케이프 처리 (간단)
            s = raw.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace('\\\\', '\\')
            if _is_candidate(s, existing):
                candidates.add(s)

    return candidates


# ──────────────────────────────────────────────────────────────────────────────
# 데이터 파일 스캔
# ──────────────────────────────────────────────────────────────────────────────

CSV_SKIP_COLUMNS = {
    'id', 'system id', 'type', 'sprite', 'tags', 'tier', 'rarity',
    'hints', 'source', 'order', 'tech/manufacturer',
}


def extract_from_data_files(mod_dir: Path, existing: set) -> set:
    """모드 data/ 디렉토리의 JSON/CSV에서 번역 후보 추출."""
    candidates = set()
    data_dir = mod_dir / 'data'
    if not data_dir.is_dir():
        return candidates

    for fpath in data_dir.rglob('*'):
        if not fpath.is_file():
            continue
        if fpath.name == 'mod_info.json':
            continue

        if fpath.suffix == '.json':
            try:
                obj = json.loads(fpath.read_text(encoding='utf-8', errors='replace'))
                _collect_json_strings(obj, existing, candidates)
            except Exception:
                pass

        elif fpath.suffix == '.csv':
            try:
                text = fpath.read_text(encoding='utf-8', errors='replace')
                rows = list(csv.reader(io.StringIO(text)))
                if not rows:
                    continue
                headers = rows[0]
                translatable_cols = set()
                for i, h in enumerate(headers):
                    if i == 0:
                        continue
                    if h.strip().lower() not in {c.lower() for c in CSV_SKIP_COLUMNS}:
                        translatable_cols.add(i)
                for row in rows[1:]:
                    for i in translatable_cols:
                        if i < len(row):
                            cell = row[i].strip()
                            # rules.csv: 멀티라인/숫자시작 제외
                            if cell and not cell[0].isdigit() and '\n' not in cell:
                                if _is_candidate(cell, existing):
                                    candidates.add(cell)
            except Exception:
                pass

    return candidates


def _collect_json_strings(obj, existing: set, result: set):
    if isinstance(obj, str):
        if _is_candidate(obj, existing):
            result.add(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _collect_json_strings(v, existing, result)
    elif isinstance(obj, list):
        for item in obj:
            _collect_json_strings(item, existing, result)


# ──────────────────────────────────────────────────────────────────────────────
# JAR 디컴파일
# ──────────────────────────────────────────────────────────────────────────────

def decompile_jar(jar_path: Path, out_dir: Path, cfr_jar: Path, java_cmd: str) -> bool:
    """CFR로 JAR 디컴파일."""
    if out_dir.exists() and any(out_dir.rglob('*.java')):
        print(f"  디컴파일 스킵 (이미 존재): {out_dir}")
        return True

    out_dir.mkdir(parents=True, exist_ok=True)
    if not cfr_jar.exists():
        print(f"  WARN: CFR JAR 없음: {cfr_jar} — JAR 소스 스캔 건너뜀")
        return False

    print(f"  CFR 디컴파일: {jar_path.name} → {out_dir}")
    cmd = [java_cmd, '-jar', str(cfr_jar), str(jar_path),
           '--outputdir', str(out_dir), '--silent', 'true']
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  WARN: CFR 오류 (일부 클래스 디컴파일 실패할 수 있음)")
    return True


# ──────────────────────────────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='모드 번역 후보 추출')
    parser.add_argument('--mod', required=True, help='모드 ID (config.json mods[].id)')
    parser.add_argument('--skip-jar', action='store_true', help='JAR 디컴파일/스캔 건너뜀')
    args = parser.parse_args()
    mod_id = args.mod

    with open(SCRIPT_DIR / 'config.json', encoding='utf-8') as f:
        cfg = json.load(f)

    paths = cfg['paths']

    mod_cfg = next((m for m in cfg.get('mods', []) if m['id'] == mod_id), None)
    if mod_cfg is None:
        print(f"ERROR: config.json에 모드 '{mod_id}' 없음", file=sys.stderr)
        sys.exit(1)

    game_mods = Path(_resolve(paths['game_mods']))
    patches_dir = Path(_resolve(paths['patches']))
    intermediate = SCRIPT_DIR / 'intermediate'
    intermediate.mkdir(exist_ok=True)

    mod_dir = game_mods / mod_id
    if not mod_dir.is_dir():
        print(f"ERROR: 모드 폴더 없음: {mod_dir}", file=sys.stderr)
        sys.exit(1)

    # 기존 번역 사전 로드 (중복 제외용)
    existing = set()
    common_file = _resolve(paths.get('translations', ''))
    if common_file and os.path.exists(common_file):
        with open(common_file, encoding='utf-8') as f:
            existing.update(json.load(f).keys())

    mod_trans_file = patches_dir / mod_id / 'translations.json'
    if mod_trans_file.exists():
        with open(mod_trans_file, encoding='utf-8') as f:
            existing.update(json.load(f).keys())

    print(f"\n[{mod_id}] 번역 후보 추출")
    print(f"  기존 번역 제외 기준: {len(existing)}개 항목")

    candidates = set()

    # 1. 데이터 파일 스캔
    print(f"\n데이터 파일 스캔...")
    data_cands = extract_from_data_files(mod_dir, existing)
    print(f"  데이터 파일 후보: {len(data_cands)}개")
    candidates.update(data_cands)

    # 2. JAR 디컴파일 + 소스 스캔
    if not args.skip_jar:
        mod_jar = mod_cfg.get('mod_jar')
        if mod_jar:
            jar_paths = [mod_jar] if isinstance(mod_jar, str) else list(mod_jar)
            for jar_rel in jar_paths:
                jar_path = mod_dir / jar_rel
                if not jar_path.exists():
                    print(f"  WARN: JAR 없음: {jar_path}")
                    continue

                jar_name = Path(jar_rel).stem
                src_dir = intermediate / f"{mod_id}_{jar_name}_src"
                cfr_jar = SCRIPT_DIR / 'tools' / 'cfr.jar'
                java_cmd = str(Path(_resolve(paths.get('game_core', '../starsector-core'))).parent / 'jre' / 'bin' / 'java')
                if not Path(java_cmd).exists():
                    java_cmd = 'java'

                if decompile_jar(jar_path, src_dir, cfr_jar, java_cmd):
                    print(f"\nJAR 소스 스캔: {jar_rel}")
                    jar_cands = extract_from_java_sources(src_dir, existing)
                    print(f"  JAR 소스 후보: {len(jar_cands)}개")
                    candidates.update(jar_cands)
        else:
            print(f"  mod_jar 미설정, JAR 스캔 건너뜀")

    # 3. 출력
    out_file = intermediate / f"{mod_id}_candidates.json"
    output = {s: None for s in sorted(candidates)}
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n추출 완료: {len(candidates)}개 후보")
    print(f"출력: {out_file}")
    print(f"\n다음 단계: patches/{mod_id}/translations.json에 번역 추가 후 build.py update_mod 실행")


if __name__ == '__main__':
    main()
