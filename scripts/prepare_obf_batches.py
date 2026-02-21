#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""obf_jar UI 후보를 번역 배치로 분할"""

from pathlib import Path
import json, os, re

SCRIPT_DIR = Path(__file__).parent.parent

def _resolve(p):
    if isinstance(p, str) and (p.startswith('./') or p.startswith('../') or p == '.'):
        return str((SCRIPT_DIR / p).resolve())
    return p

with open(SCRIPT_DIR / 'config.json', encoding='utf-8') as _f:
    _cfg = json.load(_f)
_p = _cfg['paths']

INTERMEDIATE = str(SCRIPT_DIR / 'intermediate')
BATCH_SIZE   = 100

CANDIDATES = os.path.join(INTERMEDIATE, 'ui_candidates.json')
OUT_DIR    = INTERMEDIATE

with open(CANDIDATES, encoding="utf-8") as f:
    candidates = json.load(f)

def ui_score(s):
    score = 0
    if " " in s: score += 3
    if s and s[0].isupper(): score += 2
    if any(c in s for c in ".,!?:;"): score += 1
    if "%s" in s or "%d" in s: score += 2
    if len(s) > 400: score -= 2
    return score

# 진짜 번역 대상 필터링
translatable = {}
for s, src in candidates.items():
    if " " not in s:
        continue
    if re.search(r"\.\w+\$\w+", s):
        continue
    if re.search(r"\.(class|void|super|null|new|int|for|while|do|return|if|this|public|private|static)\b", s):
        continue
    translatable[s] = src

print(f"최종 번역 대상: {len(translatable)}개")

items = sorted(translatable.items(), key=lambda x: -ui_score(x[0]))
batches = [items[i:i+BATCH_SIZE] for i in range(0, len(items), BATCH_SIZE)]
print(f"배치 수: {len(batches)}개 (각 {BATCH_SIZE}개)")

os.makedirs(OUT_DIR, exist_ok=True)
for i, batch in enumerate(batches, 1):
    batch_data = {s: src for s, src in batch}
    fname = os.path.join(OUT_DIR, f"batch_{i:02d}.json")
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(batch_data, f, ensure_ascii=False, indent=2)

print("배치 파일 저장 완료")
print()
print("=== 번역 대상 상위 30개 ===")
for s, src in items[:30]:
    short_src = src.split("/")[-1].replace(".class", "")
    print(f"  [{ui_score(s)}] {repr(s)[:80]}  ({short_src})")
