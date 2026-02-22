# Nexerelin 한국어 패치

Nexerelin 모드 한국어 번역 패치 데이터 폴더.

## 파일 구조

| 파일 | 역할 |
|------|------|
| `translations.json` | EN→KO 번역 사전 (데이터 파일 번역에 적용) |
| `exclusions.json` | 모드 전용 패치 제외 목록 |
| `data/` | 파일 오버레이 (번역 완료 파일 직접 교체, 향후 추가) |
| `graphics/` | 리소스 오버레이 (향후 추가) |

## 번역 적용 방식

**데이터 파일 번역** (`translations.json` 경유):
- `build_mods.py`가 `translations.json` 사전으로 Nexerelin의 `data/` 내 JSON/CSV 값 교체
- `common.json` 공통 번역 + `translations.json` 모드 전용 번역 순으로 적용 (모드 전용 우선)

**JAR 번역** (`ExerelinCore.jar` 상수 풀 패치):
- `patch_mod_jar.py`가 post_build 훅으로 자동 실행
- `exclusions.json`의 제외 목록 + 전역 `patches/exclusions.json` 합집합 적용

## exclusions.json 관리

```json
{
  "blocked_classes": [
    "exerelin/plugins/XStreamConfig.class"
  ],
  "blocked_strings": []
}
```

**`blocked_classes`**: 이 클래스 파일은 번역 없이 원본 그대로 JAR에 포함됨.
- `XStreamConfig.class`: 세이브 직렬화용 XStream alias 110개 등록. 번역 시 기존 세이브 로드 실패 (`CannotResolveClassException`).

**`blocked_strings`**: 번역 사전에 있어도 이 JAR에서는 적용 금지.
- 현재 비어있음 (전역 exclusions.json의 blocked_strings로 충분)
- Nexerelin 내부 ID 문자열이 common.json과 충돌하면 여기에 추가

## 빌드

```bash
# Nexerelin + starsectorkorean 모두 빌드
python build.py update_mod

# 번역 후보 추출 (신규 번역 작업 시 1회)
python scripts/extract_mod_strings.py --mod Nexerelin
# → intermediate/Nexerelin_candidates.json
```

## 전제 조건

Nexerelin 모드가 게임 `mods/Nexerelin/` 폴더에 설치되어 있어야 함.
`config.json`의 `"enabled": true` 확인.
