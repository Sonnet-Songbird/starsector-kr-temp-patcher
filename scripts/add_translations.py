#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""add_translations.py - 새 번역 항목을 patches/common.json에 추가"""

from pathlib import Path
import json, os

SCRIPT_DIR = Path(__file__).parent.parent

def _resolve(p):
    if isinstance(p, str) and (p.startswith('./') or p.startswith('../') or p == '.'):
        return str((SCRIPT_DIR / p).resolve())
    return p

with open(SCRIPT_DIR / 'config.json', encoding='utf-8') as _f:
    _cfg = json.load(_f)
_p = _cfg['paths']

TRANSLATIONS = _resolve(_p['translations'])

new_translations = {
    # === 함대 교전 다이얼로그 ===
    "Move in to engage": "교전 진입",
    "Join the disengage attempt": "이탈 시도 합류",
    "Join the engagement": "교전 합류",
    "Join the pursuit": "추격 합류",
    "Perform a salvage operation, then leave": "구난 작업 후 이탈",
    "Pursue them": "추격",
    "Maneuver to force a pitched battle": "정면 결전 강요",
    "Outmaneuver the opposing fleet, forcing them to fight you head on.": "상대 함대를 기동으로 압박해 정면 결전을 강요합니다.",
    "Perform limited emergency repairs": "제한적 긴급 수리 수행",
    "Emergency repairs": "긴급 수리",
    "Your forces": "아군 전력",
    "Your forces were": "아군 전력은",
    "Allied forces": "동맹 전력",
    "Cut the comm link": "통신 차단",
    "Order your second-in-command to handle it": "부지휘관에게 처리 지시",
    "Transfer command for this engagement": "이번 교전 지휘권 이양",
    "Take command of the action": "전투 지휘권 인수",
    "Crash-mothball some of your ships to prevent malfunctions": "오작동 방지를 위해 일부 함선 긴급 격납",
    "Continue into battle": "전투 계속",
    "Go back": "돌아가기",
    "Accept the comm request": "통신 요청 수락",
    "Open a comm link": "통신 개설",
    ": supporting your forces.": ": 아군 지원 중.",
    ": supporting the enemy.": ": 적군 지원 중.",
    ": supporting the opposing side.": ": 상대편 지원 중.",
    ": joining the enemy.": ": 적군 합류 중.",
    "You try to establish a comm link, but only get static.": "통신을 시도했지만 잡음만 들립니다.",
    "Never mind": "신경 쓰지 마",
    "Pick through the wreckage": "잔해 수색",
    # === 함대 상태 패널 ===
    "Held in reserve": "예비 대기",
    "Deployed in last engagement": "최근 전투 출격",
    "Retreated from last engagement": "최근 전투 후퇴",
    "Disabled or destroyed": "불능화 또는 격파",
    "Completely destroyed": "완전 격파",
    # === 다시 표시 안 함 ===
    "Don't show this again": "다시 표시 안 함",
    # === 출격 화면 ===
    "No ships deployed": "출격 함선 없음",
    "No allied ships deployed": "아군 출격 함선 없음",
    "Deploy opposing ships for simulation": "시뮬레이션용 적군 함선 배치",
    "Show advanced options >>>": "고급 옵션 보기 >>>",
    "Combat time: ": "전투 시간: ",
    " seconds": "초",
    "Projected deployment recovery cost: ": "예상 출격 회복 비용: ",
    " supplies": " 보급품",
    "Select ships from other categories to add them here": "다른 카테고리에서 함선을 선택해 여기에 추가하세요",
    "Destroy ships in battle to unlock them for simulation": "전투에서 함선을 격파하면 시뮬레이션에서 잠금 해제됩니다",
    # === 배치 점수 툴팁 ===
    "Deployment Points": "배치 점수",
    "Required to deploy ships. The side more able of engaging on its terms gets more points. This is determined at the start of the engagement by the presence of capable officers in command of combat-ready ships. The number and size of the ships involved is also a small contributing factor.": "함선 출격에 필요합니다. 교전에서 주도권을 더 잘 잡는 편이 더 많은 점수를 얻습니다. 이는 교전 시작 시 전투 준비된 함선을 지휘하는 유능한 장교의 존재에 의해 결정됩니다. 관련 함선의 수와 크기도 소폭 기여합니다.",
    "capable officers in command of combat-ready ships": "전투 준비된 함선을 지휘하는 유능한 장교",
    "The base battle size is %s points. It is increased by %s points due to the presence of an orbital station. The base battle size can be adjusted in gameplay settings. The larger side gets at most %s of the battle size in deployment points, which for the current battle size is up to %s points.": "기본 전투 규모는 %s점입니다. 궤도 기지가 있어 %s점 증가했습니다. 기본 전투 규모는 게임플레이 설정에서 조정할 수 있습니다. 큰 편은 전투 규모의 최대 %s에 해당하는 배치 점수를 받으며, 현재 전투 규모 기준 최대 %s점입니다.",
    "The maximum battle size is %s points. It can be adjusted in gameplay settings. The larger side gets at most %s of the battle size in deployment points, which for the current battle size is up to %s points.": "최대 전투 규모는 %s점입니다. 게임플레이 설정에서 조정할 수 있습니다. 큰 편은 전투 규모의 최대 %s에 해당하는 배치 점수를 받으며, 현재 전투 규모 기준 최대 %s점입니다.",
    "This is a simulation battle, and each side can deploy up to the maximum of %s points.": "이것은 시뮬레이션 전투이며, 각 편은 최대 %s점까지 배치할 수 있습니다.",
    "%s, and certain skills, will increase the available deployment points, but only up to %s of the battle size. You currently have %s bonus deployment points from skills and objectives.": "%s와(과) 일부 스킬로 사용 가능한 배치 점수가 증가하지만, 전투 규모의 최대 %s까지만 적용됩니다. 현재 스킬과 목표물에서 %s 보너스 배치 점수를 얻고 있습니다.",
    "Controlling battlefield objectives": "전장 목표 제어",
    "%s will increase the available deployment points, but only up to %s of the battle size. You currently have the maximum possible deployment points.": "%s로 사용 가능한 배치 점수가 증가하지만, 전투 규모의 최대 %s까지만 적용됩니다. 현재 최대 배치 점수를 보유하고 있습니다.",
    "Your forces can currently deploy ships worth up to %s points total, which is %s of battle size. The enemy can deploy up to %s points, which is %s.": "현재 아군 전력은 총 %s점 가치의 함선을 배치할 수 있으며, 이는 전투 규모의 %s입니다. 적군은 최대 %s점, 즉 %s를 배치할 수 있습니다.",
    "You can always deploy at least one ship, regardless of its point cost.": "점수에 관계없이 항상 최소 한 척의 함선은 배치할 수 있습니다.",
    # === 함선 툴팁 ===
    "Deployment points": "배치 점수",
    "Ready for deployment": "배치 가능",
    "Mothballed, can not be deployed": "격납됨, 배치 불가",
    "Not combat-ready, can not be deployed": "전투 준비 안 됨, 배치 불가",
    "Risks hull damage and critical malfunctions": "선체 손상 및 치명적 결함 위험",
    "Risks malfunctions during deployment": "배치 중 결함 위험",
    "Special modifications: ": "특수 개조: ",
    "Requires a ": "필요: ",
    " point to recover, grants ": "점 회복, 부여 ",
    "% bonus XP": "% 보너스 경험치",
    "Replacement chassis": "교체 차체",
    "CR per fighter deployed": "전투기 출격당 CR",
    "CR per deployment": "배치당 CR",
    "Peak performance (sec)": "최고 성능 (초)",
    "Deployment recovery cost (supplies)": "배치 회복 비용 (보급품)",
    "Hull integrity": "선체 완전성",
    # === 코덱스 링크 ===
    "Press %s for more info": "%s를 눌러 상세 정보 확인",
    "Press %s to open Codex": "%s를 눌러 코덱스 열기",
    "  %s open Codex": "  %s 코덱스 열기",
    "Open the Codex": "코덱스 열기",
    # === 전투 HUD ===
    "No ships currently deployed": "현재 출격 함선 없음",
    "Flagship not currently deployed": "기함 현재 미출격",
    "HOLDING FIRE": "사격 중지",
    "STRAFE LOCK": "이동 고정",
    "Press %s to retreat": "%s를 눌러 후퇴",
    "Shuttle ready for command transfer": "지휘 이양 셔틀 준비 완료",
    "Press %s to open map and select new flagship": "%s를 눌러 지도 열고 새 기함 선택",
    "Press %s to transfer command to selected ship": "%s를 눌러 선택 함선으로 지휘 이양",
    "Press %s to select which ships to deploy": "%s를 눌러 출격할 함선 선택",
    "--- Or ---": "--- 또는 ---",
    # === 전투 상태 표시 ===
    "peak performance steady": "최고 성능 안정",
    " enemy presence": " 적군 감지",
    "Zero Flux Engine Boost": "제로 플럭스 엔진 부스트",
    "Venting Flux": "플럭스 방출 중",
    "Engine Damage": "엔진 손상",
    "% engine capability": "% 엔진 성능",
    " seconds remaining": "초 남음",
    " top speed": " 최고 속도",
    "+0 top speed": "+0 최고 속도",
    "top speed at ": "최고 속도 ",
    "Inside Nebula": "성운 내부",
    # === 전면 돌격 / 후퇴 ===
    "Full Assault!": "전면 돌격!",
    "Full Assault!   (on)": "전면 돌격!   (활성화)",
    "Full Retreat!": "전면 후퇴!",
    "Order a full retreat?": "전면 후퇴 명령?",
    'All ships not already retreating will be issued a "Retreat" order. You will not be able to deploy reinforcements or give any more orders.': '아직 후퇴하지 않은 모든 함선에 "후퇴" 명령이 내려집니다. 이후 증원 배치나 추가 명령을 내릴 수 없게 됩니다.',
    "Ordering a full assault will cancel all existing assignments and make your ships engage the enemy forces more aggressively, potentially exposing them to greater danger.": "전면 돌격 명령은 기존의 모든 임무를 취소하고 아군 함선이 더 공격적으로 교전하게 합니다. 더 큰 위험에 노출될 수 있습니다.",
    "Ordering a full assault will cancel all assignments and also make your ships engage very aggressively. Cancelling a full assault requires a command point.": "전면 돌격 명령은 모든 임무를 취소하고 함선이 매우 공격적으로 교전하게 합니다. 전면 돌격 취소 시 지휘 점수가 필요합니다.",
    "Your fleet is in a full retreat! No further orders will be carried out.": "함대가 전면 후퇴 중입니다! 더 이상의 명령은 수행되지 않습니다.",
    # === 일시정지 ===
    "Paused. Press ": "일시정지. ",
    " again to unpause.": "를 다시 눌러 해제.",
    " to unpause.": "를 눌러 해제.",
    # === 설계 유형 ===
    "Design type: ": "설계 유형: ",
    "Design type": "설계 유형",
    "High Tech": "하이테크",
    "Midline": "미드라인",
    "Low Tech": "로우테크",
    "Remnant": "잔재",
    # === 튜토리얼 ===
    "Rogue Miner": "불량 채굴자",
    "Rogue Miner Force": "불량 채굴 부대",
    # === 기타 UI ===
    "You decide to...": "당신은 결정합니다...",
    "Reinforcements": "증원",
}

with open(TRANSLATIONS, encoding="utf-8") as f:
    tr = json.load(f)

before = len(tr)
added = 0
skipped = 0
for k, v in new_translations.items():
    if k not in tr:
        tr[k] = v
        added += 1
    else:
        skipped += 1

print(f"추가: {added}개, 이미 있음: {skipped}개")
print(f"총 번역: {before} → {len(tr)}개")

with open(TRANSLATIONS, "w", encoding="utf-8") as f:
    json.dump(tr, f, ensure_ascii=False, indent=2)
print("저장 완료")
