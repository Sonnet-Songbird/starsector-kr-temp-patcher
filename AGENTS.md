# 유지보수 참고

번역 규칙·파일 위치·함정 등 유지보수에 필요한 정보를 빠르게 참조하기 위한 문서.

---

## 파일 위치

| 파일 | 경로 | 비고 |
|------|------|------|
| **번역 사전 (공통)** | `kr_work/patches/common.json` | 주 사전 (커밋 대상) |
| **번역 사전 (api 전용)** | `kr_work/patches/api_jar.json` | api JAR 전용 (커밋 대상) |
| **번역 사전 (obf 전용)** | `kr_work/patches/obf_jar.json` | obf JAR 전용 (커밋 대상) |
| **전역 패치 제외 목록** | `kr_work/patches/exclusions.json` | blocked_classes + blocked_strings (커밋 대상) |
| **상수 풀 패칭 라이브러리** | `kr_work/scripts/patch_utils.py` | 05/06/patch_mod_jar 공통 import |
| **모드 JAR 패처** | `kr_work/scripts/patch_mod_jar.py` | post_build 훅으로 자동 호출 |
| api JAR 원본 클래스 | `kr_work/api_classes/` | 게임 업데이트 비교용 (패칭에는 .bak 직접 사용) |
| api 디컴파일 소스 | `kr_work/api_src/` | 16MB, 분석 스크립트 입력 |
| **starsectorkorean 모드 오버레이** | `kr_work/patches/starsectorkorean/` | 커밋 대상 (translations.json, data/, graphics/) |
| **Nexerelin 모드 오버레이** | `kr_work/patches/Nexerelin/` | 커밋 대상 (translations.json, exclusions.json) |
| **모드 전용 제외 목록** | `kr_work/patches/{mod_id}/exclusions.json` | 모드별 blocked_classes + blocked_strings |
| 패치된 api JAR | `kr_work/output/starsector-core/starfarer.api.jar` | 7.0MB, 빌드 산출물 |
| 패치된 obf JAR | `kr_work/output/starsector-core/starfarer_obf.jar` | 빌드 산출물 |
| 완전한 모드 폴더 | `kr_work/output/mods/starsectorkorean/` | 빌드 산출물 (릴리즈 ZIP 소스) |
| 영어 원본 백업 | `starsector-core/starfarer.api.jar.bak` | restore 파이프라인 필수 |
| 영어 원본 백업 | `starsector-core/starfarer_obf.jar.bak` | restore 파이프라인 필수 |
| 모드 디렉토리 | `mods/starsectorkorean/` | |
| 파이프라인 설정 | `kr_work/config.json` | 경로·파이프라인 정의 |
| 스크립트 카탈로그 | `kr_work/scripts/SCRIPTS.md` | |

### 모드 패치 구조 (patches/{mod_id}/)

모드 JAR 번역 지원 모드는 `patches/{mod_id}/` 아래 다음 파일을 가질 수 있다:

| 파일 | 필수 | 설명 |
|------|------|------|
| `translations.json` | 선택 | EN→KO 번역 사전. common.json보다 우선 적용. |
| `exclusions.json` | 선택 | 모드 전용 제외 목록. 전역 exclusions.json과 합집합으로 적용. |
| `data/`, `graphics/` | 선택 | 파일 오버레이. build_mods.py가 output/mods/{id}/에 복사. |

**exclusions.json 3단계 제외 원칙 (최소 적용 원칙):**

| 수단 | 범위 | 사용 기준 |
|------|------|---------|
| `blocked_classes` | 클래스 전체 차단 (가장 정밀) | UI 문자열 없는 유틸/설정/직렬화 클래스 전체를 제외. 내부 키 비교(.equals)가 있는 경우. |
| `blocked_jar_strings` | JAR만 차단 (중간) | 동적 키 구성("header_" + id)에 쓰이는 문자열. 데이터 파일 번역은 유지. |
| `blocked_strings` | JAR + 데이터 파일 모두 차단 (최후의 수단) | 다수 클래스에 걸쳐 JSON/CSV 키로 사용되어 클래스 단위 차단이 불가한 경우. |

**실제 적용 사례 (Nexerelin):**
- `XStreamConfig.class` → `blocked_classes`: 110개 XStream alias 보호 (세이브 호환)
- `NexConfig.class` → `blocked_classes`: `factionId.equals("neutral")` 비교 보호
  번역 시 `defaultConfig = null` → `DiplomacyManager NPE` 발생
- `"invasions"` → `blocked_jar_strings`: `addHeader("invasions")` → `"header_침공"` = 존재하지 않는 키
- `"diplomacy"`, `"ceasefire"` 등 81개 → `blocked_strings`: 이벤트/상태 코드 키 오염 방지

자세한 구조 가이드: `patches/exclusions.json.template`

전역 `patches/exclusions.json`은 핵심 게임 JAR(starfarer_obf.jar, starfarer.api.jar) 전용 제외 목록이며 모드 JAR에도 동시에 적용됨. 모드에서만 문제가 되는 항목은 모드 전용 파일에 분리해서 관리.

### intermediate/ 파일

| 파일 | 내용 | 재생성 |
|------|------|--------|
| `consistency_gaps.json` | 일관성 기반 미번역 분석 | `find_consistency_gaps.py` |
| `short_ui_gaps.json` | 짧은 레이블 미번역 분석 | `find_short_ui_gaps.py` |
| `more_untrans.json` | 추가 미번역 후보 | `find_more_ui.py` |
| `targeted_untrans.json` | 타깃 미번역 후보 | `extract_strings.py` |
| `more_labels.json` | 레이블 그룹화 | `find_more_ui.py` |
| `priority_untrans.json` | 우선순위 미번역 | `get_important_strings.py` |
| `json_keys.txt` | 모드 strings.json 키 목록 | `check_missing_strings.py` |

---

## 절대 번역 금지

### DRM 인증 문자열

`starfarer_obf.jar`의 `com/fs/starfarer/campaign/accidents/A.class`에 있는 문자열들은 농담처럼 보이지만 시리얼 번호 저장용 Preferences 키를 파생하는 데 암호학적으로 사용된다.

```
"Nobody will ever pirate starfarer, "
"because starfarer is not pirateable. "
"It is not pirateable because I am so "
"god damned good at writing top secret code "
```

번역 시: 파생 키 변경 → `Preferences.get()` null → 인증 실패 → 게임 실행 불가.

`patches/exclusions.json`의 `blocked_classes`(`accidents/A.class`)에 등록되어 있다. 이 항목을 제거하지 말 것.

### launcher 클래스

- `com/fs/starfarer/launcher/` 패키지 전체
- `com/fs/starfarer/StarfarerLauncher.class`

`patches/exclusions.json`의 `blocked_classes`에 등록되어 있다.

### 게임 내부 ID

단일 소문자 단어, 대문자 상수형 식별자는 번역 금지:
- 난이도 코드: `EASY`, `MEDIUM`, `HARD`, `IMPOSSIBLE`, `VARIABLE`
- `fleet`, `credits`, `colony` 등 단일 단어

번역 전 안전성 확인 (ID로 쓰이는지):
```bash
python scripts/check_dangerous_strings.py
```

코드 내 다음 패턴으로 쓰이는 문자열은 번역하면 안 된다:
- `return "string"` — ID 반환
- `.equals("string")`, `.get("string")` — 비교/조회 키
- `.put("string", ...)` — Map 키

---

## 작업 전 체크리스트

```bash
# Python 버전 확인 (3.9+)
python --version

# .bak 파일 존재 확인
ls ../starsector-core/*.bak

# 현재 적용 상태 확인 (kr_work/ 에서 실행)
python build.py check
```

---

## 작업 패턴

### 번역 추가

```bash
# 1. patches/common.json에 "영어": "한국어" 추가
# 2. 재패치 및 적용
python build.py patch apply
# 3. 검증
python build.py verify
```

### 전체 재현 테스트

```bash
python build.py rebuild
# restore → patch → apply → verify 순서
```

### 모드 파일만 갱신 (JAR 재패치 없이)

```bash
python build.py update_mod
```

### 신규 모드 번역 추가 절차

```bash
# 1. config.json에 모드 항목 추가
{
  "id": "MyMod",
  "enabled": true,
  "mod_jar": "jars/MyMod.jar",    # JAR이 있는 경우
  "post_build": [
    "scripts/update_mod_version.py",
    "scripts/patch_mod_jar.py"     # JAR이 있는 경우
  ]
}

# 2. patches/MyMod/ 디렉토리 생성
mkdir patches/MyMod

# 3. 번역 후보 추출 (1회)
python scripts/extract_mod_strings.py --mod MyMod
# → intermediate/MyMod_candidates.json

# 4. 모드 XStream aliases 확인 후 exclusions.json 작성 (JAR이 있는 경우)
# XStreamConfig 또는 유사 클래스를 blocked_classes에 추가

# 5. 번역 작업: patches/MyMod/translations.json 작성

# 6. 빌드 및 적용
python build.py update_mod
```

### 추가 번역 대상 탐색

```bash
python scripts/find_consistency_gaps.py
python scripts/extract_strings.py
python scripts/find_more_ui.py
```

---

## 파이프라인 구조

파이프라인 정의는 `config.json`에 있다. `build.py`는 실행기일 뿐이며 로직을 포함하지 않는다.

```
patch      → 05_patch_classes.py (인메모리) → 06_patch_obf.py (인메모리)
build_mod  → 게임 mods/ + patches/ 오버레이 → output/mods/ (build_mods.py) → post_build 훅
             post_build 훅 예시:
               update_mod_version.py --mod {id}   (mod_info.json 버전 갱신)
               patch_mod_jar.py --mod {id}         (모드 JAR 상수 풀 패치)
               translate_mission_java.py --mod {id} (Java 임무 파일 번역)
apply      → JAR 복사 → apply_mods.py → game mods/ 동기화
restore    → .bak 파일로 starsector-core JAR 복원
verify     → verify_cr.py
status     → verify_cr.py --status
update_mod → build_mod → apply
check      → verify → status
all        → patch → build_mod → apply → verify
rebuild    → restore → patch → build_mod → apply → verify
```

**patch_mod_jar.py 제외 규칙 적용 순서:**
```
patches/exclusions.json (전역)
  + patches/{mod_id}/exclusions.json (모드 전용, 선택)
  = 합집합 → ExerelinCore.jar 등 모드 JAR에 적용
```

---

## 알려진 함정

### EASY/MEDIUM/HARD는 게임 내부 난이도 코드

`EASY`, `MEDIUM`, `HARD`, `IMPOSSIBLE`, `VARIABLE`은 게임 로직에서 난이도 판별에 직접 사용되는 키값이다. 번역하면 난이도 선택 UI가 동작하지 않는다. `patches/common.json`에 포함하지 말 것.

### rules.csv 항목 오염

rules.csv의 조건/스크립트 텍스트가 `patches/common.json`에 들어가면 패치 시 오염된다. 멀티라인 항목(개행 포함), 숫자로 시작하는 항목은 제외해야 한다.

### Windows bash에서 Python 경로

bash에서 `/d/...` 경로로 Python을 실행하면 파일을 인식 못하는 경우가 있다. `D:/...` Windows 경로를 사용할 것.

### Long/Double 상수 2슬롯

Java .class 상수 풀에서 `Long`(tag 5) / `Double`(tag 6) 타입은 슬롯 2개를 차지한다. 파싱 시 인덱스 카운터를 2 증가시켜야 하며, 이를 빠뜨리면 이후 전체 파싱이 어긋나 클래스 파일이 깨진다.

### Java Modified UTF-8

Java `.class` 파일의 CONSTANT_Utf8은 Python 표준 UTF-8과 다르다 (null을 `0xC0 0x80`으로 인코딩, 보조 평면 문자를 서로게이트 쌍으로 처리). 한국어 BMP 문자(U+AC00–U+D7A3)는 차이가 없으나, 이모지 등 보조 평면 문자가 포함된 문자열이 나타나면 `cesu8` 패키지가 필요하다.

---

## 기여 가이드

이 프로젝트에 기여하는 방법을 유형별로 정리한다.

### A. 번역 추가 / 수정 (가장 일반적)

**핵심 게임 번역 (`patches/common.json`, `patches/api_jar.json`, `patches/obf_jar.json`):**

```bash
# 1. 해당 JSON 파일을 편집하여 "영어": "한국어" 쌍 추가
# 예: patches/common.json
#   "Combat Readiness": "전투 준비도",

# 2. 안전성 확인 (ID로 쓰이는지 검사)
python scripts/check_dangerous_strings.py

# 3. 재패치 및 적용
python build.py patch apply

# 4. 검증
python build.py verify
```

**주의:** 번역을 추가하기 전 반드시 아래를 확인할 것:
- 단일 소문자 단어는 내부 ID일 가능성이 높음 (예: `"fleet"`, `"credits"`)
- `.equals("string")`, `getString("string")` 패턴으로 쓰이는 문자열은 번역 금지
- TRANSLATION_NOTES.md 1절 "절대 번역 금지 항목" 참고

**Nexerelin 등 모드 번역 (`patches/{mod_id}/translations.json`):**

```bash
# 1. 번역 후보 추출 (처음 작업 시)
python scripts/extract_mod_strings.py --mod Nexerelin
# → intermediate/Nexerelin_candidates.json

# 2. patches/Nexerelin/translations.json에 번역 추가

# 3. 모드만 재빌드
python build.py update_mod
```

---

### B. 번역 오류 수정 (잘못된 번역, 깨진 UI)

```bash
# 1. 어느 사전에 해당 번역이 있는지 검색
python -c "
import json, glob
for f in glob.glob('patches/**/*.json', recursive=True):
    try:
        d = json.load(open(f, encoding='utf-8'))
        if isinstance(d, dict) and '찾을 영어 원문' in d:
            print(f, '->', d['찾을 영어 원문'])
    except: pass
"

# 2. 해당 파일의 번역값 수정

# 3. 재빌드 및 검증
python build.py patch apply verify   # 핵심 JAR 번역인 경우
python build.py update_mod           # 모드 번역인 경우
```

---

### C. 새로운 모드 번역 추가

```bash
# 1. 게임 폴더에 모드가 설치되어 있는지 확인
ls /d/Starsector/mods/MyMod/

# 2. config.json에 모드 항목 추가
# {
#   "id": "MyMod",
#   "enabled": true,
#   "mod_jar": "jars/MyMod.jar",      # JAR이 없으면 이 줄 생략
#   "post_build": [
#     "scripts/update_mod_version.py",
#     "scripts/patch_mod_jar.py"       # JAR이 있는 경우만
#   ]
# }

# 3. patches/MyMod/ 디렉토리 생성
mkdir patches/MyMod

# 4. 번역 후보 추출
python scripts/extract_mod_strings.py --mod MyMod
# → intermediate/MyMod_candidates.json 참고하여 번역 작업

# 5. (JAR이 있는 경우) XStream alias 클래스 확인
python -c "
import zipfile, re
with zipfile.ZipFile('D:/Starsector/mods/MyMod/jars/MyMod.jar') as z:
    for name in z.namelist():
        if 'XStream' in name or 'xstream' in name.lower():
            print(name)
"

# 6. patches/MyMod/exclusions.json 작성
# {
#   "blocked_classes": ["path/to/XStreamConfig.class"],
#   "blocked_jar_strings": [],
#   "blocked_strings": []
# }
# 자세한 가이드: patches/exclusions.json.template

# 7. 번역 사전 작성: patches/MyMod/translations.json
# {"English text": "한국어 텍스트", ...}

# 8. 빌드 및 검증
python build.py update_mod
```

---

### D. 번역 안전성 문제 수정 (버그, 게임 기능 오동작)

번역 후 게임 기능이 오동작하는 경우 (UI 표시 이상, 이벤트 오류, 세이브 로드 실패 등):

**1. 원인 파악:**

| 증상 | 원인 가능성 | 대응 |
|------|------------|------|
| 특정 UI 요소 비어있거나 오작동 | JSON/CSV 키가 번역됨 | `blocked_strings`에 추가 |
| 세이브 로드 실패 (`CannotResolveClassException`) | XStream alias 번역됨 | alias 등록 클래스를 `blocked_classes`에 추가 |
| NPE 또는 NullPointerException | 내부 ID 비교 문자열 번역됨 | 해당 클래스를 `blocked_classes`에 추가 |
| 메뉴 항목이 잘못된 키를 표시 | 동적 키 구성 문자열 번역됨 | `blocked_jar_strings`에 추가 |

**2. 최소 적용 원칙에 따라 수단 선택:**

```
1순위: blocked_classes    → 클래스 전체 차단 (가장 정밀)
2순위: blocked_jar_strings → JAR에서만 차단 (데이터 파일 번역 유지)
3순위: blocked_strings    → JAR + 데이터 파일 모두 차단 (최후의 수단)
```

**3. 전역 vs 모드 전용:**
- 핵심 게임 JAR(api/obf)에서 발생 → `patches/exclusions.json` 수정
- 특정 모드 JAR에서만 발생 → `patches/{mod_id}/exclusions.json` 수정

**4. 적용 및 검증:**

```bash
python build.py update_mod   # 모드 문제인 경우
python build.py rebuild      # 핵심 JAR 문제인 경우
python build.py verify
```

---

### E. 게임 업데이트 후 작업

```bash
# 1. 새 버전 JAR 백업
cp starsector-core/starfarer.api.jar starsector-core/starfarer.api.jar.bak
cp starsector-core/starfarer_obf.jar starsector-core/starfarer_obf.jar.bak

# 2. 변경된 문자열 확인
python scripts/compare_jars.py

# 3. 새로 추가된 미번역 후보 탐색
python scripts/find_consistency_gaps.py
python scripts/extract_strings.py

# 4. 번역 추가 후 전체 재빌드
python build.py rebuild
```

---

### F. 번역 품질 지침

- **용어 일관성**: `TRANSLATION_NOTES.md` 4절의 표준 용어 사용
- **원문 유지**: 고유 함선명(Onslaught 등), 세력명(Hegemony 등), 고유명사는 번역하지 않음
- **맥락 확인**: 짧은 단어는 반드시 `api_src/`에서 사용 맥락 확인 후 번역
- **테스트**: 번역 추가 후 반드시 게임 실행하여 실제 표시 확인

---

## 환경

| 항목 | 값 |
|------|----|
| Python | `python` (PATH 또는 config.json에서 지정, 3.9+) |
| JDK 11 jar | `jar` (PATH, JDK 11+) |
| Starsector JRE | `/d/Starsector/jre/bin/java` (Java 17, 디컴파일용) |
| CFR | `tools/cfr.jar` (0.152) |
| OS | Windows 11 Pro, bash (Git Bash) |
