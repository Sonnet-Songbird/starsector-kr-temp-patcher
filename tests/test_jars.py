"""test_jars.py - JAR 번역 적용 + 제외 규칙 + DRM 안전 검증"""

import json
import struct
import zipfile
from pathlib import Path

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


class TestClassPinpointTranslation(BaseTestCase):
    """class_trans.json 핀포인트 번역 기능 검증."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
        from patch_utils import resolve_path
        cls._resolve_path = staticmethod(resolve_path)

        class_trans_path = resolve_path(cls.paths.get('class_trans', ''))
        cls.class_trans = {}
        if class_trans_path:
            p = Path(class_trans_path)
            if p.exists():
                with open(p, encoding='utf-8') as f:
                    data = json.load(f)
                    # _comment 키 제외
                    cls.class_trans = {k: v for k, v in data.items()
                                       if not k.startswith('_')}

    def _find_jar_for_class(self, classname):
        """주어진 클래스가 있는 출력 JAR 경로를 반환 (없으면 None)."""
        for jar_path in [
            self.output_core / 'starfarer.api.jar',
            self.output_core / 'starfarer_obf.jar',
        ]:
            if not jar_path.exists():
                continue
            with zipfile.ZipFile(jar_path) as z:
                if classname in z.namelist():
                    return jar_path
        return None

    def _load_global_keys(self):
        """공통 + api + obf 전역 번역 사전의 원문 키 집합."""
        keys = set(self.common_translations)
        for trans_key in ('api_trans', 'obf_trans'):
            p_str = self._resolve_path(self.paths.get(trans_key, ''))
            if p_str:
                p = Path(p_str)
                if p.exists():
                    with open(p, encoding='utf-8') as f:
                        keys.update(json.load(f).keys())
        return keys

    def test_class_specific_applied(self):
        """class_trans.json 등록 클래스에 번역이 적용됐는지 확인."""
        if not self.class_trans:
            self.skipTest("class_trans.json 비어있거나 없음")

        failures = []
        skipped = []
        for classname, trans in self.class_trans.items():
            jar_path = self._find_jar_for_class(classname)
            if jar_path is None:
                skipped.append(classname)
                continue
            try:
                strings = get_string_literals(jar_path, classname)
            except Exception as e:
                failures.append(f"{classname}: 파싱 오류 ({e})")
                continue
            for src, tgt in trans.items():
                if tgt not in strings:
                    failures.append(
                        f"{classname}: '{src}' → '{tgt}' 번역 미적용"
                        f" (현재 strings: {sorted(s for s in strings if has_korean(s))[:3]})"
                    )

        if skipped:
            print(f"  [skip] 출력 JAR에 없는 클래스 {len(skipped)}개: {skipped}")
        self.assertFalse(
            failures,
            "class_trans 번역이 적용되지 않음:\n" + "\n".join(failures)
        )

    def test_class_specific_isolated(self):
        """class_trans 전용 원문이 비등록 클래스에서 번역되지 않았는지 확인."""
        if not self.class_trans:
            self.skipTest("class_trans.json 비어있거나 없음")

        global_keys = self._load_global_keys()
        registered_classes = set(self.class_trans.keys())

        # 전역 사전에 없는 class_trans 원문만 → 이것들만 핀포인트 의미 있음
        # {src: tgt} (첫 번째 등록 클래스 기준)
        pinpoint_trans = {}
        for trans in self.class_trans.values():
            for src, tgt in trans.items():
                if src not in global_keys and src not in pinpoint_trans:
                    pinpoint_trans[src] = tgt

        if not pinpoint_trans:
            self.skipTest(
                "class_trans의 모든 원문이 이미 전역 사전에 있음 — 격리 테스트 해당 없음"
            )

        # bak JAR에서 src가 있었는데 패치 후 없어졌으면 격리 실패
        from patch_utils import decode_java_utf8, parse_constant_pool
        game_core = Path(self._resolve_path(self.paths['game_core']))
        jar_pairs = [
            (game_core / 'starfarer.api.jar.bak', self.output_core / 'starfarer.api.jar'),
            (game_core / 'starfarer_obf.jar.bak', self.output_core / 'starfarer_obf.jar'),
        ]

        failures = []
        for bak_path, pat_path in jar_pairs:
            if not bak_path.exists() or not pat_path.exists():
                continue

            with zipfile.ZipFile(bak_path) as bak_z, zipfile.ZipFile(pat_path) as pat_z:
                all_classes = [n for n in bak_z.namelist()
                               if n.endswith('.class') and n not in registered_classes]
                for name in all_classes:
                    try:
                        bak_data = bak_z.read(name)
                        bak_entries, _ = parse_constant_pool(bak_data)
                        bak_str_idx = {struct.unpack_from('>H', v)[0]
                                       for tag, v in (e for e in bak_entries if e) if tag == 8}
                        bak_strings = set()
                        for i, entry in enumerate(bak_entries):
                            if entry and entry[0] == 1 and i in bak_str_idx:
                                try:
                                    bak_strings.add(decode_java_utf8(entry[1]))
                                except Exception:
                                    pass

                        for src in pinpoint_trans:
                            if src not in bak_strings:
                                continue
                            # bak에 src 있음 → 패치 후 없어졌으면 격리 실패
                            try:
                                pat_data = pat_z.read(name)
                                pat_entries, _ = parse_constant_pool(pat_data)
                                pat_str_idx = {struct.unpack_from('>H', v)[0]
                                               for tag, v in (e for e in pat_entries if e) if tag == 8}
                                pat_strings = set()
                                for i, entry in enumerate(pat_entries):
                                    if entry and entry[0] == 1 and i in pat_str_idx:
                                        try:
                                            pat_strings.add(decode_java_utf8(entry[1]))
                                        except Exception:
                                            pass
                                if src not in pat_strings:
                                    tgt = pinpoint_trans[src]
                                    failures.append(
                                        f"[격리 실패] {name}: '{src}' → '{tgt}' 적용됨 (비등록 클래스)"
                                    )
                            except Exception:
                                pass
                    except Exception:
                        pass

        self.assertFalse(
            failures,
            "class_trans 번역이 비등록 클래스에 누출됨:\n" + "\n".join(failures)
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
