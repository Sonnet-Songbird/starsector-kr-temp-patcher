# Nexerelin 한국어 패치 (준비 중)

Nexerelin 모드 한국어 번역 패치 데이터 폴더입니다.

## 구조

- `translations.json` — EN→KO 번역 사전 (현재 비어있음)
- `data/` — 파일 오버레이 (번역 완료 파일 직접 교체, 향후 추가)
- `graphics/` — 폰트 등 리소스 (향후 추가)

## 사용법

`config.json`에서 `"enabled": true`로 변경하면 빌드 파이프라인에 자동 포함됩니다.

번역 진행 방법:
1. `translations.json`에 EN→KO 번역 쌍 추가
2. `python build.py update_mod` 실행

## 전제 조건

Nexerelin 모드가 게임 mods/ 폴더에 설치되어 있어야 합니다.
