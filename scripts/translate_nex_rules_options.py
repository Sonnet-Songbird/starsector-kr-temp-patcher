#!/usr/bin/env python3
"""
translate_nex_rules_options.py — Nexerelin rules.csv options 컬럼 번역

rules.csv의 options 컬럼은 각 줄이 [priority:]id:text 형식이므로
일반적인 CSV 셀 교체로는 번역 불가능. 전용 파서로 text 부분만 번역.

post_build 훅으로 실행:
    python translate_nex_rules_options.py --mod Nexerelin
"""

import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from patch_utils import load_config, load_exclusions, resolve_path


def _split_option_line(line: str):
    """
    options 컬럼 한 줄에서 (prefix, text) 분리.

    형식:
        id:text
        priority:id:text
        #id:text
        #priority:id:text

    반환: (prefix, text) — prefix는 id 부분 포함, text는 실제 표시 텍스트.
    재조합: prefix + translated_text
    """
    s = line.rstrip()
    hash_prefix = ''
    if s.startswith('#'):
        hash_prefix = '#'
        s = s[1:]

    colon1 = s.find(':')
    if colon1 == -1:
        return (hash_prefix, s)

    before_first = s[:colon1]
    rest = s[colon1 + 1:]

    if before_first.isdigit():
        # priority:id:text
        colon2 = rest.find(':')
        if colon2 != -1:
            id_part = rest[:colon2]
            text = rest[colon2 + 1:]
            prefix = hash_prefix + before_first + ':' + id_part + ':'
            return (prefix, text)
        # priority:text (no separate id)
        return (hash_prefix + before_first + ':', rest)

    if re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', before_first):
        # id:text
        return (hash_prefix + before_first + ':', rest)

    # Unknown format — treat whole line as text
    return (hash_prefix, s)


def translate_options_cell(cell: str, translations: dict):
    """
    options 컬럼 셀 전체 번역. 각 줄의 text 부분만 번역.
    반환: (new_cell, changed: bool)
    """
    lines = cell.split('\n')
    new_lines = []
    changed = False

    for line in lines:
        if not line.strip():
            new_lines.append(line)
            continue

        prefix, text = _split_option_line(line)
        new_text = translations.get(text, text)

        if new_text != text:
            changed = True

        new_lines.append(prefix + new_text)

    return '\n'.join(new_lines), changed


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--mod', required=True)
    args, _ = parser.parse_known_args()

    cfg = load_config()
    paths = cfg['paths']

    output_mods = Path(resolve_path(paths['output_mods']))
    mod_dir = output_mods / args.mod
    patches = Path(resolve_path(paths['patches']))

    # Load translations
    trans_file = patches / args.mod / 'translations.json'
    if not trans_file.exists():
        print(f'  [{args.mod}] translations.json 없음 — 건너뜀')
        return

    with open(trans_file, encoding='utf-8') as f:
        translations = json.load(f)

    # Apply exclusions
    _, blocked_strings, _ = load_exclusions(paths, args.mod)
    if blocked_strings:
        before = len(translations)
        translations = {k: v for k, v in translations.items() if k not in blocked_strings}
        removed = before - len(translations)
        if removed:
            print(f'  [{args.mod}] blocked_strings {removed}개 제외')

    print(f'  [{args.mod}] options 번역 사전: {len(translations)}개')

    # Process rules.csv (and UNGP_rules.csv if present)
    target_files = [
        mod_dir / 'data/campaign/rules.csv',
        mod_dir / 'data/campaign/UNGP_rules.csv',
    ]

    for rules_path in target_files:
        if not rules_path.exists():
            continue

        try:
            text = rules_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            text = rules_path.read_text(encoding='utf-8-sig')

        rows = list(csv.reader(io.StringIO(text)))
        if not rows:
            continue

        headers = rows[0]
        options_col = None
        for i, h in enumerate(headers):
            if h.strip().lower() == 'options':
                options_col = i
                break

        if options_col is None:
            print(f'  {rules_path.name}: options 컬럼 없음 — 건너뜀')
            continue

        changed_cells = 0
        new_rows = [headers]
        for row in rows[1:]:
            new_row = list(row)
            if options_col < len(new_row) and new_row[options_col].strip():
                new_cell, was_changed = translate_options_cell(
                    new_row[options_col], translations
                )
                if was_changed:
                    new_row[options_col] = new_cell
                    changed_cells += 1
            new_rows.append(new_row)

        if changed_cells > 0:
            out = io.StringIO()
            writer = csv.writer(out, lineterminator='\n')
            writer.writerows(new_rows)
            rules_path.write_text(out.getvalue(), encoding='utf-8')
            print(f'  {rules_path.name}: {changed_cells}개 options 셀 번역 완료')
        else:
            print(f'  {rules_path.name}: 변경 없음')


if __name__ == '__main__':
    main()
