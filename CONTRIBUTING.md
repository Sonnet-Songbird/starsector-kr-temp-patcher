# 기여 방법

오역 신고, 번역 수정, 신규 번역 추가 모두 환영합니다.
프로그래밍 지식이 없어도 기여할 수 있습니다.

---

## 1. 오역/누락 신고

버그 신고와 동일하게 **GitHub Issues**를 사용합니다.

1. 상단 **Issues** 탭 클릭
2. **New issue** 클릭
3. 다음 정보를 포함하여 작성:
   - 원문 (영어)
   - 현재 번역 (한국어)
   - 제안 번역 (한국어)
   - 게임 내 위치 (어느 화면/메뉴에서 보이는지)

---

## 2. 번역 수정 (Pull Request)

### JAR 하드코딩 문자열 수정

`intermediate/final_translations.json`에서 수정합니다.

**웹 UI로 수정하는 방법 (프로그래밍 불필요):**

1. 이 리포지터리에서 `intermediate/final_translations.json` 파일을 클릭
2. 오른쪽 상단 연필 아이콘(Edit) 클릭
3. `Ctrl+F`로 수정할 영어 원문을 검색
4. 한국어 값을 수정
5. 하단 **Propose changes** 클릭 → Pull Request 생성

### 모드 데이터 파일 수정

`output/mods/starsectorkorean/data/` 안의 CSV/JSON 파일을 수정합니다.

- `data/strings/strings.json` — UI 문자열
- `data/strings/tooltips.json` — 툴팁
- `data/strings/descriptions.csv` — 함선/무기/행성 설명
- `data/campaign/rules.csv` — 대화/이벤트 텍스트
- `data/hulls/ship_data.csv` — 함선 이름

메모장으로도 편집할 수 있지만, UTF-8 인코딩을 지원하는 편집기(VS Code, Notepad++ 등)를 권장합니다.

---

## 3. Pull Request 제출

1. 이 리포지터리를 **Fork**
2. 변경사항 적용
3. **Pull Request** 생성 (base: `main`)
4. PR 본문에 변경 내용을 간단히 설명

---

## 4. 번역 규칙

### 용어집 (반드시 준수)

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
| Phase Cloak | 위상 클로킹 |
| Carrier | 항모 |

### 번역하면 안 되는 것

다음은 게임 내부에서 ID로 사용되므로 **절대 번역 금지**:

- 고유 함선명: Onslaught, Conquest, Odyssey 등
- 세력명: Hegemony, Tri-Tachyon, Persean League 등
- 난이도 코드: `EASY`, `MEDIUM`, `HARD`, `IMPOSSIBLE`

### 자세한 기술 규칙

`TRANSLATION_NOTES.md`를 참고하세요.

---

## 5. 로컬 빌드 (개발자)

수정 후 직접 빌드하려면 `README.md`의 **전체 빌드 방법** 섹션을 참고하세요.

번역 추가 → 재패치 → 검증:
```bash
python build.py patch apply
python build.py verify
```
