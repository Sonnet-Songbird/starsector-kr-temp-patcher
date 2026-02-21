#!/bin/bash
# 06_package.sh - 패치된 클래스 파일을 새 JAR로 패키징
#
# 사전 요구사항:
#   - patched_jar/ 디렉토리 존재 (05_patch_classes.py 실행 후)

set -e

BASE="$(cd "$(dirname "$0")/.." && pwd)"
JAR_CMD="jar"
OUT_JAR="$BASE/output/starfarer.api.kr.jar"

echo "=== JAR 패키징 ==="

mkdir -p "$BASE/output"

cd "$BASE/patched_jar"
"$JAR_CMD" cf "$OUT_JAR" .

SIZE=$(ls -la "$OUT_JAR" | awk '{print $5}')
echo "완료: $OUT_JAR ($SIZE bytes)"
echo ""
echo "적용 방법:"
echo "  1. 백업: cp starsector-core/starfarer.api.jar starfarer.api.jar.bak"
echo "  2. 교체: cp $OUT_JAR starsector-core/starfarer.api.jar"
