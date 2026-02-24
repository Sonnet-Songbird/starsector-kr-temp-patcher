#!/usr/bin/env python3
"""sync_spec_csvs.py — 스펙 CSV를 바닐라 최신 버전 기반으로 재생성

동작:
  1. starsector-core/data/ 의 바닐라 CSV를 기준 파일로 사용 (스펙 정확)
  2. patches/common.json 번역 사전으로 표시용 컬럼(name, desc 등)을 번역
  3. 결과를 patches/starsectorkorean/data/ 에 오버레이로 저장

  → 기존 한글 모드 CSV의 구버전 스펙 완전 배제
  → 바닐라 기준이므로 신버전 추가 항목도 자동 포함
  → 번역 사전에 없는 항목은 영문 그대로 유지

제외 파일 (patches/ 에서 별도 관리):
  data/campaign/rules.csv
  data/strings/descriptions.csv
  data/config/hull_mods.csv         (바닐라 없음)
  data/config/version/...           (바닐라 없음)

Usage:
  python scripts/sync_spec_csvs.py [--dry-run]
"""

import csv
import io
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
BASE_DIR   = SCRIPT_DIR.parent

# patches/ 에서 이미 별도 관리 중인 파일 — 덮어쓰지 않음
SKIP_FILES = {
    'campaign/rules.csv',
    'strings/descriptions.csv',
    'config/hull_mods.csv',
    'config/version/version_files.csv',
}

# 번역 대상 컬럼 명시적 허용 목록 — 이 목록에 있는 컬럼만 번역
# (스킵 목록 방식은 새 컬럼이 추가될 때 예기치 않게 번역될 위험이 있음)
TRANSLATE_COLUMNS = {
    'name',               # 항목 이름 (함선·무기·스킬 등)
    'designation',        # 함선 등급 (Destroyer, Cruiser 등)
    'desc',               # 짧은 설명 텍스트
    'description',        # 긴 설명 텍스트
    'notes',              # 비고
    'role desc',          # 전투기 편대 역할 설명
    'summary',            # 요약 텍스트
    'text',               # 텍스트 (rules.csv 는 SKIP_FILES 로 보호)
    'title',              # 제목
    'short description',  # 짧은 설명 (일부 파일)
}


# ─── CSV 유틸 ────────────────────────────────────────────────────────────────

def parse_csv(path: Path):
    """Starsector CSV 파싱. 반환: (headers, rows_as_lists, raw_lines)"""
    text  = path.read_text(encoding='utf-8', errors='replace')
    rows  = list(csv.reader(io.StringIO(text)))
    lines = text.splitlines(keepends=True)

    if not rows:
        return [], [], lines

    # 헤더 행 찾기
    hdr_idx = 0
    for i, row in enumerate(rows):
        if row and row[0].strip() and not row[0].strip().startswith('#'):
            hdr_idx = i
            break

    headers   = [h.strip() for h in rows[hdr_idx]]
    data_rows = rows[hdr_idx + 1:]

    return headers, data_rows, hdr_idx


def translate_csv(path: Path, output_path: Path,
                  translations: dict, dry_run: bool) -> tuple:
    """
    바닐라 CSV를 읽어 translations 사전으로 번역한 뒤 output_path에 저장.
    반환: (총 행 수, 번역된 셀 수)
    """
    text     = path.read_text(encoding='utf-8', errors='replace')
    raw_rows = list(csv.reader(io.StringIO(text)))

    if not raw_rows:
        return 0, 0

    # 헤더 행 위치 탐지
    hdr_idx = 0
    for i, row in enumerate(raw_rows):
        if row and row[0].strip() and not row[0].strip().startswith('#'):
            hdr_idx = i
            break

    headers = [h.strip() for h in raw_rows[hdr_idx]]

    # 번역 대상 컬럼 인덱스 — TRANSLATE_COLUMNS 에 명시된 컬럼만 번역
    translate_lower = {c.lower() for c in TRANSLATE_COLUMNS}
    translate_cols = set()
    for i, h in enumerate(headers):
        if h.strip().lower() in translate_lower:
            translate_cols.add(i)

    translated_cells = 0
    out_rows = []

    for row_idx, row in enumerate(raw_rows):
        if row_idx < hdr_idx:
            out_rows.append(row)  # 헤더 이전 주석/빈 행 그대로
            continue
        if row_idx == hdr_idx:
            out_rows.append(row)  # 헤더 행 그대로
            continue

        new_row = list(row)
        # 길이 보정
        while len(new_row) < len(headers):
            new_row.append('')

        for col_i in translate_cols:
            if col_i >= len(new_row):
                continue
            val = new_row[col_i]
            if val in translations:
                new_row[col_i] = translations[val]
                translated_cells += 1

        out_rows.append(new_row)

    data_rows = [r for r in out_rows[hdr_idx + 1:] if r]

    if not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        buf = io.StringIO()
        w   = csv.writer(buf, lineterminator='\n')
        for row in out_rows:
            w.writerow(row)
        output_path.write_text(buf.getvalue(), encoding='utf-8')

    return len(data_rows), translated_cells


# ─── 메인 ────────────────────────────────────────────────────────────────────

def main():
    dry_run = '--dry-run' in sys.argv

    with open(BASE_DIR / 'config.json', encoding='utf-8') as f:
        config = json.load(f)
    paths = config['paths']

    def resolve(key):
        p = paths[key]
        if p.startswith('./') or p.startswith('../'):
            return (BASE_DIR / p).resolve()
        return Path(p)

    game_core = resolve('game_core')
    game_mods = resolve('game_mods')
    patches   = resolve('patches')

    vanilla_root = game_core / 'data'
    korean_root  = game_mods / 'starsectorkorean' / 'data'
    output_root  = patches   / 'starsectorkorean' / 'data'

    # 번역 사전 로드 (common + api_jar + obf_jar 병합)
    translations = {}
    for key, label in [('translations', 'common.json'),
                        ('api_trans',   'api_jar.json'),
                        ('obf_trans',   'obf_jar.json')]:
        p = paths.get(key, '')
        if not p:
            continue
        path = (BASE_DIR / p).resolve() if p.startswith('.') else Path(p)
        if path.exists():
            with open(path, encoding='utf-8') as f:
                chunk = json.load(f)
            translations.update(chunk)
            print(f'  + {label}: {len(chunk):,}개')
    print(f'번역 사전 합계: {len(translations):,}개 항목')

    print('=' * 60)
    print('sync_spec_csvs — 바닐라 CSV + common.json 번역 적용')
    print('=' * 60)
    print(f'바닐라:  {vanilla_root}')
    print(f'출력:    {output_root}')
    if dry_run:
        print('[DRY RUN 모드 — 파일 저장 안 함]')

    total_files  = 0
    total_cells  = 0
    skipped      = 0

    # 한글 모드의 모든 CSV 대상 파일 순회 (바닐라 대응 파일이 있는 것만)
    for korean_csv in sorted(korean_root.rglob('*.csv')):
        rel     = korean_csv.relative_to(korean_root)
        rel_str = rel.as_posix()

        if rel_str in SKIP_FILES:
            print(f'\n  [SKIP] {rel_str}')
            skipped += 1
            continue

        vanilla_csv = vanilla_root / rel

        if not vanilla_csv.exists():
            print(f'\n  [SKIP] 바닐라 없음: {rel_str}')
            skipped += 1
            continue

        output_csv = output_root / rel

        rows, cells = translate_csv(
            vanilla_csv, output_csv, translations, dry_run
        )

        status = '저장' if not dry_run else 'dry-run'
        print(f'\n  [{rel_str}]')
        print(f'    바닐라 {rows}행, 번역된 셀 {cells}개 → {status}')
        if not dry_run:
            print(f'    {output_csv.relative_to(BASE_DIR)}')

        total_files += 1
        total_cells += cells

    print('\n' + '=' * 60)
    print(f'완료: {total_files}개 파일, {total_cells}개 셀 번역, {skipped}개 건너뜀')
    if not dry_run:
        print('다음 단계: python build.py all')
    print('=' * 60)


if __name__ == '__main__':
    main()
