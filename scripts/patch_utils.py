#!/usr/bin/env python3
"""
patch_utils.py - Java .class 상수 풀 패칭 공유 라이브러리

05_patch_classes.py, 06_patch_obf.py, patch_mod_jar.py 등이 공통으로 사용하는
알고리즘 모음. config/경로 의존성 없음.

공개 API:
    decode_java_utf8(raw: bytes) -> str
    encode_java_utf8(s: str) -> bytes
    parse_constant_pool(data: bytes) -> tuple[list, int]
    rebuild_class(data: bytes, translations: dict) -> Optional[bytes]
    is_blocked_class(classname: str, blocked_classes: set) -> bool
    patch_jar(src_jar, dst_jar, translations, blocked_classes, blocked_strings, label) -> dict
"""

import struct
import sys
import zipfile
from pathlib import Path
from typing import Optional


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
                c = ((b & 0x1F) << 6) | (raw[i + 1] & 0x3F)
                result.append(chr(c))
                i += 2
            else:
                result.append(chr(0xFFFD)); i += 1
        elif b < 0xF0:
            if i + 2 < len(raw):
                c = ((b & 0x0F) << 12) | ((raw[i + 1] & 0x3F) << 6) | (raw[i + 2] & 0x3F)
                result.append(chr(c))
                i += 3
            else:
                result.append(chr(0xFFFD)); i += 1
        else:
            # Supplementary chars in CESU-8: two 3-byte surrogate sequences
            # (BMP Korean doesn't need this path)
            if i + 5 < len(raw) and raw[i] == 0xED and raw[i + 3] == 0xED:
                hi = ((raw[i + 1] & 0x0F) << 6) | (raw[i + 2] & 0x3F)
                lo = ((raw[i + 4] & 0x0F) << 6) | (raw[i + 5] & 0x3F)
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
            raw = bytes(data[pos:pos + length]); pos += length
            entries.append((tag, raw))
        elif tag in (5, 6):  # Long, Double - occupy 2 slots
            entries.append((tag, bytes(data[pos:pos + 8]))); pos += 8
            entries.append(None)  # dummy slot
            i += 1
        elif tag in (3, 4):  # Integer, Float
            entries.append((tag, bytes(data[pos:pos + 4]))); pos += 4
        elif tag in (7, 8, 16, 19, 20):  # Class, String, MethodType, Module, Package
            entries.append((tag, bytes(data[pos:pos + 2]))); pos += 2
        elif tag in (9, 10, 11, 12, 17, 18):  # Fieldref, Methodref, InterfaceMethodref, NameAndType, Dynamic, InvokeDynamic
            entries.append((tag, bytes(data[pos:pos + 4]))); pos += 4
        elif tag == 15:  # MethodHandle
            entries.append((tag, bytes(data[pos:pos + 3]))); pos += 3
        else:
            raise ValueError(f"Unknown constant pool tag {tag} at offset {pos - 1}")
        i += 1

    return entries, pos


def rebuild_class(data: bytes, translations: dict) -> Optional[bytes]:
    """
    Apply translations to a class file's constant pool.
    Returns new class bytes, or None if no changes were made.

    번역 대상 = CONSTANT_String(tag 8) 참조 Utf8
              - 클래스명/필드명/메서드명으로도 사용되는 Utf8

    Java enum 클래스는 'static { VARIABLE = new TokenType("VARIABLE", 0); }'
    형태로 초기화되어 필드명 Utf8과 string literal Utf8이 같은 인덱스를 공유
    (컴파일러 중복 제거)할 수 있음. 이 경우 string_utf8_indices 에 포함되지만
    name_utf8_indices 에도 포함되어 번역 대상에서 제외됨 → NoSuchFieldError 방지.
    """
    try:
        entries, rest_start = parse_constant_pool(data)
    except ValueError as e:
        print(f"  Parse error: {e}", file=sys.stderr)
        return None

    # --- Pass 1a: 상수 풀에서 인덱스 분류 ---
    string_utf8_indices: set = set()  # CONSTANT_String 이 참조하는 Utf8 (string literal)
    name_utf8_indices: set = set()    # 식별자로 사용되는 Utf8 (번역 금지)

    for entry in entries:
        if entry is None:
            continue
        tag, val = entry
        if tag == 8:    # CONSTANT_String → utf8_index
            string_utf8_indices.add(struct.unpack_from('>H', val)[0])
        elif tag == 7:  # CONSTANT_Class → name_index (클래스명)
            name_utf8_indices.add(struct.unpack_from('>H', val)[0])
        elif tag == 12: # CONSTANT_NameAndType → name_index, descriptor_index
            name_utf8_indices.add(struct.unpack_from('>H', val)[0])
            # descriptor_index 는 "I", "Ljava/lang/String;" 형태 — 번역 대상 아님

    # --- Pass 1b: 클래스 바디에서 자신의 field/method name_index 수집 ---
    # NameAndType 은 타 클래스의 외부 참조만 커버함.
    # 클래스가 자신의 필드를 선언할 때 field_info.name_index 는 바디에만 존재.
    # enum 의 VARIABLE 필드가 이에 해당함.
    try:
        pos = rest_start + 6  # access_flags(2) + this_class(2) + super_class(2)
        icount = struct.unpack_from('>H', data, pos)[0]; pos += 2
        pos += icount * 2  # interfaces 배열 건너뜀

        # fields 와 methods 는 동일한 구조: count(2) + [access(2)+name(2)+desc(2)+attrs...]
        for _section in range(2):  # 0=fields, 1=methods
            count = struct.unpack_from('>H', data, pos)[0]; pos += 2
            for _ in range(count):
                # access_flags(2), name_index(2), descriptor_index(2)
                name_utf8_indices.add(struct.unpack_from('>H', data, pos + 2)[0])
                pos += 6
                # attributes
                acount = struct.unpack_from('>H', data, pos)[0]; pos += 2
                for _ in range(acount):
                    name_utf8_indices.add(struct.unpack_from('>H', data, pos)[0])
                    attr_len = struct.unpack_from('>I', data, pos + 2)[0]
                    pos += 6 + attr_len
    except (struct.error, IndexError):
        pass  # 파싱 실패 시 상수 풀에서 얻은 정보만 사용

    # 실제 번역 대상: string literal 이면서 식별자가 아닌 Utf8
    translatable = string_utf8_indices - name_utf8_indices
    if not translatable:
        return None  # 번역할 항목 없음 — 빠른 경로

    # --- Pass 2: 상수 풀 재조립 ---
    modified = False
    new_pool = bytearray()

    for i, entry in enumerate(entries):
        if entry is None:
            # Long/Double dummy slot - skip (already accounted for by previous entry)
            continue

        tag, val = entry

        if tag == 1 and i in translatable:  # CONSTANT_Utf8, 번역 안전
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
# 제외 규칙
# ──────────────────────────────────────────────────────────────────────────────

def is_blocked_class(classname: str, blocked_classes: set) -> bool:
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
# JAR 수준 패처 (공통 루프 로직)
# ──────────────────────────────────────────────────────────────────────────────

def patch_jar(
    src_jar: Path,
    dst_jar: Path,
    translations: dict,
    blocked_classes: set,
    blocked_strings: set,
    label: str = "",
) -> dict:
    """
    src_jar의 .class 파일에 translations를 적용해 dst_jar로 저장.
    blocked_strings는 사전에서 먼저 제거한 후 패치.
    src_jar == dst_jar인 경우(in-place) 임시 파일로 우회.

    Returns:
        dict with keys: total, patched, errors
    """
    # blocked_strings 필터링
    effective_translations = translations
    if blocked_strings:
        before = len(translations)
        effective_translations = {k: v for k, v in translations.items()
                                   if k not in blocked_strings}
        removed = before - len(effective_translations)
        if removed and label:
            print(f"  [{label}] 제외: blocked_strings {removed}개")

    src_jar = Path(src_jar)
    dst_jar = Path(dst_jar)
    in_place = src_jar.resolve() == dst_jar.resolve()

    if in_place:
        # in-place: 임시 파일에 쓴 뒤 교체
        tmp_jar = dst_jar.with_suffix('.jar.tmp')
    else:
        tmp_jar = dst_jar
        dst_jar.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    patched = 0
    errors = 0

    with zipfile.ZipFile(src_jar, 'r') as src_zip, \
         zipfile.ZipFile(tmp_jar, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as dst_zip:

        for info in src_zip.infolist():
            try:
                data = src_zip.read(info.filename)
            except Exception as e:
                print(f"  Read error {info.filename}: {e}")
                errors += 1
                continue

            if info.filename.endswith('.class'):
                total += 1
                if is_blocked_class(info.filename, blocked_classes):
                    dst_zip.writestr(info, data)
                    continue
                result = rebuild_class(data, effective_translations)
                if result is not None:
                    dst_zip.writestr(info, result)
                    patched += 1
                    continue

            # Non-class files (META-INF, resources) → copy as-is
            dst_zip.writestr(info, data)

    if in_place:
        import os
        os.replace(tmp_jar, dst_jar)

    return {"total": total, "patched": patched, "errors": errors}
