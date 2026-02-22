# 기여 방법

오역 신고, 번역 수정, 신규 번역 추가 모두 환영합니다.
프로그래밍 지식이 없어도 기여할 수 있습니다.

---

## 1. 오역/누락 신고

**GitHub Issues**를 사용합니다.

1. 상단 **Issues** 탭 → **New issue** 클릭
2. 다음 정보를 포함하여 작성:
   - 원문 (영어)
   - 현재 번역 (한국어)
   - 제안 번역 (한국어)
   - 게임 내 위치 (어느 화면/메뉴/이벤트에서 보이는지)

---

## 2. 번역 수정 / 추가 (Pull Request)

### 어떤 파일을 수정해야 하나요?

| 번역 대상 | 수정할 파일 |
|----------|------------|
| 게임 UI 하드코딩 문자열 (버튼·레이블·메시지·스킬 효과 등 대부분) | `patches/common.json` |
| api JAR 전용 문자열 (스킬 fragment, 전투 수치 접미사) | `patches/api_jar.json` |
| obf JAR 전용 문자열 (시장·행성·함대 관련 심층 UI) | `patches/obf_jar.json` |
| 함선·무기·행성 설명 | `patches/starsectorkorean/data/strings/descriptions.csv` |
| 대화·이벤트 텍스트 | `patches/starsectorkorean/data/campaign/rules.csv` |
| UI 시스템 메시지 | `patches/starsectorkorean/data/strings/strings.json` |
| 툴팁 | `patches/starsectorkorean/data/strings/tooltips.json` |
| 함선 이름 | `patches/starsectorkorean/data/hulls/ship_data.csv` |
| Nexerelin 모드 텍스트 전반 | `patches/Nexerelin/translations.json` |

> **중요: `output/` 폴더의 파일은 절대 직접 수정하지 마세요.**
> `output/`은 빌드 산출물이며 다음 빌드 시 덮어씌워집니다. 수정한 내용이 소실됩니다.
> 반드시 위 표의 `patches/` 경로에 있는 소스 파일을 수정해야 합니다.

---

### 번역 사전 파일 형식

`patches/common.json`, `patches/api_jar.json`, `patches/obf_jar.json`, `patches/Nexerelin/translations.json`은 모두 동일한 형식입니다:

```json
{
  "영어 원문 그대로": "한국어 번역",
  "Fleet": "함대",
  "Combat Readiness": "전투 준비도",
  "Damage dealt: %s": "가한 피해: %s"
}
```

- 키(왼쪽)는 게임 소스의 영어 문자열과 **정확히 일치**해야 합니다 (대소문자, 공백, 특수문자 포함).
- `%s`, `$변수명` 같은 치환 플레이스홀더는 번역문에도 그대로 포함시킵니다.
- JSON 형식을 지켜주세요: 마지막 항목을 제외한 모든 줄 끝에 쉼표.

---

### 웹 UI로 수정하는 방법 (로컬 환경 불필요)

GitHub에서 직접 편집할 수 있습니다:

1. 수정할 파일을 클릭 (예: `patches/common.json`)
2. 오른쪽 상단 연필 아이콘 **Edit this file** 클릭
3. `Ctrl+F`로 수정할 영어 원문 검색
4. 한국어 값 수정
5. 하단 **Propose changes** 클릭 → Pull Request 생성

---

### 번역이 어느 파일에 있는지 모를 때

`patches/` 아래 JSON 파일들을 일괄 검색합니다:

```bash
python -c "
import json, glob
query = '찾을 영어 원문'  # 여기에 영어 원문 입력
for f in glob.glob('patches/**/*.json', recursive=True):
    try:
        d = json.load(open(f, encoding='utf-8'))
        if isinstance(d, dict) and query in d:
            print(f, '->', d[query])
    except: pass
"
```

---

## 3. 번역 규칙

### 번역하면 안 되는 것 (절대 금지)

다음은 게임 내부에서 **ID 또는 인증 키로 사용**되므로 번역 사전에 포함하지 않습니다:

- **DRM 문자열**: `"Nobody will ever pirate starfarer"` 등 `accidents/A.class`의 문자열
  → 번역 시 게임 실행 불가 (시리얼 인증 실패)
- **XStream 세이브 alias**: `"Hyperspace"`, `"Farming"`, `"Mining"` 등
  → 번역 시 기존 세이브 파일 로드 불가 (`CannotResolveClassException`)
- **게임 내부 ID/코드**: `EASY`, `MEDIUM`, `HARD`, `IMPOSSIBLE`, `VARIABLE`
  → 번역 시 난이도 선택 UI 오동작
- **단일 소문자 단어**: `"fleet"`, `"credits"`, `"colony"` 등
  → 내부 Map 키 또는 비교 값으로 사용될 가능성이 높음

> 자세한 기술 규칙은 `TRANSLATION_NOTES.md` 1절을 참고하세요.

### 표준 용어집 (반드시 준수)

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

### 번역하지 않는 것 (고유명사)

- 고유 함선명: Onslaught, Conquest, Odyssey, Invincible 등
- 세력명: Hegemony, Tri-Tachyon, Persean League 등
- NPC 고유명사: Kanta, Sierra, Midnight 등

---

## 4. Pull Request 제출

1. 이 리포지터리를 **Fork**
2. 변경사항을 `patches/` 경로의 소스 파일에 적용
3. **Pull Request** 생성 (base: `main`)
4. PR 본문에 변경 내용 간단히 설명 (어떤 문자열을, 왜 수정했는지)

---

## 5. 로컬 빌드 (선택 사항)

수정 후 직접 빌드하고 게임에서 확인하려면 `README.md`의 **전체 빌드 방법** 섹션을 참고하세요.

| 수정 대상 | 권장 빌드 명령 |
|----------|--------------|
| `patches/common.json` / `api_jar.json` / `obf_jar.json` | `python build.py all` |
| `patches/starsectorkorean/data/` 파일 | `python build.py update_mod` |
| `patches/Nexerelin/translations.json` | `python build.py update_mod` |
| 전체 클린 재빌드 | `python build.py rebuild` |

빌드 후 `python build.py verify`로 번역 적용 여부를 확인합니다.
