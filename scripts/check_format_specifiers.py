#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
번역 JSON의 Java 포맷 지정자(%d, %s, %f 등) 정합성 검사.

- 원문(source)과 번역(target)의 지정자 개수가 다르면 COUNT_MISMATCH (수동 확인 필요).
- 순서가 동일하면 안전(FINE).
- 순서가 바뀌었거나 타입이 어긋나면:
  - 그리디 매칭으로 위치 지정자(%N$X)를 도출 가능하면 FIXABLE (--fix 적용 가능).
  - 매칭 불가능하면 UNFIXABLE (수동 확인 필요).

사용:
  python scripts/check_format_specifiers.py            # 전체 스캔, 보고만
  python scripts/check_format_specifiers.py --fix      # FIXABLE 자동 패치
  python scripts/check_format_specifiers.py --json     # 보고를 JSON으로 stdout 출력
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
PATCHES = ROOT / 'patches'

# 일반 평면 dict 형식 (key: source, value: target)
FLAT_TRANS_FILES: list[Path] = [
    PATCHES / 'api_jar.json',
    PATCHES / 'common.json',
    PATCHES / 'obf_jar.json',
    PATCHES / 'Nexerelin' / 'translations.json',
    PATCHES / 'starsectorkorean' / 'translations.json',
]

# 클래스별 중첩 dict 형식: {class_path: {source: target, ...}}
NESTED_TRANS_FILES: list[Path] = [
    PATCHES / 'class_trans.json',
]

# Java Formatter 지정자
# %[argument_index$][flags][width][.precision]conversion
SPEC_RE = re.compile(
    r'%'
    r'(?:(\d+)\$)?'        # 1: argument index (1-based)
    r'([-#+0,(]*)'         # 2: flags (공백 플래그는 오탐 위험으로 제외)
    r'(\d+)?'              # 3: width
    r'(\.\d+)?'            # 4: precision
    r'([a-zA-Z])'          # 5: conversion
)


@dataclass
class Spec:
    start: int
    end: int
    raw: str
    arg_index: int | None
    flags: str
    width: str
    precision: str
    conversion: str


def extract_specs(s: str) -> list[Spec]:
    masked = s.replace('%%', '\x00\x00')  # %%는 리터럴이므로 마스킹
    specs: list[Spec] = []
    for m in SPEC_RE.finditer(masked):
        conv = m.group(5)
        if conv == 'n':  # %n = newline, 인자 미소비
            continue
        idx = int(m.group(1)) if m.group(1) else None
        specs.append(Spec(
            start=m.start(),
            end=m.end(),
            raw=m.group(0),
            arg_index=idx,
            flags=m.group(2) or '',
            width=m.group(3) or '',
            precision=m.group(4) or '',
            conversion=conv,
        ))
    return specs


def conv_family(c: str) -> str:
    cl = c.lower()
    if cl in ('s', 'b', 'h'):
        return 'general'  # 모든 타입 허용
    if cl in ('d', 'o', 'x'):
        return 'integer'
    if cl in ('f', 'e', 'g', 'a'):
        return 'float'
    if cl == 'c':
        return 'char'
    if cl == 't':
        return 'datetime'
    return 'unknown'


def target_accepts_source(target_conv: str, source_conv: str) -> bool:
    """target_conv가 source_conv가 가리키는 인자 타입을 받아들일 수 있는가."""
    tf = conv_family(target_conv)
    sf = conv_family(source_conv)
    if tf == 'general':
        return True
    return tf == sf


@dataclass
class Diagnostic:
    file: str
    class_key: str | None  # nested 구조에서만 사용
    source: str
    target: str
    status: str  # FINE | FIXABLE | UNFIXABLE | COUNT_MISMATCH | EXPLICIT_INDEX
    reason: str = ''
    fixed_target: str | None = None
    mapping: list[int] = field(default_factory=list)


def derive_mapping(src_specs: list[Spec], tgt_specs: list[Spec]) -> list[int] | None:
    """target 각 spec이 1-based 어떤 source spec의 인자를 소비해야 하는지 계산.
    실패 시 None.
    """
    if any(s.arg_index is not None for s in src_specs + tgt_specs):
        return None  # 이미 위치 지정자 사용 중 — 수동 검토
    if len(src_specs) != len(tgt_specs):
        return None

    n = len(src_specs)
    used = [False] * n
    mapping: list[int] = []

    for t in tgt_specs:
        chosen = -1
        # 1순위: 동일 family 매칭 (예: target=%d ↔ source=%d)
        for i, s in enumerate(src_specs):
            if used[i]:
                continue
            if conv_family(t.conversion) == conv_family(s.conversion):
                chosen = i
                break
        # 2순위: target이 general(%s/%b/%h)이면 어떤 source든 허용
        if chosen < 0 and conv_family(t.conversion) == 'general':
            for i, s in enumerate(src_specs):
                if used[i]:
                    continue
                chosen = i
                break
        if chosen < 0:
            return None
        used[chosen] = True
        mapping.append(chosen + 1)

    return mapping


def is_identity(mapping: list[int]) -> bool:
    return mapping == list(range(1, len(mapping) + 1))


def rewrite_target(target: str, tgt_specs: list[Spec], mapping: list[int]) -> str:
    """target의 각 spec을 mapping에 따라 %N$... 형식으로 재작성."""
    out: list[str] = []
    last = 0
    for spec, idx in zip(tgt_specs, mapping):
        out.append(target[last:spec.start])
        out.append(f"%{idx}${spec.flags}{spec.width}{spec.precision}{spec.conversion}")
        last = spec.end
    out.append(target[last:])
    return ''.join(out)


def diagnose_pair(source: str, target: str, file: str, class_key: str | None) -> Diagnostic | None:
    src_specs = extract_specs(source)
    if not src_specs:
        return None  # 원문에 지정자 없으면 검사 의미 없음

    tgt_specs = extract_specs(target)

    if any(s.arg_index is not None for s in src_specs + tgt_specs):
        return Diagnostic(
            file=file, class_key=class_key, source=source, target=target,
            status='EXPLICIT_INDEX',
            reason='원문 또는 번역에 이미 %N$ 위치 지정자 사용 — 수동 검토 권장.'
        )

    if len(src_specs) != len(tgt_specs):
        return Diagnostic(
            file=file, class_key=class_key, source=source, target=target,
            status='COUNT_MISMATCH',
            reason=f'지정자 개수 불일치: source={len(src_specs)}, target={len(tgt_specs)}'
        )

    # 순차 매핑이 안전한지 확인
    sequential_ok = all(
        target_accepts_source(t.conversion, s.conversion)
        for s, t in zip(src_specs, tgt_specs)
    )
    if sequential_ok:
        return Diagnostic(
            file=file, class_key=class_key, source=source, target=target,
            status='FINE'
        )

    # 재배치 매핑 시도
    mapping = derive_mapping(src_specs, tgt_specs)
    if mapping is None or is_identity(mapping):
        return Diagnostic(
            file=file, class_key=class_key, source=source, target=target,
            status='UNFIXABLE',
            reason='타입이 맞지 않으며 자동 매핑 도출 실패.'
        )

    fixed = rewrite_target(target, tgt_specs, mapping)
    return Diagnostic(
        file=file, class_key=class_key, source=source, target=target,
        status='FIXABLE',
        reason=f'순차 매칭 시 타입 불일치, 위치 지정자 도출: {mapping}',
        fixed_target=fixed,
        mapping=mapping,
    )


def iter_flat_pairs(path: Path) -> Iterable[tuple[str, str, str | None]]:
    if not path.exists():
        return
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return
    for k, v in data.items():
        if not isinstance(k, str) or not isinstance(v, str):
            continue
        yield k, v, None


def iter_nested_pairs(path: Path) -> Iterable[tuple[str, str, str | None]]:
    if not path.exists():
        return
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return
    for class_key, pairs in data.items():
        if class_key.startswith('_'):
            continue
        if not isinstance(pairs, dict):
            continue
        for k, v in pairs.items():
            if not isinstance(k, str) or not isinstance(v, str):
                continue
            yield k, v, class_key


def scan() -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    for path in FLAT_TRANS_FILES:
        rel = str(path.relative_to(ROOT))
        for k, v, _ in iter_flat_pairs(path):
            d = diagnose_pair(k, v, rel, None)
            if d is not None and d.status != 'FINE':
                diags.append(d)
    for path in NESTED_TRANS_FILES:
        rel = str(path.relative_to(ROOT))
        for k, v, ck in iter_nested_pairs(path):
            d = diagnose_pair(k, v, rel, ck)
            if d is not None and d.status != 'FINE':
                diags.append(d)
    return diags


def apply_fixes(diags: list[Diagnostic]) -> int:
    """FIXABLE 항목을 실제 파일에 적용. 적용된 건 수 반환."""
    by_file: dict[str, list[Diagnostic]] = {}
    for d in diags:
        if d.status != 'FIXABLE':
            continue
        by_file.setdefault(d.file, []).append(d)

    applied = 0
    for rel, items in by_file.items():
        path = ROOT / rel
        with open(path, encoding='utf-8') as f:
            data = json.load(f)

        if rel.endswith('class_trans.json'):
            # nested
            for d in items:
                ck = d.class_key
                assert ck is not None
                if data.get(ck, {}).get(d.source) == d.target:
                    data[ck][d.source] = d.fixed_target
                    applied += 1
        else:
            for d in items:
                if data.get(d.source) == d.target:
                    data[d.source] = d.fixed_target
                    applied += 1

        # 들여쓰기 2, 한글 보존
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write('\n')

    return applied


def short(s: str, n: int = 80) -> str:
    s = s.replace('\n', '\\n')
    return s if len(s) <= n else s[:n - 3] + '...'


def print_report(diags: list[Diagnostic]) -> None:
    by_status: dict[str, list[Diagnostic]] = {}
    for d in diags:
        by_status.setdefault(d.status, []).append(d)

    print(f'== 포맷 지정자 검사 결과 ==')
    print(f'총 이슈: {len(diags)}건')
    for status in ('FIXABLE', 'UNFIXABLE', 'COUNT_MISMATCH', 'EXPLICIT_INDEX'):
        items = by_status.get(status, [])
        print(f'  {status}: {len(items)}건')

    for status in ('FIXABLE', 'UNFIXABLE', 'COUNT_MISMATCH', 'EXPLICIT_INDEX'):
        items = by_status.get(status, [])
        if not items:
            continue
        print(f'\n--- {status} ---')
        for d in items:
            loc = f'{d.file}'
            if d.class_key:
                loc += f' :: {d.class_key}'
            print(f'[{loc}]')
            print(f'  source : {short(d.source)}')
            print(f'  target : {short(d.target)}')
            if d.fixed_target is not None:
                print(f'  fixed  : {short(d.fixed_target)}')
            if d.reason:
                print(f'  reason : {d.reason}')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--fix', action='store_true', help='FIXABLE 항목을 실제 JSON에 적용')
    ap.add_argument('--json', action='store_true', help='결과를 JSON으로 stdout에 출력')
    args = ap.parse_args()

    diags = scan()

    if args.json:
        out = [
            {
                'file': d.file,
                'class_key': d.class_key,
                'source': d.source,
                'target': d.target,
                'status': d.status,
                'reason': d.reason,
                'fixed_target': d.fixed_target,
                'mapping': d.mapping,
            }
            for d in diags
        ]
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print_report(diags)

    if args.fix:
        applied = apply_fixes(diags)
        print(f'\n자동 수정 적용: {applied}건')

    return 0


if __name__ == '__main__':
    sys.exit(main())
