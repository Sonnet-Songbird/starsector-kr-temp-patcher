# 스크립트 카탈로그

스크립트 위치: `kr_work/scripts/`

---

## [CORE] 핵심 파이프라인

`build.py`에서 자동 실행되는 스크립트. 직접 실행 가능하나 `python build.py <pipeline>` 사용 권장.

| 스크립트 | 목적 | 입력 | 출력 | build.py 연동 |
|----------|------|------|------|---------------|
| `patch_utils.py` | Java .class 상수 풀 패칭 공유 라이브러리 | (라이브러리, 직접 실행 없음) | — | patch_api_jar/patch_obf_jar/patch_mod_jar 공통 import |
| `patch_api_jar.py` | starfarer.api.jar 상수 풀 패치 (인메모리 ZIP) | `starfarer.api.jar.bak` + `patches/common.json` + `patches/api_jar.json` + `patches/exclusions.json` | `output/starsector-core/starfarer.api.jar` | `patch` 파이프라인 1단계 |
| `patch_obf_jar.py` | starfarer_obf.jar 인메모리 패치 | `starfarer_obf.jar.bak` + `patches/common.json` + `patches/obf_jar.json` + `patches/exclusions.json` | `output/starsector-core/starfarer_obf.jar` | `patch` 파이프라인 2단계 |
| `patch_mod_jar.py` | 범용 모드 JAR 상수 풀 패치 (post_build 훅) | `output/mods/{id}/{mod_jar}` + `patches/common.json` + `patches/{id}/translations.json` + `patches/exclusions.json` (전역) + `patches/{id}/exclusions.json` (모드 전용, 선택) | `output/mods/{id}/{mod_jar}` (in-place) | `build_mod` post_build 훅 |
| `build_mods.py` | 게임 원본 모드 + patches/ 오버레이 → output/mods/ 빌드 | `game_mods/<id>/` + `patches/<id>/` + `patches/exclusions.json` | `output/mods/<id>/` | `build_mod` 파이프라인 |
| `apply_mods.py` | output/mods/ → 게임 mods/ 동기화 | `output/mods/<id>/` | `game_mods/<id>/` | `apply` 파이프라인 |
| `translate_mission_java.py` | 16개 임무 MissionDefinition.java 번역 | `starsector-core/data/missions/` (게임 원본) | `output/mods/starsectorkorean/data/missions/` | `build_mod` post_build 훅 |
| `verify_cr.py` | 한글화 적용 4개 spot-check 검증 | `starsector-core/*.jar`, 모드 폴더 | 콘솔 출력 (PASS/FAIL) | `verify` 파이프라인 |

### verify_cr.py 체크 항목
1. api JAR `CRPluginImpl` → `'전투 준비도 '` 포함 여부
2. api JAR `CRPluginImpl` → `'오작동 위험: '` 포함 여부
3. obf JAR 전체 → 한국어 문자열 1개 이상 존재
4. `forlornhope/MissionDefinition.java` → `'인빈서블'` 포함 여부

`--status` 플래그: PASS/FAIL 대신 한/영 상태 요약만 출력.

### patch_mod_jar.py 제외 규칙 우선순위

```
patches/exclusions.json         ← 전역 (DRM, launcher, XStream alias 등)
  ∪
patches/{mod_id}/exclusions.json ← 모드 전용 (XStreamConfig 클래스, 모드 내부 ID 등)
  ↓
ExerelinCore.jar 등 모드 JAR에 합집합으로 적용
```

모드 전용 `exclusions.json` 형식:
```json
{
  "blocked_classes": ["exerelin/plugins/XStreamConfig.class"],
  "blocked_strings": ["SomeModInternalId"]
}
```

---

## [SETUP] 초기 환경 구성 (게임 업데이트 시 재실행)

게임 버전이 변경될 때 새 JAR 클래스를 추출/분석하기 위해 실행.
**실행 순서**: `01` → `02` → `04` → 번역 추가 → `build.py all`

| 스크립트 | 목적 | 입력 | 출력 |
|----------|------|------|------|
| `extract_jars.sh` | 현재 api JAR 압축 해제 (패칭과 무관; 게임 업데이트 전후 compare_jars.py 비교용) | `starsector-core/starfarer.api.jar` | `api_classes/` |
| `decompile.sh` | CFR으로 api JAR 디컴파일 | `starsector-core/starfarer.api.jar` | `api_src/` |
| `find_strings.py` | 미번역 UI 문자열 후보 추출 | `api_src/` + `patches/*.json` (전체 사전) | `intermediate/untranslated.json` |
| `compare_jars.py` | 두 클래스 폴더 MD5 비교 (업데이트 전후 diff) | `<폴더A>` `<폴더B>` (인자) | 변경 클래스 목록 |

### 게임 업데이트 절차
```bash
# 1. 새 .bak 백업 (현재 영어 JAR)
cp starsector-core/starfarer.api.jar starsector-core/starfarer.api.jar.bak
cp starsector-core/starfarer_obf.jar starsector-core/starfarer_obf.jar.bak

# 2. 클래스 및 소스 재추출
bash scripts/extract_jars.sh
bash scripts/decompile.sh

# 3. 변경된 클래스 확인 (옵션)
python scripts/compare_jars.py <이전_api_classes_백업> api_classes

# 4. 미번역 신규 문자열 탐색
python scripts/find_strings.py

# 5. 전체 재패치 적용
python build.py all
```

---

## [ANALYSIS] 분석/탐색 도구

추가 번역 항목 발굴, 품질 확인 등 필요 시 실행.

| 스크립트 | 목적 | 입력 | 사용 시점 |
|----------|------|------|----------|
| `extract_mod_strings.py` | 모드 JAR + 데이터 파일에서 번역 후보 추출 | `game_mods/{id}/` (JAR+data) | 신규 모드 번역 시작 전 1회 실행 |
| `extract_strings.py` | JAR에서 미번역 UI 문자열 추출 | `starsector-core/*.jar` | 추가 번역 항목 탐색 |
| `extract_obf_ui.py` | obf JAR 전용 UI 문자열 정밀 추출 | `starsector-core/starfarer_obf.jar` | obf 번역 확장 시 |
| `prepare_obf_batches.py` | obf 번역 후보를 100개씩 배치 분할 | `extract_obf_ui.py` 출력 | obf 번역 배치 작업 준비 |
| `find_consistency_gaps.py` | 일관성 기반 미번역 항목 탐색 | `patches/*.json` (전체 사전) | 누락 번역 일관성 확인 |
| `find_mixed_categories.py` | 번역/미번역 혼재 카테고리 분석 | `api_src/` | UI 일관성 점검 |
| `find_more_ui.py` | 미번역 레이블 그룹화 탐색 | `api_src/` | 추가 번역 대상 발굴 |
| `find_short_ui_gaps.py` | 짧은 UI 레이블 미번역 탐색 | `api_src/` | 짧은 레이블 보완 |
| `analyze_strings.py` | 미번역 문자열 필터링 (간단 스크립트) | `intermediate/*.json` | 빠른 현황 파악 |
| `get_important_strings.py` | 번역 우선순위 상위 300개 추출 | `api_src/` | 번역 우선순위 결정 |
| `check_missing_strings.py` | strings.json 키 누락 확인 | 모드 strings.json | 모드 strings.json 점검 |
| `check_tooltips.py` | tooltips.json 누락 항목 확인 | 모드 tooltips.json | 모드 tooltips.json 점검 |
| `check_dangerous_strings.py` | 단일 단어 ID 사용 여부 스캔 | `api_src/` | 번역 안전성 사전 확인 |

---

## [UTIL] 번역 데이터 관리

`patches/common.json` (주 사전) 관리, 정제, 병합.

| 스크립트 | 목적 | 주요 동작 |
|----------|------|----------|
| `add_translations.py` | 새 번역 항목 수동 추가 | `patches/common.json` 갱신 |
| `merge_translations.py` | 모드 데이터 번역 + 수동 번역 병합 | `patches/common.json` 갱신 |
| `clean_translations.py` | 위험 단어(ID 가능) 제거 | `patches/common.json` 정제 |
| `safe_translations.py` | 안전 번역만 필터링 출력 | 안전성 검증 |
| `final_clean.py` | rules.csv 스타일 항목, 멀티라인 제거 | 최종 정제 |
| `migrate_translations.py` | **[일회성]** final_translations.json → common/api/obf 분리 마이그레이션 | 3개 사전 파일 생성 |

---

## [MOD] 모드 파일 생성 도구

스킬/스킨 파일을 새로 생성하거나 재생성해야 할 때.

| 스크립트 | 목적 | 산출물 |
|----------|------|--------|
| `gen_skin_overrides.py` | .skin 파일 한국어 이름 오버라이드 생성 | `patches/starsectorkorean/data/hulls/skins/` |
| `gen_skill_files.py` | 스킬 .skill 파일 생성 (CUSTOM scope) | `patches/starsectorkorean/data/characters/skills/` |
| `gen_victor21_ko.py` | victor21 KR 폰트 .fnt/.png 생성 | `patches/starsectorkorean/graphics/fonts/` |
