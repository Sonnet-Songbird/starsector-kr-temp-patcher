"""base_test.py - 공통 TestCase 기반 클래스"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
from patch_utils import load_config, load_exclusions, resolve_path


class BaseTestCase(unittest.TestCase):
    """config 및 경로를 세션 레벨로 공유하는 기반 TestCase."""

    @classmethod
    def setUpClass(cls):
        cls.cfg = load_config()
        cls.paths = cls.cfg['paths']
        cls.output_core = Path(resolve_path(cls.paths['output_core']))
        cls.output_mods = Path(resolve_path(cls.paths['output_mods']))
        cls.enabled_mods = [m for m in cls.cfg.get('mods', [])
                            if m.get('enabled', True)]
        bc, bs, bjs = load_exclusions(cls.paths)
        cls.blocked_classes = bc
        cls.blocked_strings = bs
        cls.blocked_jar_strings = bjs
        with open(resolve_path(cls.paths['translations']), encoding='utf-8') as f:
            cls.common_translations = json.load(f)
