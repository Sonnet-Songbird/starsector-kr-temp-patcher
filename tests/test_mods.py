"""test_mods.py - 모드 파일 유효성 + 번역 적용 샘플 검증"""

import csv
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
from build_mods import (
    _load_json_lazy,
    _strip_comments_and_trailing_commas,
    _normalize_lenient_json,
    _split_string_segments,
)

from base_test import BaseTestCase


class TestModFiles(BaseTestCase):
    """output/mods/ 의 텍스트 파일 유효성 검사."""

    def test_all_output_json_parseable(self):
        """한국어가 포함된 JSON 파일이 _load_json_lazy로 파싱 가능.

        우리 파이프라인이 수정한 파일(한국어 포함)만 검사:
          - 번역 파이프라인이 json.dump()로 재기록한 파일 → 표준 JSON
          - patches/에서 복사한 overlay 파일 → Starsector 비표준 JSON 허용
        두 경우 모두 _load_json_lazy가 파싱 가능해야 함.

        한국어가 없는 파일은 원본 게임 파일일 수 있으며, Java float 리터럴 등
        미지원 문법을 포함할 수 있으므로 건너뜀 (파이프라인도 건드리지 않음).
        """
        errors = []
        for f in self.output_mods.rglob('*.json'):
            if f.name == 'mod_info.json':
                continue
            text = f.read_text(encoding='utf-8', errors='replace')
            # 한국어가 없는 파일은 원본 게임 파일 → 건너뜀
            if not any(0xAC00 <= ord(c) <= 0xD7A3 for c in text):
                continue
            try:
                _load_json_lazy(text)
            except Exception as e:
                errors.append(f"{f.relative_to(self.output_mods)}: {e}")
        self.assertFalse(errors, "JSON 파싱 실패:\n" + "\n".join(errors))

    def test_all_output_csv_parseable(self):
        """output/mods/ 의 모든 CSV 파일이 파싱 가능."""
        errors = []
        for f in self.output_mods.rglob('*.csv'):
            try:
                list(csv.reader(
                    io.StringIO(f.read_text(encoding='utf-8', errors='replace'))
                ))
            except Exception as e:
                errors.append(f"{f.relative_to(self.output_mods)}: {e}")
        self.assertFalse(errors, "CSV 파싱 실패:\n" + "\n".join(errors))


class TestMissionTranslation(BaseTestCase):
    """미션 파일 번역 확인."""

    def test_forlornhope_korean(self):
        """forlornhope 미션에 '인빈서블' 포함."""
        f = (self.output_mods
             / 'starsectorkorean/data/missions/forlornhope/MissionDefinition.java')
        if not f.exists():
            self.skipTest(f"forlornhope MissionDefinition.java 없음: {f}")
        content = f.read_text(encoding='utf-8', errors='replace')
        self.assertIn('인빈서블', content, "forlornhope에 '인빈서블' 번역 없음")


class TestLenientJSONParser(unittest.TestCase):
    """Starsector 비표준 JSON 파서(_load_json_lazy 외) 단위 테스트."""

    def test_strip_line_and_block_comments(self):
        text = '{"a": 1, // line\n /* block */ "b": 2 # hash\n}'
        cleaned = _strip_comments_and_trailing_commas(text)
        self.assertEqual(_load_json_lazy(cleaned), {"a": 1, "b": 2})

    def test_preserve_comment_like_inside_string(self):
        # 문자열 안의 //, /*, # 는 주석이 아님
        text = '{"url": "http://example.com/path", "note": "/* not comment */ # not"}'
        self.assertEqual(
            _load_json_lazy(text),
            {"url": "http://example.com/path", "note": "/* not comment */ # not"},
        )

    def test_trailing_comma(self):
        self.assertEqual(_load_json_lazy('{"a": 1,}'), {"a": 1})
        self.assertEqual(_load_json_lazy('[1, 2, 3,]'), [1, 2, 3])

    def test_unquoted_keys(self):
        self.assertEqual(_load_json_lazy('{a: 1, b: 2}'), {"a": 1, "b": 2})

    def test_java_float_suffix(self):
        self.assertEqual(_load_json_lazy('{"x": 0.24f, "y": 5f}'), {"x": 0.24, "y": 5})

    def test_bareword_enum_value(self):
        # Java 상수 스타일 bareword 값
        result = _load_json_lazy('{"module": MILITARY, "tags": [STATIONS, NAV]}')
        self.assertEqual(result, {"module": "MILITARY", "tags": ["STATIONS", "NAV"]})

    def test_bareword_reserved_kept(self):
        # true/false/null 은 인용하지 않고 그대로 처리
        self.assertEqual(
            _load_json_lazy('{"a": true, "b": false, "c": null}'),
            {"a": True, "b": False, "c": None},
        )

    def test_string_with_colon_not_treated_as_key(self):
        # 회귀 테스트: 문자열 안 "producer: $x" 의 ':' 가 키 인용 패턴에 잘못 매칭되면 안 됨
        text = '{"desc": "revenue per producer: $commodities"}'
        self.assertEqual(
            _load_json_lazy(text),
            {"desc": "revenue per producer: $commodities"},
        )

    def test_combined_lenient_features(self):
        text = '''
        {
            // 코멘트
            speed: 0.5f,
            module: MILITARY,
            "tags": [STATIONS,],   # trailing comma
            "desc": "level: 5 or higher",
        }
        '''
        self.assertEqual(
            _load_json_lazy(text),
            {
                "speed": 0.5,
                "module": "MILITARY",
                "tags": ["STATIONS"],
                "desc": "level: 5 or higher",
            },
        )

    def test_split_string_segments_handles_escaped_quote(self):
        segs = _split_string_segments('{"a":"x\\"y","b":1}')
        # 문자열 세그먼트는 따옴표 포함, 비문자열은 따옴표 제외
        text_reconstructed = ''.join(s for _, s in segs)
        self.assertEqual(text_reconstructed, '{"a":"x\\"y","b":1}')


class TestNexerelinTranslation(BaseTestCase):
    """Nexerelin 모드 번역 적용 샘플 확인."""

    def test_nexerelin_data_has_korean(self):
        """agentConfig.json 또는 diplomacyConfig.json에 한국어 존재."""
        nex_dir = self.output_mods / 'Nexerelin'
        if not nex_dir.exists():
            self.skipTest("Nexerelin 모드 없음")

        candidates = [
            nex_dir / 'data/config/exerelin/agentConfig.json',
            nex_dir / 'data/config/exerelin/diplomacyConfig.json',
            nex_dir / 'data/strings/descriptions.json',
        ]

        for cand in candidates:
            if cand.exists():
                content = cand.read_text(encoding='utf-8', errors='replace')
                if any(0xAC00 <= ord(c) <= 0xD7A3 for c in content):
                    return  # 한 파일이라도 한국어 있으면 PASS

        self.fail(
            f"Nexerelin 번역 미적용 (확인 파일: {[c.name for c in candidates]})"
        )
