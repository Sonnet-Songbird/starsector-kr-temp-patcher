"""test_jars.py - JAR 번역 적용 + 제외 규칙 + DRM 안전 검증"""

import zipfile

from base_test import BaseTestCase
from helpers import get_string_literals, has_korean, jar_has_korean


class TestJarTranslation(BaseTestCase):
    """핵심 JAR에 번역이 적용됐는지 확인."""

    def test_api_jar_has_korean(self):
        """api JAR에 한국어 문자열이 최소 1개 이상 존재."""
        jar = self.output_core / 'starfarer.api.jar'
        if not jar.exists():
            self.skipTest("starfarer.api.jar 없음")
        self.assertTrue(jar_has_korean(jar), "starfarer.api.jar 번역 미적용")

    def test_obf_jar_has_korean(self):
        """obf JAR에 한국어 문자열이 최소 1개 이상 존재."""
        jar = self.output_core / 'starfarer_obf.jar'
        if not jar.exists():
            self.skipTest("starfarer_obf.jar 없음")
        self.assertTrue(jar_has_korean(jar), "starfarer_obf.jar 번역 미적용")

    def test_api_jar_cr_plugin_korean(self):
        """CRPluginImpl에 '전투 준비도' 포함 (스킬 번역 확인)."""
        classname = 'com/fs/starfarer/api/impl/combat/CRPluginImpl.class'
        jar_path = self.output_core / 'starfarer.api.jar'
        if not jar_path.exists():
            self.skipTest("starfarer.api.jar 없음")
        with zipfile.ZipFile(jar_path) as z:
            if classname not in z.namelist():
                self.skipTest(f"{classname} 없음 (게임 버전 차이?)")
        strings = get_string_literals(jar_path, classname)
        ko = [s for s in strings if has_korean(s)]
        self.assertTrue(
            any('전투 준비도' in s for s in strings),
            f"CRPluginImpl에 '전투 준비도' 없음. 발견된 한국어: {ko[:5]}"
        )


class TestDrmSafety(BaseTestCase):
    """DRM 보호 문자열이 번역되지 않았는지 확인 (CRITICAL)."""

    def test_drm_strings_intact(self):
        """accidents/A.class의 anti-piracy 문자열이 원문 그대로 존재."""
        classname = 'com/fs/starfarer/campaign/accidents/A.class'
        jar_path = self.output_core / 'starfarer_obf.jar'
        if not jar_path.exists():
            self.skipTest("starfarer_obf.jar 없음")
        with zipfile.ZipFile(jar_path) as z:
            if classname not in z.namelist():
                self.skipTest(f"{classname} 없음")
        strings = get_string_literals(jar_path, classname)
        self.assertTrue(
            any('Nobody will ever pirate starfarer' in s for s in strings),
            "DRM 문자열이 번역됨 — 인증 실패 위험! accidents/A.class를 blocked_classes에 추가하세요."
        )


class TestExclusionRules(BaseTestCase):
    """blocked_classes가 올바르게 번역 제외됐는지 확인."""

    def test_blocked_classes_not_translated(self):
        """blocked_classes의 클래스에 한국어 번역이 없어야 함."""
        if not self.blocked_classes:
            self.skipTest("blocked_classes 비어있음")

        failures = []
        for jar_name, jar_path in [
            ('api', self.output_core / 'starfarer.api.jar'),
            ('obf', self.output_core / 'starfarer_obf.jar'),
        ]:
            if not jar_path.exists():
                continue
            with zipfile.ZipFile(jar_path) as z:
                all_names = set(z.namelist())
                for bc in self.blocked_classes:
                    if bc.endswith('/'):
                        to_check = [n for n in all_names
                                    if n.startswith(bc) and n.endswith('.class')]
                    else:
                        to_check = [bc] if bc in all_names else []

                    for classname in to_check:
                        try:
                            strings = get_string_literals(jar_path, classname)
                        except Exception:
                            continue
                        ko = [s for s in strings if has_korean(s)]
                        if ko:
                            failures.append(f"[{jar_name}] {classname}: {ko[:3]}")

        self.assertFalse(
            failures,
            "blocked_class에 한국어 번역 발견:\n" + "\n".join(failures)
        )


class TestNexerelinJar(BaseTestCase):
    """Nexerelin 모드 JAR 번역 + 세이브 호환성 확인."""

    def _jar_path(self):
        return self.output_mods / 'Nexerelin/jars/ExerelinCore.jar'

    def test_nexerelin_jar_has_korean(self):
        """ExerelinCore.jar에 한국어 번역 적용됨."""
        jar = self._jar_path()
        if not jar.exists():
            self.skipTest("Nexerelin JAR 없음")
        self.assertTrue(jar_has_korean(jar), "ExerelinCore.jar 번역 미적용")

    def test_nexerelin_xstream_intact(self):
        """XStreamConfig.class의 문자열이 번역 안 됨 (세이브 호환성)."""
        jar = self._jar_path()
        if not jar.exists():
            self.skipTest("Nexerelin JAR 없음")
        classname = 'exerelin/plugins/XStreamConfig.class'
        with zipfile.ZipFile(jar) as z:
            if classname not in z.namelist():
                self.skipTest(f"{classname} 없음")
        strings = get_string_literals(jar, classname)
        ko = [s for s in strings if has_korean(s)]
        self.assertFalse(
            ko,
            f"XStreamConfig가 번역됨 — 세이브 호환성 위험: {ko[:3]}"
        )
