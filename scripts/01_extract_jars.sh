#!/bin/bash
# 01_extract_jars.sh - 현재 버전 api JAR 압축 해제
#
# 게임 업데이트 시 새 JAR의 클래스를 api_classes/ 에 추출.
# 추출 후 02_decompile.sh → build.py all 순서로 실행.
#
# 사전 요구사항:
#   - JDK 11+ (jar 명령어가 PATH에 있어야 함)
#   - starsector-core/starfarer.api.jar 존재 (.bak이 아닌 현재 버전)

set -e

BASE="$(cd "$(dirname "$0")/.." && pwd)"
GAME_CORE="$(cd "$BASE/../starsector-core" && pwd)"
JAR_CMD="jar"

echo "=== api JAR 압축 해제 ==="

# 기존 api_classes 초기화
mkdir -p "$BASE/api_classes"
rm -rf "$BASE/api_classes/"* 2>/dev/null || true

# 현재 버전 JAR 압축 해제
echo "starfarer.api.jar 압축 해제 중..."
cd "$BASE/api_classes"
"$JAR_CMD" xf "$GAME_CORE/starfarer.api.jar"
echo "  완료: $(find . -name '*.class' | wc -l) classes"

echo ""
echo "완료! 다음 단계: bash scripts/02_decompile.sh"
