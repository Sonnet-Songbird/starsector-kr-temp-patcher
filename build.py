#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build.py — Starsector 한글화 단일 진입점 CLI

사용법:
    python build.py <pipeline> [pipeline2 ...]

파이프라인 목록 (config.json에 정의):
    patch       — 양쪽 JAR 재패치 (output/ 에 생성)
    apply       — starsector-core + mod 적용
    restore     — 영어 원본 복원 (.bak 사용)
    verify      — spot-check 검증
    status      — 현재 적용 상태 확인
    update_mod  — mod 파일만 갱신 (JAR 재패치 없이)
    check       — verify + status
    all         — patch → apply → verify
    rebuild     — restore → patch → apply → verify

예시:
    python build.py all
    python build.py patch apply
    python build.py rebuild
    python build.py restore
    python build.py verify
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "config.json"


def _abs(paths_dict, base_dir):
    """상대경로 값을 절대경로로 변환. 절대경로는 그대로 유지."""
    out = {}
    for k, v in paths_dict.items():
        if isinstance(v, str) and (v.startswith("./") or v.startswith("../") or v == "."):
            out[k] = str((base_dir / v).resolve())
        else:
            out[k] = v
    return out


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["paths"] = _abs(cfg["paths"], SCRIPT_DIR)
    return cfg


def resolve(value, paths):
    """경로 문자열에서 {변수} 치환."""
    if isinstance(value, str):
        for k, v in paths.items():
            value = value.replace(f"{{{k}}}", v)
        return value
    if isinstance(value, list):
        return [resolve(v, paths) for v in value]
    return value


def run_script(script_rel, args, paths, python_cmd):
    script_path = SCRIPT_DIR / script_rel
    cmd = [python_cmd, str(script_path)] + (args or [])
    print(f"  [script] {script_rel}")
    result = subprocess.run(cmd, cwd=str(SCRIPT_DIR))
    if result.returncode != 0:
        raise RuntimeError(f"스크립트 실패: {script_rel} (exit {result.returncode})")


def run_command(cmd_list, paths):
    cmd = resolve(cmd_list, paths)
    print(f"  [command] {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"명령 실패: {' '.join(cmd)} (exit {result.returncode})")


def do_copy(src, dst, paths):
    src = resolve(src, paths)
    dst = resolve(dst, paths)
    print(f"  [copy] {src} → {dst}")
    shutil.copy2(src, dst)


def do_sync(src_dir, dst_dir, paths):
    """src_dir의 모든 파일을 dst_dir에 동기화 (덮어쓰기)."""
    src_dir = resolve(src_dir, paths)
    dst_dir = resolve(dst_dir, paths)
    print(f"  [sync] {src_dir} → {dst_dir}")
    if not os.path.isdir(src_dir):
        raise RuntimeError(f"소스 디렉토리 없음: {src_dir}")
    os.makedirs(dst_dir, exist_ok=True)
    count = 0
    for root, dirs, files in os.walk(src_dir):
        rel = os.path.relpath(root, src_dir)
        target_dir = os.path.join(dst_dir, rel)
        os.makedirs(target_dir, exist_ok=True)
        for fname in files:
            shutil.copy2(os.path.join(root, fname), os.path.join(target_dir, fname))
            count += 1
    print(f"         {count}개 파일 동기화됨")


def execute_step(step, paths, python_cmd):
    """단일 스텝 실행."""
    if "script" in step:
        run_script(step["script"], step.get("args"), paths, python_cmd)
    elif "command" in step:
        run_command(step["command"], paths)
    elif "copy" in step:
        do_copy(step["copy"], step["to"], paths)
    elif "sync" in step:
        do_sync(step["sync"], step["to"], paths)
    else:
        raise ValueError(f"알 수 없는 스텝 타입: {step}")


def run_pipeline(name, config, visited=None):
    """파이프라인 실행 (중첩 파이프라인 지원)."""
    if visited is None:
        visited = set()
    if name in visited:
        raise RuntimeError(f"순환 파이프라인 감지: {name}")
    visited.add(name)

    pipelines = config["pipelines"]
    paths = config["paths"]
    python_cmd = paths.get("python", "python")

    if name not in pipelines:
        available = ", ".join(pipelines.keys())
        raise ValueError(f"알 수 없는 파이프라인: '{name}'\n사용 가능: {available}")

    steps = pipelines[name]
    print(f"\n{'='*50}")
    print(f"파이프라인: {name}")
    print(f"{'='*50}")

    for step in steps:
        if isinstance(step, str):
            # 중첩 파이프라인
            run_pipeline(step, config, visited=set(visited))
        else:
            execute_step(step, paths, python_cmd)

    print(f"[OK] {name} 완료")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    config = load_config()
    pipelines_to_run = sys.argv[1:]

    failed = []
    for pipeline_name in pipelines_to_run:
        try:
            run_pipeline(pipeline_name, config)
        except (RuntimeError, ValueError, FileNotFoundError) as e:
            print(f"\n[FAIL] {pipeline_name}: {e}", file=sys.stderr)
            failed.append(pipeline_name)
            break  # 실패 시 이후 파이프라인 중단

    print(f"\n{'='*50}")
    if failed:
        print(f"결과: FAIL ({', '.join(failed)})")
        sys.exit(1)
    else:
        ran = ", ".join(pipelines_to_run)
        print(f"결과: ALL OK ({ran})")


if __name__ == "__main__":
    main()
