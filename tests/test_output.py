"""test_output.py - 빌드 산출물 존재 여부 + ZIP 무결성 검사"""

import zipfile

from base_test import BaseTestCase


class TestOutputFiles(BaseTestCase):
    """output/ 디렉토리에 필요한 파일이 모두 생성됐는지 확인."""

    def test_api_jar_exists(self):
        """starfarer.api.jar가 output_core에 존재."""
        self.assertTrue(
            (self.output_core / 'starfarer.api.jar').exists(),
            f"starfarer.api.jar 없음: {self.output_core}"
        )

    def test_obf_jar_exists(self):
        """starfarer_obf.jar가 output_core에 존재."""
        self.assertTrue(
            (self.output_core / 'starfarer_obf.jar').exists(),
            f"starfarer_obf.jar 없음: {self.output_core}"
        )

    def test_jars_valid_zip(self):
        """두 핵심 JAR이 모두 유효한 ZIP 아카이브."""
        for jar in ['starfarer.api.jar', 'starfarer_obf.jar']:
            with self.subTest(jar=jar):
                path = self.output_core / jar
                if not path.exists():
                    self.skipTest(f"{jar} 없음 — test_*_jar_exists에서 먼저 실패")
                with zipfile.ZipFile(path) as z:
                    bad = z.testzip()
                self.assertIsNone(bad, f"{jar} ZIP 오류: {bad}")

    def test_output_mod_dirs_exist(self):
        """활성화된 모드 디렉토리가 output_mods에 존재."""
        for m in self.enabled_mods:
            with self.subTest(mod=m['id']):
                self.assertTrue(
                    (self.output_mods / m['id']).is_dir(),
                    f"모드 디렉토리 없음: {m['id']}"
                )

    def test_mod_jars_exist(self):
        """mod_jar 설정이 있는 모드의 JAR이 output_mods에 존재."""
        for m in self.enabled_mods:
            jar_rel = m.get('mod_jar')
            if not jar_rel:
                continue
            jar_list = [jar_rel] if isinstance(jar_rel, str) else list(jar_rel)
            for j in jar_list:
                with self.subTest(mod=m['id'], jar=j):
                    self.assertTrue(
                        (self.output_mods / m['id'] / j).exists(),
                        f"모드 JAR 없음: {m['id']}/{j}"
                    )
