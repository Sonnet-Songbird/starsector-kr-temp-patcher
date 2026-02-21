# TRANSLATION_NOTES.md — 번역 주의사항 및 기술 특징

---

## 1. 절대 번역 금지 항목

### 1-1. DRM 인증 문자열 (가장 중요)

`starfarer_obf.jar`의 `com/fs/starfarer/campaign/accidents/A.class`에는 농담처럼 보이지만 **시리얼 번호 저장용 Preferences 키를 파생하는 데 암호학적으로 사용되는** 문자열이 있다.

**호출 체인:**
```
CombatMain.main()
  → ooOO.getPrefs()
    → accidents.A.super()   ← 키 문자열 반환
      → Preferences.get(key, null)
        → accidents.A.super(String)  ← 검증
          → StarfarerSettings에 저장
```

**번역 금지 문자열 (일부라도 번역하면 키가 달라짐):**
```
"Nobody will ever pirate starfarer, "
"because starfarer is not pirateable. "
"It is not pirateable because I am so "
"god damned good at writing top secret code "
```
조각들을 연결한 전체 문자열도 금지. 관련 "crackers/crack it/cracking efforts" 조각 전부 포함.

**결과:** 번역 시 파생 키 변경 → `Preferences.get()` null 반환 → 인증 항상 실패 → 게임 실행 불가.

**현재 상태:** `patches/exclusions.json`의 `blocked_classes`에 `accidents/A.class`로 등록됨. 이 항목을 절대 제거하지 말 것.

### 1-2. launcher 클래스
```
com/fs/starfarer/launcher/ 패키지 전체
com/fs/starfarer/StarfarerLauncher.class
```
런처 UI는 비트맵 폰트를 사용하므로 한국어 문자를 렌더링할 수 없음. `patches/exclusions.json`의 `blocked_classes`에 등록됨.

### 1-3. 게임 내부 ID/키 역할을 하는 문자열

**확인된 오염 사례:**

| 문자열 | 역할 | 번역 시 결과 |
|--------|------|-------------|
| `"EASY"` | 난이도 코드 | 난이도 선택 UI 오동작 |
| `"MEDIUM"` | 난이도 코드 | 동일 |
| `"HARD"` | 난이도 코드 | 동일 |
| `"IMPOSSIBLE"` | 난이도 코드 | 동일 |
| `"VARIABLE"` | 난이도 코드 | 동일 |
| `"Hyperspace"` | XStream 클래스 alias | 세이브 파일 로드 실패 (`CannotResolveClassException`) |
| `"Farming"` | XStream 클래스 alias | 동일 |
| `"Mining"` | XStream 클래스 alias | 동일 |
| `"fleet"`, `"credits"` 등 단일 소문자 단어 | 내부 ID 가능 | 기능 오동작 가능 |

**XStream alias 메커니즘:**
게임은 세이브 파일 직렬화에 XStream을 사용하며, 클래스 이름을 짧은 별칭으로 등록한다:
```java
xstream.alias("Hyperspace", Hyperspace.class);
```
세이브 XML에는 `cl="Hyperspace"` 형태로 기록되며, 로드 시 별칭으로 클래스를 역직렬화한다. JAR 패치로 `"Hyperspace"` 문자열이 `"하이퍼스페이스"`로 교체되면 alias 등록 시 한국어로 등록되어 기존 세이브의 `cl="Hyperspace"` 속성을 해석하지 못하게 된다.

이러한 alias를 등록하는 클래스는 `patches/exclusions.json`의 `blocked_classes`에 등록해야 한다. 해당 클래스 전체가 패치에서 제외되므로, 번역 사전에 alias 문자열이 있더라도 그 클래스에서는 적용되지 않는다. alias 문자열을 표시 텍스트로도 사용하는 다른 클래스에서는 정상적으로 번역된다.

**판별 기준:**

코드에서 다음 패턴으로 사용되는 문자열은 번역 금지:
```java
// ID 반환 패턴
return "some_string";
getId() { return "string"; }

// 비교/조회 패턴
if (x.equals("MEDIUM")) ...
switch (difficulty) { case "HARD": ... }
map.get("fleet")
map.containsKey("credits")
map.put("colony", ...)
```

번역 안전한 패턴:
```java
// UI 렌더링 호출
addPara("Fleet size: %s", ...)
setText("Combat Readiness")
addTitle("Market Info")
throw new RuntimeException("Fleet is null")
log.info("Fleet deployed")
```

`scripts/check_dangerous_strings.py`로 사전 확인 가능.

---

## 2. 번역 데이터 오염 패턴

### 2-1. rules.csv 항목 오염
`data/campaign/rules.csv`의 조건/스크립트 텍스트를 `patches/common.json`에 포함하면 오염됨.

**제외해야 하는 패턴:**
- 개행 문자(`\n`)가 포함된 멀티라인 항목
- 숫자로 시작하는 항목 (`"100 credits"`, `"3 months"` 등)
- `$변수명`, `#태그` 등 rules.csv 전용 문법 포함 항목

`scripts/final_clean.py`가 이러한 항목을 자동 제거함.

### 2-2. 단일 소문자 단어 오염
`"fleet"`, `"colony"`, `"market"`, `"credits"` 등 단독으로 쓰이는 단어는 게임 내부 ID일 가능성이 높음. 짧은 단어는 반드시 컨텍스트 확인 후 추가.

`scripts/clean_translations.py`에 위험 단어 필터 목록이 있음.

---

## 3. Java .class 파일 기술 특징

### 3-1. 상수 풀(Constant Pool) 구조
Java 클래스 파일의 문자열 리터럴은 상수 풀(CP)에 저장됨. 패치는 CP의 `CONSTANT_Utf8` 항목(tag=1)만 수정하면 됨. 다른 바이트코드 영역은 건드리지 않음.

```
클래스 파일 구조:
[magic 4B][minor 2B][major 2B][CP 개수 2B][CP 항목들...][나머지 바이트코드]
```

**패치 원칙**: CP만 교체하고 나머지 바이트코드는 원본 그대로. 상수 풀 인덱스는 바이트코드 내 명령에 하드코딩되어 있지만, 값만 바꾸는 것이므로 인덱스 변경 없음 → 바이트코드 수정 불필요.

### 3-2. Long/Double 2슬롯 규칙
CP에서 `Long`(tag=5)와 `Double`(tag=6)은 두 슬롯을 차지함. 파싱 시 반드시 `i += 2` 처리해야 이후 슬롯 번호가 어긋나지 않음.

```python
elif tag in (5, 6):  # Long, Double
    entries.append((tag, data[pos:pos+8])); pos += 8
    entries.append(None)  # 빈 더미 슬롯
    i += 1  # 추가로 1 증가 (루프에서 1 더하므로 총 2 증가)
```

이를 빠뜨리면 이후 모든 CP 인덱스가 1씩 어긋나서 클래스 파일이 깨짐.

### 3-3. Java Modified UTF-8 vs 표준 UTF-8
Java 클래스 파일의 CONSTANT_Utf8 항목은 **Java Modified UTF-8** 인코딩을 사용함. 표준 UTF-8과의 차이:
- Null 문자(`\u0000`)를 2바이트 `\xC0\x80`으로 인코딩
- 보조 평면 문자(U+10000 이상, 이모지 등)를 서로게이트 쌍으로 인코딩

**현재 코드**: Python의 `utf-8`로 디코딩 사용 중. 한국어 완성형(U+AC00–U+D7A3)은 BMP 범위이므로 차이 없음. 이모지나 희귀 문자가 포함되면 `cesu8` 패키지 필요.

### 3-4. CP 재조립 시 개수 필드 주의
패치 후 CP를 재조립할 때 항목 개수 필드(`CP count`)는 실제 항목 수 + 1 (인덱스 1부터 시작하는 규약). Long/Double의 더미 슬롯도 카운트에 포함.

```python
# 잘못된 예
header = data[:8] + struct.pack('>H', len(real_entries) + 1)

# 올바른 예 (더미 슬롯 포함)
header = data[:8] + struct.pack('>H', len(all_entries_including_dummies) + 1)
```

---

## 4. 번역 품질 기준

### 4-1. 용어 일관성
아래 표준 용어 외의 표현 사용 금지:

| 영어 | 한국어 |
|------|--------|
| Phase Cloak | 위상 클로킹 |
| Combat Readiness | 전투 준비도 |
| Peak Active Performance | 최고 성능 유지 |
| Flux | 플럭스 |
| Faction | 세력 |
| Carrier | 항모 |

더 많은 용어 → `README.md` 번역 용어집 참고.

### 4-2. 번역 금지 (원문 유지)
- 고유 함선명 (Onslaught, Conquest 등)
- 세력명 (Hegemony, Tri-Tachyon 등)
- 함장/NPC 고유명사

### 4-3. 번역 선택 사항
- 로그 메시지 (`log.info(...)`)는 번역해도 무방하나 우선순위 낮음
- 개발자 디버그 텍스트는 번역 불필요

---

## 5. 파이프라인 운용 주의사항

### 5-1. .bak 파일 없으면 restore 불가
`restore` 파이프라인은 `.bak` 파일에 의존함. `.bak`이 없으면 영어 원본으로 돌아갈 수 없음.
→ 게임 업데이트 시 **반드시 먼저 백업**:
```bash
cp starsector-core/starfarer.api.jar starsector-core/starfarer.api.jar.bak
cp starsector-core/starfarer_obf.jar starsector-core/starfarer_obf.jar.bak
```

### 5-2. .bak 파일에서 인메모리 패치
`scripts/05_patch_classes.py`는 `starfarer.api.jar.bak`에서 직접 읽어 인메모리로 번역 후 `output/starsector-core/starfarer.api.jar`에 바로 쓴다. `api_classes/`는 게임 업데이트 전후 비교(`compare_jars.py`)에만 필요하며 패칭에는 사용되지 않는다.

### 5-3. 패치 소스와 output/ 분리
- `patches/starsectorkorean/` (리포 내) → 모드 오버레이 파일. 커밋 대상. `translations.json`, `data/`, `graphics/` 포함.
- `build_mod` 파이프라인: 게임 설치 폴더의 원본 모드(`mods/starsectorkorean/`) + `patches/starsectorkorean/` 오버레이 → `output/mods/starsectorkorean/` 빌드.
- `output/mods/starsectorkorean/` → 빌드 산출물. gitignore. 릴리즈 ZIP 소스.
- `output/` 전체는 절대 커밋하지 않는다.

### 5-4. 동시 실행 금지
여러 `build.py` 인스턴스를 동시에 실행하면 출력 JAR 파일에 동시 접근이 발생하여 충돌할 수 있음.

---

## 6. 모드 오버라이드 방식

Starsector는 모드의 데이터 파일이 게임 원본 파일을 오버라이드함. `starsectorkorean` 모드는 다음 파일들을 오버라이드:

| 파일 | 위치 | 게임 원본 대비 |
|------|------|--------------|
| `data/strings/strings.json` | 모드 내 | 한국어 UI 문자열 |
| `data/strings/tooltips.json` | 모드 내 | 한국어 툴팁 |
| `data/characters/skills/*.skill` | 모드 내 | 59개 스킬 오버라이드 |
| `data/strings/descriptions.csv` | 모드 내 | 721개 설명 |
| `data/campaign/rules.csv` | 모드 내 | 2,245개 rules 번역 |
| `data/hulls/ship_data.csv` | 모드 내 | 함선 이름 번역 |
| `data/hulls/skins/*.skin` | 모드 내 | 65개 스킨 이름 |
| `data/missions/*/MissionDefinition.java` | 모드 내 | 16개 임무 번역 |

JAR 패치는 모드 오버라이드로 처리할 수 없는 **Java 하드코딩 문자열**을 번역하기 위함.
