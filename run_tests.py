#!/usr/bin/env python3
"""run_tests.py — 빌드 산출물 자동 테스트 (apply 전 실행)

프레임워크: unittest (표준 라이브러리, 추가 설치 불필요)

사용법:
    python run_tests.py           # 전체 (간략 출력)
    python run_tests.py -v        # 상세 출력
    python run_tests.py -k jar    # 키워드 필터 (파이프라인 실행 시 무시)
"""

import subprocess
import sys
from pathlib import Path

TESTS_DIR = str(Path(__file__).parent / 'tests')


def main():
    cmd = [sys.executable, '-m', 'unittest', 'discover',
           '-s', TESTS_DIR, '-p', 'test_*.py']
    # -v 플래그 전달 지원
    if '-v' in sys.argv:
        cmd.append('-v')
    sys.exit(subprocess.run(cmd).returncode)


if __name__ == '__main__':
    main()
