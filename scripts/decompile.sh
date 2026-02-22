#!/bin/bash
# 02_decompile.sh - CFR로 현재 버전 api JAR 디컴파일
#
# 게임 업데이트 시 04_find_strings.py, check_dangerous_strings.py 등
# 소스 분석 스크립트를 위해 api_src/ 를 재생성.
#
# 사전 요구사항:
#   - tools/cfr.jar 존재
#   - Starsector 내장 JRE (게임 설치 폴더의 jre/bin/java)

set -e

BASE="$(cd "$(dirname "$0")/.." && pwd)"
GAME_CORE="$(cd "$BASE/../starsector-core" && pwd)"
GAME_ROOT="$(cd "$BASE/.." && pwd)"
JAVA="$GAME_ROOT/jre/bin/java"
CFR="$BASE/tools/cfr.jar"

echo "=== api JAR 디컴파일 (CFR) ==="

mkdir -p "$BASE/api_src"
rm -rf "$BASE/api_src/"* 2>/dev/null || true

# 현재 버전 JAR 디컴파일
echo "starfarer.api.jar 디컴파일 중..."
"$JAVA" -jar "$CFR" \
    "$GAME_CORE/starfarer.api.jar" \
    --outputdir "$BASE/api_src/" \
    --silent true
echo "  완료: $(find "$BASE/api_src" -name '*.java' | wc -l) Java 파일"

echo ""
echo "완료! 다음 단계: python scripts/04_find_strings.py (미번역 탐색)"
echo "             또는: python build.py all (전체 재패치)"
