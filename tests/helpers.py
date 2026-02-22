"""helpers.py - 테스트 공용 헬퍼 함수"""

import struct
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
from patch_utils import decode_java_utf8, parse_constant_pool


def get_string_literals(jar_path: Path, classname: str) -> set:
    """JAR 내 클래스의 CONSTANT_String 참조 Utf8 세트를 반환."""
    with zipfile.ZipFile(jar_path) as z:
        data = z.read(classname)
    entries, _ = parse_constant_pool(data)
    # CONSTANT_String(tag=8) 이 참조하는 utf8 인덱스 수집
    str_indices = {struct.unpack_from('>H', v)[0]
                   for tag, v in (e for e in entries if e) if tag == 8}
    result = set()
    for i, entry in enumerate(entries):
        if entry and entry[0] == 1 and i in str_indices:
            try:
                result.add(decode_java_utf8(entry[1]))
            except Exception:
                pass
    return result


def has_korean(text: str) -> bool:
    return any(0xAC00 <= ord(c) <= 0xD7A3 for c in text)


def jar_has_korean(jar_path: Path) -> bool:
    """JAR 내 임의의 클래스에 한국어 문자열이 있으면 True."""
    with zipfile.ZipFile(jar_path) as z:
        for name in z.namelist():
            if not name.endswith('.class'):
                continue
            try:
                entries, _ = parse_constant_pool(z.read(name))
            except Exception:
                continue
            for entry in entries:
                if entry and entry[0] == 1:
                    try:
                        if has_korean(decode_java_utf8(entry[1])):
                            return True
                    except Exception:
                        pass
    return False
