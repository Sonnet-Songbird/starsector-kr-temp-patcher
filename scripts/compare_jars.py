#!/usr/bin/env python3
"""
compare_jars.py - 두 api JAR의 클래스 변경사항 비교

게임 업데이트 후 어떤 클래스가 바뀌었는지 확인할 때 사용.

사용법:
    python compare_jars.py <이전_클래스_폴더> <새_클래스_폴더>

예시 (게임 업데이트 후):
    # 1. 이전 버전 api_classes를 따로 보관
    cp -r api_classes api_classes_0.98a
    # 2. 새 JAR 추출 (01_extract_jars.sh)
    # 3. 비교
    python scripts/compare_jars.py api_classes_0.98a api_classes

인자 없이 실행 시 기본값: api_classes/ vs patched_jar/ (패치 전후 비교)
"""

from pathlib import Path
import os, hashlib, sys

SCRIPT_DIR = Path(__file__).parent.parent

def hash_classes(dirpath):
    classes = {}
    for root, dirs, files in os.walk(dirpath):
        for f in files:
            if not f.endswith('.class'):
                continue
            path = os.path.join(root, f)
            rel = os.path.relpath(path, dirpath).replace('\\', '/')
            with open(path, 'rb') as fh:
                classes[rel] = hashlib.md5(fh.read()).hexdigest()
    return classes

if len(sys.argv) == 3:
    old_dir = sys.argv[1]
    new_dir = sys.argv[2]
elif len(sys.argv) == 1:
    old_dir = str(SCRIPT_DIR / 'api_classes')
    new_dir = str(SCRIPT_DIR / 'patched_jar')
    print(f"인자 없음 → api_classes vs patched_jar 비교 (패치 전후)\n")
else:
    print(__doc__)
    sys.exit(1)

print(f"이전: {old_dir}")
print(f"이후: {new_dir}\n")

old_classes = hash_classes(old_dir)
new_classes = hash_classes(new_dir)

diff_classes = [k for k in old_classes if k in new_classes and old_classes[k] != new_classes[k]]
old_only = sorted(set(old_classes.keys()) - set(new_classes.keys()))
new_only = sorted(set(new_classes.keys()) - set(old_classes.keys()))

print(f"변경된 클래스: {len(diff_classes)}")
for k in diff_classes[:10]:
    print(f"  DIFF: {k}")
if len(diff_classes) > 10:
    print(f"  ... 외 {len(diff_classes)-10}개")

print(f"\n이전에만 있는 클래스 (삭제됨): {len(old_only)}")
for k in old_only[:5]:
    print(f"  OLD: {k}")

print(f"\n이후에만 있는 클래스 (추가됨): {len(new_only)}")
for k in new_only[:5]:
    print(f"  NEW: {k}")
