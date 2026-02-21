#!/usr/bin/env python3
"""
05_patch_classes.py - starfarer.api.jar 상수 풀 패치 (인메모리)

06_patch_obf.py와 동일한 방식으로 ZIP 파일을 디스크에 풀지 않고
zipfile 모듈로 직접 읽고 새 ZIP으로 출력.

사용법:
    python 05_patch_classes.py

입력:
    ../starsector-core/starfarer.api.jar.bak   (영어 원본 백업)
    ./intermediate/final_translations.json

출력:
    ./output/starsector-core/starfarer.api.jar  (패치본)

핵심 원리:
  - Java .class 상수 풀에서 CONSTANT_Utf8 (tag=1) 항목을 찾아 번역
  - 상수 풀 항목 수와 인덱스는 유지 (바이트코드 참조 불변)
  - Long/Double은 2슬롯 차지하므로 정확히 처리
  - Java Modified UTF-8: null → C0 80, 서로게이트 쌍 분리 (BMP 한국어는 UTF-8과 동일)
"""

import json
import os
import struct
import sys
import zipfile
from pathlib import Path
from typing import Optional, List, Tuple

SCRIPT_DIR = Path(__file__).parent.parent


def _resolve(p, base):
    """상대경로를 절대경로로 변환. 절대경로는 그대로 반환."""
    if isinstance(p, str) and (p.startswith('./') or p.startswith('../') or p == '.'):
        return str((base / p).resolve())
    return p


# ──────────────────────────────────────────────────────────────────────────────
# 제외 목록
# ──────────────────────────────────────────────────────────────────────────────

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


# ──────────────────────────────────────────────────────────────────────────────
# Java Modified UTF-8 디코딩/인코딩
# ──────────────────────────────────────────────────────────────────────────────

def decode_java_utf8(raw: bytes) -> str:
    """Java Modified UTF-8 → Python str"""
    result = []
    i = 0
    while i < len(raw):
        b = raw[i]
        if b == 0:
            # Java modified UTF-8: null byte not used; 0xC0 0x80 encodes null
            result.append('\x00')
            i += 1
        elif b < 0x80:
            result.append(chr(b))
            i += 1
        elif b < 0xC0:
            # Continuation byte without start - skip
            result.append(chr(0xFFFD))
            i += 1
        elif b < 0xE0:
            if i + 1 < len(raw):
                c = ((b & 0x1F) << 6) | (raw[i+1] & 0x3F)
                result.append(chr(c))
                i += 2
            else:
                result.append(chr(0xFFFD)); i += 1
        elif b < 0xF0:
            if i + 2 < len(raw):
                c = ((b & 0x0F) << 12) | ((raw[i+1] & 0x3F) << 6) | (raw[i+2] & 0x3F)
                result.append(chr(c))
                i += 3
            else:
                result.append(chr(0xFFFD)); i += 1
        else:
            # Supplementary chars in CESU-8: two 3-byte surrogate sequences
            # (BMP Korean doesn't need this path)
            if i + 5 < len(raw) and raw[i] == 0xED and raw[i+3] == 0xED:
                hi = ((raw[i+1] & 0x0F) << 6) | (raw[i+2] & 0x3F)
                lo = ((raw[i+4] & 0x0F) << 6) | (raw[i+5] & 0x3F)
                cp = 0x10000 + ((hi - 0xD800) << 10) + (lo - 0xDC00)
                result.append(chr(cp))
                i += 6
            else:
                result.append(chr(0xFFFD)); i += 1
    return ''.join(result)


def encode_java_utf8(s: str) -> bytes:
    """Python str → Java Modified UTF-8"""
    result = bytearray()
    for ch in s:
        cp = ord(ch)
        if cp == 0:
            result += b'\xc0\x80'  # Modified UTF-8 null
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
            # Supplementary: CESU-8 (surrogate pair)
            cp -= 0x10000
            hi = 0xD800 + (cp >> 10)
            lo = 0xDC00 + (cp & 0x3FF)
            for surrogate in (hi, lo):
                result.append(0xED)
                result.append(0xA0 | ((surrogate >> 6) & 0x0F))
                result.append(0x80 | (surrogate & 0x3F))
    return bytes(result)


# ──────────────────────────────────────────────────────────────────────────────
# 상수 풀 파싱 및 재조립
# ──────────────────────────────────────────────────────────────────────────────

def parse_constant_pool(data: bytes):
    """
    Returns:
      entries: list of (tag, bytes) or None (Long/Double dummy slot)
      rest_start: offset after constant pool
    """
    if data[:4] != b'\xca\xfe\xba\xbe':
        raise ValueError("Not a valid class file")

    count = struct.unpack_from('>H', data, 8)[0]  # constant_pool_count
    entries = [None]  # index 0 is unused
    pos = 10
    i = 1
    while i < count:
        tag = data[pos]; pos += 1
        if tag == 1:  # CONSTANT_Utf8
            length = struct.unpack_from('>H', data, pos)[0]; pos += 2
            raw = bytes(data[pos:pos+length]); pos += length
            entries.append((tag, raw))
        elif tag in (5, 6):  # Long, Double - occupy 2 slots
            entries.append((tag, bytes(data[pos:pos+8]))); pos += 8
            entries.append(None)  # dummy slot
            i += 1
        elif tag in (3, 4):  # Integer, Float
            entries.append((tag, bytes(data[pos:pos+4]))); pos += 4
        elif tag in (7, 8, 16, 19, 20):  # Class, String, MethodType, Module, Package
            entries.append((tag, bytes(data[pos:pos+2]))); pos += 2
        elif tag in (9, 10, 11, 12, 17, 18):  # Fieldref, Methodref, InterfaceMethodref, NameAndType, Dynamic, InvokeDynamic
            entries.append((tag, bytes(data[pos:pos+4]))); pos += 4
        elif tag == 15:  # MethodHandle
            entries.append((tag, bytes(data[pos:pos+3]))); pos += 3
        else:
            raise ValueError(f"Unknown constant pool tag {tag} at offset {pos-1}")
        i += 1

    return entries, pos


def rebuild_class(data: bytes, translations: dict) -> Optional[bytes]:
    """
    Apply translations to a class file's constant pool.
    Returns new class bytes, or None if no changes were made.
    """
    try:
        entries, rest_start = parse_constant_pool(data)
    except ValueError as e:
        print(f"  Parse error: {e}", file=sys.stderr)
        return None

    modified = False
    new_pool = bytearray()

    for entry in entries:
        if entry is None:
            # Long/Double dummy slot - skip (already accounted for by previous entry)
            continue

        tag, val = entry

        if tag == 1:  # CONSTANT_Utf8
            try:
                text = decode_java_utf8(val)
            except Exception:
                text = val.decode('utf-8', errors='replace')

            if text in translations:
                translated = translations[text]
                try:
                    encoded = encode_java_utf8(translated)
                except Exception:
                    encoded = translated.encode('utf-8', errors='replace')

                new_pool += bytes([1]) + struct.pack('>H', len(encoded)) + encoded
                modified = True
                continue

        # Write entry unchanged
        if tag == 1:  # CONSTANT_Utf8 needs length prefix
            new_pool += bytes([1]) + struct.pack('>H', len(val)) + val
        else:
            new_pool += bytes([tag]) + val

    if not modified:
        return None

    # Rebuild the class file:
    # header: magic(4) + minor_version(2) + major_version(2) + constant_pool_count(2)
    # + constant_pool entries + rest of class
    new_count = len(entries)  # entries[0] is None (unused slot 0), but we count it
    header = data[:8] + struct.pack('>H', new_count)
    return bytes(header) + bytes(new_pool) + data[rest_start:]


# ──────────────────────────────────────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────────────────────────────────────

def main():
    with open(SCRIPT_DIR / 'config.json', encoding='utf-8') as f:
        paths = json.load(f)['paths']

    base = SCRIPT_DIR
    bak_jar = os.path.join(_resolve(paths['game_core'], base), 'starfarer.api.jar.bak')
    out_jar = os.path.join(_resolve(paths['output_core'], base), 'starfarer.api.jar')
    trans_f = _resolve(paths['translations'], base)

    if not os.path.exists(bak_jar):
        print(f"ERROR: .bak not found: {bak_jar}", file=sys.stderr)
        print("게임 업데이트 전에 백업을 먼저 생성하세요:", file=sys.stderr)
        print("  cp starsector-core/starfarer.api.jar starsector-core/starfarer.api.jar.bak", file=sys.stderr)
        sys.exit(1)

    # translations 병합: common + api_trans
    translations = {}
    for key in ('translations', 'api_trans'):
        p = _resolve(paths.get(key, ''), base)
        if p and os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                translations.update(json.load(f))
        elif key == 'translations':
            print(f"ERROR: Translation file not found: {p}", file=sys.stderr)
            sys.exit(1)

    # exclusions 로드: blocked_classes, blocked_strings
    blocked_classes, blocked_strings = _load_exclusions(paths, base)
    if blocked_strings:
        before = len(translations)
        translations = {k: v for k, v in translations.items() if k not in blocked_strings}
        removed = before - len(translations)
        if removed:
            print(f"  제외: blocked_strings {removed}개")
    print(f"Loaded {len(translations)} translations (common + api)")

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
                result = rebuild_class(data, translations)
                if result is not None:
                    dst_zip.writestr(info, result)
                    patched += 1
                    continue

            # Non-class files (META-INF, resources) → copy as-is
            dst_zip.writestr(info, data)

    print(f"\nProcessed {total} class files")
    print(f"  Patched:  {patched}")
    print(f"  Errors:   {errors}")
    print(f"  Unchanged: {total - patched - errors}")
    print(f"\nOutput: {out_jar}")
    print(f"Size: {os.path.getsize(out_jar):,} bytes")


if __name__ == '__main__':
    main()
