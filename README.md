# 스타섹터 임시 한글 패치

> 이 리파지터리는 Claude Code (Claude Sonnet 4.6)를 통해 생성되었으며, 코드와 문서 전반이 LLM에 의해 작성되었습니다. 어색한 표현이 있을 수 있습니다.

스타섹터(Starsector)를 위한 **임시 한글 패치**입니다.

Java 클래스 파일의 상수 풀(Constant Pool)을 직접 수정하여 게임 하드코딩 UI 문자열을 한국어로 번역하며, 모드 데이터 파일(CSV/JSON)로는 처리할 수 없는 텍스트까지 번역합니다. 또한 `starsectorkorean` 모드 원본에 추가 번역 데이터를 패치하여 완전한 한글화 모드를 생성하고, Nexerelin 등 주요 모드의 번역도 포함합니다.

> **주의:** 이 프로젝트는 Discord 커뮤니티 비공식 번역 작업의 임시 성과물입니다. 정식 한글화가 완료되면 종료됩니다.
>
> **원본 출처:** [Discord 서버 초대 링크](https://discord.gg/zUKDSSrD4N)

---

## 빠른 시작 (비프로그래머)

1. 오른쪽 **Releases** 탭에서 최신 ZIP 파일을 다운로드합니다.
2. 압축을 풀고, 내용물을 Starsector 설치 폴더에 **그대로 덮어씌웁니다**.
   - `starsector-core/` 폴더 → Starsector 설치 폴더의 `starsector-core/`
   - `mods/starsectorkorean/` 폴더 → Starsector 설치 폴더의 `mods/`
3. 게임 실행 후 **모드 목록에서 `starsectorkorean`을 활성화**합니다.

---

## 전체 빌드 방법 (개발자)

### 전제 조건

| 항목 | 요구사항 |
|------|---------|
| Python | 3.9 이상 (`python` 명령이 PATH에 있어야 함) |
| Starsector | 설치 완료 |
| `starsectorkorean` 모드 | 사전 설치 필요 (`mods/starsectorkorean/` 존재해야 함) |
| `.bak` 파일 | `starsector-core/starfarer.api.jar.bak`, `starfarer_obf.jar.bak` |

> **`.bak` 파일 생성 방법** (최초 1회):
> ```bash
> cp starsector-core/starfarer.api.jar starsector-core/starfarer.api.jar.bak
> cp starsector-core/starfarer_obf.jar starsector-core/starfarer_obf.jar.bak
> ```

### 폴더 구조

이 리포지터리는 Starsector 설치 폴더(`starsector-core/`, `mods/`)의 **형제 디렉토리**에 클론해야 합니다:

```
Starsector/               ← 게임 설치 폴더
├── starsector-core/
│   ├── starfarer.api.jar
│   ├── starfarer.api.jar.bak   ← 반드시 미리 생성
│   ├── starfarer_obf.jar
│   └── starfarer_obf.jar.bak   ← 반드시 미리 생성
├── mods/
│   └── starsectorkorean/       ← 원본 모드 (사전 설치 필요)
└── kr_work/              ← 이 리포지터리 (여기에 클론)
    ├── config.json
    └── ...
```

### 설치 및 빌드

```bash
# 1. 클론
git clone https://github.com/Sonnet-Songbird/starsector-kr-temp-patcher.git kr_work
cd kr_work

# 2. 전체 빌드 (패치 + 테스트 + 적용 + 검증)
python build.py all
```

### 주요 명령

| 상황 | 명령 |
|------|------|
| 전체 재패치 및 적용 | `python build.py all` |
| 모드 파일만 갱신 (JAR 재패치 없이) | `python build.py update_mod` |
| 영어 원본 복원 후 전체 재적용 | `python build.py rebuild` |
| 빌드 산출물 테스트만 실행 | `python build.py test` |
| 적용 상태 확인 | `python build.py check` |
| 영어 원본으로 복원 | `python build.py restore` |

---

## 디렉토리 구조

```
kr_work/
├── build.py              — 파이프라인 실행기 (단일 진입점)
├── run_tests.py          — 빌드 산출물 자동 테스트 진입점
├── config.json           — 경로·파이프라인 설정 (상대경로 기본값으로 커밋됨)
├── README.md             — 이 파일
├── AGENTS.md             — 유지보수 참고 (규칙·경로·파이프라인·함정)
├── TRANSLATION_NOTES.md  — 번역 주의사항 및 기술 특징
├── CONTRIBUTING.md       — 기여 방법 안내
│
├── scripts/              — 스크립트 (scripts/SCRIPTS.md 참고)
│   ├── patch_utils.py       — Java .class 상수 풀 패칭 공유 라이브러리
│   ├── patch_api_jar.py     — api JAR 인메모리 패치
│   ├── patch_obf_jar.py     — obf JAR 인메모리 패치
│   ├── patch_mod_jar.py     — 범용 모드 JAR 상수 풀 패처 (post_build 훅)
│   ├── build_mods.py        — 모드 빌드 (원본 + 패치 오버레이)
│   ├── apply_mods.py        — 모드 적용 (게임 폴더로 복사)
│   ├── verify_cr.py         — 한글화 적용 spot-check 검증
│   └── ...                  — 분석/탐색 도구 (SCRIPTS.md 참고)
│
├── tests/                — 자동 테스트 (unittest, 추가 설치 불필요)
│   ├── base_test.py         — 공통 BaseTestCase
│   ├── helpers.py           — JAR 파싱 헬퍼
│   ├── test_output.py       — 빌드 산출물 존재·ZIP 무결성
│   ├── test_jars.py         — JAR 번역 확인·DRM 안전·blocked_class 검증
│   └── test_mods.py         — 모드 파일 유효성·번역 샘플 확인
│
├── patches/              ★ 커밋 대상 (번역 사전 + 모드 패치 파일)
│   ├── common.json           — 주 사전 (JAR 공통 번역)
│   ├── api_jar.json          — api JAR 전용 번역 (스킬 fragment 등)
│   ├── obf_jar.json          — obf JAR 전용 번역
│   ├── exclusions.json       — 전역 제외 목록 (DRM·launcher·XStream alias)
│   ├── exclusions.json.template — 제외 수단 선택 가이드
│   ├── starsectorkorean/     — starsectorkorean 모드 오버레이
│   │   └── data/
│   │       ├── strings/      — strings.json, tooltips.json
│   │       ├── characters/skills/  — 59개 스킬 파일
│   │       ├── hulls/        — ship_data.csv, skins/
│   │       ├── campaign/     — rules.csv, descriptions.csv
│   │       └── missions/     — 16개 임무 descriptor.json, mission_text.txt
│   └── Nexerelin/            — Nexerelin 모드 오버레이
│       ├── translations.json — Nexerelin 전용 번역 사전 (4,233개)
│       └── exclusions.json   — Nexerelin 전용 제외 목록
│
├── intermediate/         — 분석 캐시 (.gitignore, 재생성 가능)
│
├── api_classes/          — api JAR 클래스 추출본 (게임 업데이트 비교용)
├── api_src/              — api JAR 디컴파일 소스 (분석 스크립트 입력용)
│
├── output/               ★ 빌드 산출물 (.gitignore, 재생성 가능)
│   ├── starsector-core/
│   │   ├── starfarer.api.jar    — 패치된 api JAR
│   │   └── starfarer_obf.jar   — 패치된 obf JAR
│   └── mods/
│       ├── starsectorkorean/   — 완전한 한글화 모드 (Releases ZIP 소스)
│       └── Nexerelin/          — 번역된 Nexerelin 모드
│
└── tools/cfr.jar         — CFR 0.152 디컴파일러 (MIT License, Lee Benfield)
```

### 재생성 가능 항목

| 항목 | 재생성 방법 |
|------|-----------|
| `api_classes/` | `bash scripts/extract_jars.sh` |
| `api_src/` | `bash scripts/decompile.sh` |
| `output/` 전체 | `python build.py all` |
| `intermediate/` 분석 캐시 | 해당 `find_*.py` 스크립트 재실행 |

---

## 번역 현황

| 대상 | 수량 |
|------|------|
| api JAR 수정 클래스 | 913개 |
| obf JAR 수정 클래스 | 665개 |
| 번역 사전 합계 (핵심 게임) | 16,356개 (common 9,667 + api 3,472 + obf 3,217) |
| **Nexerelin 모드 번역** | **4,233개** |
| 스킬 파일 | 59개 |
| descriptions.csv 항목 | 721개 |
| rules.csv 번역 | 2,245개 |
| ship_data.csv 항목 | 211줄 |
| .skin 파일 | 65개 |
| 임무 MissionDefinition.java | 16개 |

---

## 번역 용어집

| 영어 | 한국어 |
|------|--------|
| Fleet | 함대 |
| Colony | 식민지 |
| Credits | 크레딧 |
| Faction | 세력 |
| Market | 시장 |
| Officer | 장교 |
| Hull | 선체 |
| Armor | 장갑 |
| Shield | 방어막 |
| Flux | 플럭스 |
| Combat Readiness | 전투 준비도 |
| Peak Active Performance | 최고 성능 유지 |
| Phase Cloak | 위상 클로킹 |
| Carrier | 항모 |

더 많은 번역 규칙은 `TRANSLATION_NOTES.md`를 참고하세요.

---

## 제약사항

- **DRM 클래스 번역 금지**: `accidents/A.class` 문자열은 시리얼 인증에 사용됨. 번역 시 게임 실행 불가.
- **launcher 번역 금지**: `com/fs/starfarer/launcher/` 및 `StarfarerLauncher.class`
- **게임 ID 번역 금지**: 난이도 코드(EASY/MEDIUM/HARD 등), 단일 소문자 단어 식별자
- **`.bak` 파일 관리**: 게임 업데이트 전 반드시 미리 `.bak` 백업. 없으면 `restore` 파이프라인 불가.
- **`starsectorkorean` 모드 필수**: 빌드 전 원본 모드가 `mods/starsectorkorean/`에 존재해야 함.

---

## 기여

오역 신고, 번역 수정, 신규 번역 추가 모두 환영합니다. 자세한 방법은 [`CONTRIBUTING.md`](CONTRIBUTING.md)를 참고하세요.

---

## 라이선스

이 프로젝트는 자유롭게 사용, 수정, 재배포할 수 있습니다. 자세한 내용은 [`LICENSE`](LICENSE) 파일을 참고하세요.

`tools/cfr.jar`은 MIT License의 CFR 디컴파일러입니다 (저작권: Lee Benfield).

Starsector 게임 자체는 Fractal Softworks의 저작물이며 이 프로젝트와 무관합니다.
