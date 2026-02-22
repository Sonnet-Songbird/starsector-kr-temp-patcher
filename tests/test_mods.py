"""test_mods.py - 모드 파일 유효성 + 번역 적용 샘플 검증"""

import csv
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
from build_mods import _load_json_lazy

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
