#!/usr/bin/env python3
"""
07_gen_skin_overrides.py - 스킨 파일 한국어 이름 오버라이드 생성

게임의 data/hulls/skins/*.skin 파일에서 hullName 추출,
모드 ship_data.csv의 한국어 기본 이름과 매핑하여
patches/starsectorkorean/data/hulls/skins/ 에 오버라이드 스킨 파일 생성.

각 생성 파일에는 skinHullId + hullName(한국어) 만 포함.
게임은 나머지 필드를 원본 스킨에서 상속함.
"""

from pathlib import Path
import os, json, re, csv

SCRIPT_DIR = Path(__file__).parent.parent

def _resolve(p):
    if isinstance(p, str) and (p.startswith('./') or p.startswith('../') or p == '.'):
        return str((SCRIPT_DIR / p).resolve())
    return p

with open(SCRIPT_DIR / 'config.json', encoding='utf-8') as _f:
    _cfg = json.load(_f)
_p = _cfg['paths']

GAME_CORE    = _resolve(_p['game_core'])
GAME_MODS    = _resolve(_p['game_mods'])
PATCHES      = _resolve(_p['patches'])
TRANSLATIONS = _resolve(_p['translations'])
OUTPUT_MODS  = _resolve(_p['output_mods'])
INTERMEDIATE = str(SCRIPT_DIR / 'intermediate')

GAME_SKINS_DIR = os.path.join(GAME_CORE, 'data/hulls/skins')
GAME_SHIP_DATA = os.path.join(GAME_CORE, 'data/hulls/ship_data.csv')
MOD_SHIP_DATA  = os.path.join(PATCHES, 'starsectorkorean/data/hulls/ship_data.csv')
OUTPUT_DIR     = os.path.join(PATCHES, 'starsectorkorean/data/hulls/skins')

# 기본 함선 이름이 스킨 이름과 다른 경우 수동 매핑
# skinHullId -> 한국어 이름
MANUAL_OVERRIDES = {
    'executor':  '익스큐터',       # Pegasus 기반이지만 완전히 다른 이름
    'mudskipper2': '머드스키퍼 Mk.II',  # mudskipper 기반
    'venture_p':   '벤쳐 Mk.II',    # venture 기반
}

# ──────────────────────────────────────────────────────────────────────────────
# 함선 이름 매핑 로드 (hull_id → 한국어 이름)
# ──────────────────────────────────────────────────────────────────────────────

def load_hull_names(path):
    """CSV에서 hull_id → name 매핑 로드. col0=name, col1=id"""
    result = {}
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2 and row[1].strip() and not row[0].startswith('#'):
                result[row[1].strip()] = row[0].strip()
    return result


def load_skin_file(path):
    """skin 파일 파싱 (JSON + # 주석 지원)"""
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    content_clean = re.sub(r'#[^\n]*', '', content)
    try:
        return json.loads(content_clean)
    except json.JSONDecodeError:
        # fallback: regex
        result = {}
        for key in ('skinHullId', 'baseHullId', 'hullName'):
            m = re.search(r'"' + key + r'"\s*:\s*"([^"]*)"', content)
            if m:
                result[key] = m.group(1)
        return result


# ──────────────────────────────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────────────────────────────

def main():
    game_names = load_hull_names(GAME_SHIP_DATA)   # hull_id → 영어 이름
    mod_names  = load_hull_names(MOD_SHIP_DATA)    # hull_id → 한국어 이름

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    generated = 0
    skipped   = 0

    for fname in sorted(os.listdir(GAME_SKINS_DIR)):
        if not fname.endswith('.skin'):
            continue

        skin_data = load_skin_file(os.path.join(GAME_SKINS_DIR, fname))
        skin_id   = skin_data.get('skinHullId', fname.replace('.skin', ''))
        base_id   = skin_data.get('baseHullId', '')
        en_name   = skin_data.get('hullName', '')

        if not en_name:
            skipped += 1
            continue

        # 기본 함선 이름의 한국어 번역 찾기
        kr_base = mod_names.get(base_id, '')

        if not kr_base:
            # base_id가 모드에 없으면 영어 기본 이름 사용 (게임 이름으로 fallback)
            kr_base = game_names.get(base_id, '')

        # 수동 오버라이드 우선 적용
        if skin_id in MANUAL_OVERRIDES:
            kr_name = MANUAL_OVERRIDES[skin_id]
        elif kr_base:
            # 영어 이름에서 기본 함선 이름 부분을 한국어로 교체
            # 예: "Wolf (H)" → base_en="Wolf" → kr_base="울프" → "울프 (H)"
            en_base = game_names.get(base_id, '')
            if en_base and en_name.startswith(en_base):
                suffix = en_name[len(en_base):]   # " (H)", " (D)", " Mk.II" 등
                kr_name = kr_base + suffix
            else:
                # 이름이 base와 일치하지 않으면 영어 이름 유지
                kr_name = en_name
                print(f'  [NAME MISMATCH] {skin_id}: base="{en_base}", skin="{en_name}", keeping English')
        else:
            # 번역 없음: 영어 이름 그대로
            kr_name = en_name
            print(f'  [NO BASE TRANS] {skin_id}: base={base_id}, keeping "{en_name}"')

        # 스킨 오버라이드 파일 생성 (최소 필드만)
        content = '{\n\t"skinHullId":"%s",\n\t"hullName":"%s"\n}\n' % (skin_id, kr_name)

        out_path = os.path.join(OUTPUT_DIR, fname)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f'  {fname}: "{en_name}" → "{kr_name}"')
        generated += 1

    print(f'\n생성됨: {generated}개, 건너뜀: {skipped}개')
    print(f'출력: {OUTPUT_DIR}')


if __name__ == '__main__':
    main()
