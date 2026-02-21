#!/usr/bin/env python
"""
06_patch_obf.py - starfarer_obf.jar 번역 패치 (인메모리)

05_patch_classes.py와 동일한 방식으로 ZIP 파일을 디스크에 풀지 않고
zipfile 모듈로 직접 읽고 새 ZIP으로 출력.
(obfuscated 클래스 파일명이 255자 이상인 경우가 있어 Windows MAX_PATH 우회 필요)

사용법:
    python 06_patch_obf.py

입력:
    ../starsector-core/starfarer_obf.jar.bak   (영어 원본 백업)
    ./intermediate/final_translations.json

출력:
    ./output/starsector-core/starfarer_obf.jar  (패치본)
"""

import json
import os
import struct
import sys
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent


def _resolve(p, base):
    """상대경로를 절대경로로 변환. 절대경로는 그대로 반환."""
    if isinstance(p, str) and (p.startswith('./') or p.startswith('../') or p == '.'):
        return str((base / p).resolve())
    return p


# ─────────────────────────────────────────────────────
# 제외 목록
# ─────────────────────────────────────────────────────

def _load_exclusions(paths, base):
    """patches/exclusions.json에서 blocked_classes, blocked_strings 로드."""
    excl_file = _resolve(paths.get('exclusions', ''), base)
    if excl_file and os.path.exists(excl_file):
        with open(excl_file, encoding='utf-8') as f:
            excl = json.load(f)
        return set(excl.get('blocked_classes', [])), set(excl.get('blocked_strings', []))
    return set(), set()


def _is_blocked_class(classname: str, blocked_classes: set) -> bool:
    """클래스 경로가 blocked_classes에 포함되는지 확인 (접미 '/'는 패키지 전체 매치)."""
    for bc in blocked_classes:
        if bc.endswith('/'):
            if classname.startswith(bc):
                return True
        else:
            if classname == bc:
                return True
    return False


# ─────────────────────────────────────────────────────
# Java Modified UTF-8
# ─────────────────────────────────────────────────────
def decode_java_utf8(raw: bytes) -> str:
    result = []
    i = 0
    while i < len(raw):
        b = raw[i]
        if b == 0:
            result.append('\x00'); i += 1
        elif b < 0x80:
            result.append(chr(b)); i += 1
        elif b < 0xC0:
            result.append('\uFFFD'); i += 1
        elif b < 0xE0:
            if i + 1 < len(raw):
                c = ((b & 0x1F) << 6) | (raw[i+1] & 0x3F)
                result.append(chr(c)); i += 2
            else:
                result.append('\uFFFD'); i += 1
        elif b < 0xF0:
            if i + 2 < len(raw):
                c = ((b & 0x0F) << 12) | ((raw[i+1] & 0x3F) << 6) | (raw[i+2] & 0x3F)
                result.append(chr(c)); i += 3
            else:
                result.append('\uFFFD'); i += 1
        else:
            if i + 5 < len(raw) and raw[i] == 0xED and raw[i+3] == 0xED:
                hi = ((raw[i+1] & 0x0F) << 6) | (raw[i+2] & 0x3F)
                lo = ((raw[i+4] & 0x0F) << 6) | (raw[i+5] & 0x3F)
                cp = 0x10000 + ((hi - 0xD800) << 10) + (lo - 0xDC00)
                result.append(chr(cp)); i += 6
            else:
                result.append('\uFFFD'); i += 1
    return ''.join(result)


def encode_java_utf8(s: str) -> bytes:
    result = bytearray()
    for ch in s:
        cp = ord(ch)
        if cp == 0:
            result += b'\xc0\x80'
        elif cp < 0x80:
            result.append(cp)
        elif cp < 0x800:
            result.append(0xC0 | (cp >> 6))
            result.append(0x80 | (cp & 0x3F))
        elif cp < 0x10000:
            result.append(0xE0 | (cp >> 12))
            result.append(0x80 | ((cp >> 6) & 0x3F))
            result.append(0x80 | (cp & 0x3F))
        else:
            cp -= 0x10000
            hi = 0xD800 + (cp >> 10)
            lo = 0xDC00 + (cp & 0x3FF)
            for surrogate in (hi, lo):
                result.append(0xED)
                result.append(0xA0 | ((surrogate >> 6) & 0x0F))
                result.append(0x80 | (surrogate & 0x3F))
    return bytes(result)


# ─────────────────────────────────────────────────────
# 상수 풀 패치
# ─────────────────────────────────────────────────────
def patch_class(data: bytes, translations: dict):
    """번역 적용. 변경 없으면 None 반환."""
    if data[:4] != b'\xca\xfe\xba\xbe':
        return None
    try:
        count = struct.unpack_from('>H', data, 8)[0]
        entries = [None]  # index 0 unused
        pos = 10
        i = 1
        while i < count:
            tag = data[pos]; pos += 1
            if tag == 1:
                length = struct.unpack_from('>H', data, pos)[0]; pos += 2
                raw = bytes(data[pos:pos+length]); pos += length
                entries.append((tag, raw))
            elif tag in (5, 6):
                entries.append((tag, bytes(data[pos:pos+8]))); pos += 8
                entries.append(None); i += 1
            elif tag in (3, 4):
                entries.append((tag, bytes(data[pos:pos+4]))); pos += 4
            elif tag in (7, 8, 16, 19, 20):
                entries.append((tag, bytes(data[pos:pos+2]))); pos += 2
            elif tag in (9, 10, 11, 12, 17, 18):
                entries.append((tag, bytes(data[pos:pos+4]))); pos += 4
            elif tag == 15:
                entries.append((tag, bytes(data[pos:pos+3]))); pos += 3
            else:
                return None  # unknown tag
            i += 1
        rest_start = pos
    except Exception:
        return None

    modified = False
    new_pool = bytearray()

    for entry in entries:
        if entry is None:
            continue
        tag, val = entry
        if tag == 1:
            try:
                text = decode_java_utf8(val)
            except Exception:
                text = val.decode('utf-8', errors='replace')
            if text in translations:
                encoded = encode_java_utf8(translations[text])
                new_pool += bytes([1]) + struct.pack('>H', len(encoded)) + encoded
                modified = True
                continue
        if tag == 1:
            new_pool += bytes([1]) + struct.pack('>H', len(val)) + val
        else:
            new_pool += bytes([tag]) + val

    if not modified:
        return None

    new_count = len(entries)
    header = data[:8] + struct.pack('>H', new_count)
    return bytes(header) + bytes(new_pool) + data[rest_start:]


# ─────────────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────────────
def main():
    with open(SCRIPT_DIR / 'config.json', encoding='utf-8') as f:
        paths = json.load(f)['paths']

    base = SCRIPT_DIR
    bak_jar = os.path.join(_resolve(paths['game_core'], base), 'starfarer_obf.jar.bak')
    out_jar = os.path.join(_resolve(paths['output_core'], base), 'starfarer_obf.jar')

    if not os.path.exists(bak_jar):
        print(f"ERROR: {bak_jar} not found")
        print("게임 업데이트 전에 백업을 먼저 생성하세요:")
        print("  cp starsector-core/starfarer_obf.jar starsector-core/starfarer_obf.jar.bak")
        sys.exit(1)

    # translations 병합: common + obf_trans
    translations = {}
    for key in ('translations', 'obf_trans'):
        p = _resolve(paths.get(key, ''), base)
        if p and os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                translations.update(json.load(f))
        elif key == 'translations':
            print(f"ERROR: Translation file not found: {p}")
            sys.exit(1)

    # exclusions 로드: blocked_classes, blocked_strings
    blocked_classes, blocked_strings = _load_exclusions(paths, base)
    if blocked_strings:
        before = len(translations)
        translations = {k: v for k, v in translations.items() if k not in blocked_strings}
        removed = before - len(translations)
        if removed:
            print(f"  제외: blocked_strings {removed}개")
    print(f"Loaded {len(translations)} translations (common + obf)")

    os.makedirs(os.path.dirname(out_jar), exist_ok=True)

    total = 0
    patched = 0
    errors = 0

    with zipfile.ZipFile(bak_jar, 'r') as src_zip, \
         zipfile.ZipFile(out_jar, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as dst_zip:

        for info in src_zip.infolist():
            try:
                data = src_zip.read(info.filename)
            except Exception as e:
                print(f"  Read error {info.filename}: {e}")
                errors += 1
                continue

            if info.filename.endswith('.class'):
                total += 1
                if _is_blocked_class(info.filename, blocked_classes):
                    dst_zip.writestr(info, data)
                    continue
                result = patch_class(data, translations)
                if result is not None:
                    dst_zip.writestr(info, result)
                    patched += 1
                    continue

            # Non-class files (manifest, resources) → copy as-is
            dst_zip.writestr(info, data)

    print(f"\nProcessed {total} class files")
    print(f"  Patched:  {patched}")
    print(f"  Errors:   {errors}")
    print(f"  Unchanged: {total - patched - errors}")
    print(f"\nOutput: {out_jar}")
    print(f"Size: {os.path.getsize(out_jar):,} bytes")


if __name__ == '__main__':
    main()
