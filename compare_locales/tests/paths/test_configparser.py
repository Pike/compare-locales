# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import, unicode_literals
import unittest

from . import MockTOMLParser
from compare_locales.paths.project import ProjectConfig


class TestConfigParser(unittest.TestCase):
    def test_imports(self):
        parser = MockTOMLParser({
            "root.toml": """
basepath = "."
[env]
  o = "toolkit"
[[includes]]
  path = "{o}/other.toml"
""",
            "other.toml": """
basepath = "."
"""
        })
        config = parser.parse("root.toml")
        self.assertIsInstance(config, ProjectConfig)
