#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
translate_mission_java.py - MissionDefinition.java 파일 번역

게임 코어의 미션 파일들을 output/mods/{mod_id}/data/missions/에 복사하고,
MissionDefinition.java의 브리핑 항목 및 함대 태그라인을 번역한다.

사용법:
    python translate_mission_java.py [--mod <mod_id>]
    기본값: starsectorkorean
"""

import argparse
import json
import os
import shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent


def _resolve(p, base=SCRIPT_DIR):
    if isinstance(p, str) and (p.startswith('./') or p.startswith('../') or p == '.'):
        return str((base / p).resolve())
    return p


with open(SCRIPT_DIR / 'config.json', encoding='utf-8') as _f:
    _paths = json.load(_f)['paths']

CORE = os.path.join(_resolve(_paths['game_core']), 'data', 'missions')
OUTPUT_MODS = _resolve(_paths['output_mods'])

# 번역 매핑: 정확한 문자열 리터럴 기준
translations = {
    # ── afistfulofcredits ──
    "'Just an honest trader trying to make a living, officer.'":
        "'그저 먹고살려는 정직한 상인이에요, 경관님.'",
    "No-good two-timing 'High Rad' Moon Salazar in a rustbucket mule":
        "고물 뮬을 몰고 다니는 이중 계약자 '하이 래드' 문 살라자르",
    "Show 'High Rad' Moon what it means to break a deal":
        "'하이 래드' 문에게 계약을 어기면 어떻게 되는지 보여줘라",
    "Don't lose 'Stranger II' - it's my most valuable possession":
        "'스트레인저 II'를 잃지 마라 - 내게 가장 소중한 것이다",
    "Moon's ship has delicate engine mods; use Salamander Missiles to leave her adrift":
        "문의 함선은 엔진 개조가 섬세하다; 샐러맨더 미사일로 표류시켜라",

    # ── ambush ──
    "Tri-Tachyon phase group Gamma III":
        "트라이-태키온 위상 함대 감마 III",
    "Hegemony special anti-raider patrol force":
        "헤게모니 특수 침입자 대응 순찰대",
    "Use Sabot SRMs to overload tough targets before finishing them off with Reaper torpedos":
        "새벗 단거리 미사일로 강적의 플럭스를 과부하시킨 뒤 리퍼 어뢰로 마무리하라",
    "Remember: Your armor can safely absorb hits from anti-fighter missiles":
        "기억하라: 장갑은 대전투기 미사일의 공격을 안전하게 흡수할 수 있다",

    # ── coralnebula ──
    "Persean League task force led by Navarch Kato":
        "나바크 카토가 이끄는 페르세안 연맹 기동부대",
    "Detachment from the 3rd Holy Armada and Pather irregulars":
        "제3 성전 함대 분견대 및 패더 비정규군",
    "Using your torpedo bombers is key to victory":
        "어뢰 폭격기를 활용하는 것이 승리의 핵심이다",
    "Keep the Astral carrier 'Sirocco' on the field to repair and rearm them":
        "아스트랄 항공모함 '시로코'를 전장에 유지하여 전투기를 수리·재무장하라",

    # ── direstraits ──
    "Hegemony relief fleet with mercenary escort":
        "용병 호위대를 동반한 헤게모니 구원 함대",
    "Tri-Tachyon containment task force":
        "트라이-태키온 봉쇄 기동부대",
    "ISS Black Star must survive":
        "ISS 블랙 스타는 반드시 생존해야 한다",
    "At least 25% of the Hegemony forces must escape":
        "헤게모니 전력의 최소 25%가 탈출해야 한다",

    # ── forlornhope ──
    "The TTS Invincible":
        "TTS 인빈서블",
    "Leading elements of the Hegemony Defense Fleet":
        "헤게모니 방위 함대 선봉",
    "The TTS Invincible must survive":
        "TTS 인빈서블은 반드시 생존해야 한다",

    # ── forthegreaterlud ──
    "ISS Black Star and Luddic Path strike force":
        "ISS 블랙 스타 및 루딕 패스 타격부대",
    "PLS Praxis with escort and Tri-Tachyon allies":
        "PLS 프락시스, 호위 함선 및 트라이-태키온 동맹군",
    "Distract the enemy flagship to allow your bombers to flank it":
        "폭격기가 적 기함을 측면에서 공격할 수 있도록 적의 주의를 분산하라",

    # ── hornetsnest ──
    "ISS Van Rijn and salvage fleet":
        "ISS 반 레인 및 구조 함대",
    "Kanta pirate coalition forces":
        "칸타 해적 연합군",
    "You have very limited Command Points":
        "명령 포인트가 매우 제한적이다",
    "Concentrate your superior forces to defeat the enemy in detail":
        "우세한 전력을 집중하여 적을 각개격파하라",

    # ── nothingpersonal ──
    "ISS Athena at the head of a survey fleet":
        "탐사 함대를 이끄는 ISS 아테나",
    "HSS Phoenix and Hegemony facility guard detachments":
        "HSS 피닉스 및 헤게모니 시설 경비 분견대",
    "Defeat the enemy forces":
        "적 함대를 격파하라",
    "ISS Enki must survive - it carries irreplacable scientific equipment":
        "ISS 엔키는 반드시 생존해야 한다 - 대체 불가한 과학 장비를 탑재하고 있다",
    "Destroy the enemy escort ships first, then strike at the heart of their fleet.":
        "먼저 적 호위 함선을 격파한 뒤, 적 함대의 핵심을 공격하라.",

    # ── predatororprey ──
    "Hegemony patrol":
        "헤게모니 순찰대",
    "Tri-Tachyon carrier detachment":
        "트라이-태키온 항공모함 분견대",
    "Retreating enemy fighters will lead you to their carrier":
        "후퇴하는 적 전투기를 따라가면 항공모함으로 이어진다",
    "Time your advance against the rhythm of enemy torpedo attacks":
        "적의 어뢰 공격 리듬에 맞춰 전진 타이밍을 조절하라",

    # ── randombattle1 ──
    "Your forces":
        "아군 함대",
    "Enemy forces":
        "적군 함대",

    # ── sinkingthebismarck ──
    "Tri-Tachyon recon detachment and supply craft":
        "트라이-태키온 정찰 분견대 및 보급함",
    "HSS Bismar":
        "HSS 비스마르",
    "Destroy the HSS Bismar":
        "HSS 비스마르를 격파하라",
    "The TTS Chimera is a valuable prototype and must survive":
        "TTS 키마이라는 귀중한 시제품으로 반드시 생존해야 한다",

    # ── thelasthurrah ──
    "Mayasurian navy with heavy fighter complement":
        "중전투기 편대를 갖춘 마야수리아 해군",
    "Hegemony fleet under Commodore Jensulte":
        "준장 젠술테 휘하 헤게모니 함대",
    "MSS Garuda must survive":
        "MSS 가루다는 반드시 생존해야 한다",
    "Maintain tactical awareness and use superior mobility to choose your battles.":
        "전술적 상황 판단을 유지하고 기동력의 우위를 활용하여 유리한 전투를 선택하라.",
    "Remember: If you engage the enemy flagship in a fair fight, you will lose.":
        "기억하라: 적 기함과 정면 대결을 벌이면 패배한다.",

    # ── thewolfpack ──
    "Mercenary raiders":
        "용병 약탈대",
    "Hegemony convoy with escort":
        "호위대를 동반한 헤게모니 수송대",
    "The Hegemony convoy will attempt to flee towards the top of the map":
        "헤게모니 수송대는 지도 상단으로 도주를 시도할 것이다",
    "Controlling the Nav Buoys is critical to preventing a quick escape":
        "항법 부표 제어는 빠른 탈출을 막는 데 필수적이다",
    "Ordering a fleetwide search & destroy will make your ships more aggressive":
        "함대 전체에 수색격멸 명령을 내리면 아군 함선이 더 공격적으로 행동한다",
    "Ordering your ships to eliminate a target will make them more aggressive":
        "함선에 특정 목표 제거 명령을 내리면 더 공격적으로 행동한다",

    # ── turningthetables ──
    "ISS Hamatsu and ISS Black Star with drone escort":
        "드론 호위대를 동반한 ISS 하마츠 및 ISS 블랙 스타",
    "Luddic Path forces":
        "루딕 패스 세력",
    "ISS Black Star & ISS Hamatsu must survive":
        "ISS 블랙 스타 & ISS 하마츠는 반드시 생존해야 한다",
    "Stay with the ISS Hamatsu (friendly cruiser) for safety":
        "안전을 위해 ISS 하마츠(아군 순양함) 곁에 있어라",

    # ── 공통 ──
    "Defeat all enemy forces":
        "모든 적 함대를 격파하라",
}

missions = [
    'afistfulofcredits', 'ambush', 'coralnebula', 'direstraits',
    'forlornhope', 'forthegreaterlud', 'hornetsnest', 'm2', 'm3',
    'nothingpersonal', 'predatororprey', 'randombattle1', 'sinkingthebismarck',
    'thelasthurrah', 'thewolfpack', 'turningthetables',
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mod', default='starsectorkorean', help='모드 ID')
    args = parser.parse_args()
    mod_id = args.mod

    mod_dir = os.path.join(OUTPUT_MODS, mod_id, 'data', 'missions')

    processed = 0
    skipped = 0
    for mission in missions:
        src_dir = os.path.join(CORE, mission)
        dst_dir = os.path.join(mod_dir, mission)

        if not os.path.isdir(src_dir):
            print(f'SKIP (no src): {mission}')
            skipped += 1
            continue

        # 미션 디렉토리 복사: 이미 오버레이된 파일(descriptor.json, mission_text.txt 등)은 덮어쓰지 않음
        os.makedirs(dst_dir, exist_ok=True)
        for fname in os.listdir(src_dir):
            src_file = os.path.join(src_dir, fname)
            dst_file = os.path.join(dst_dir, fname)
            if os.path.isfile(src_file) and not os.path.exists(dst_file):
                shutil.copy2(src_file, dst_file)

        # MissionDefinition.java 번역 적용
        java_dst = os.path.join(dst_dir, 'MissionDefinition.java')
        if not os.path.exists(java_dst):
            print(f'SKIP (no java): {mission}')
            skipped += 1
            continue

        with open(java_dst, 'r', encoding='utf-8') as f:
            content = f.read()

        changed = 0
        for eng, kor in translations.items():
            old = f'"{eng}"'
            new = f'"{kor}"'
            if old in content:
                content = content.replace(old, new)
                changed += 1

        with open(java_dst, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f'OK ({changed:2d} 치환): {mission}')
        processed += 1

    print(f'\n처리 완료: {processed}개 / 건너뜀: {skipped}개')


if __name__ == '__main__':
    main()
