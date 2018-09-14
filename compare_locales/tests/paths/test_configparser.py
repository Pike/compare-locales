# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import, unicode_literals
import unittest

import pytoml as toml
from compare_locales import mozpath
from compare_locales.paths.configparser import TOMLParser
from compare_locales.paths.project import ProjectConfig


def parsers_for(data):
    class MockTOMLParser(TOMLParser):
        def load(self, ctx):
            p = mozpath.basename(ctx.path)
            ctx.data = toml.loads(data[p])
    return MockTOMLParser


class TestConfigParser(unittest.TestCase):
    def test_imports(self):
        Parser = parsers_for({
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
        config = Parser.parse("root.toml")
        self.assertIsInstance(config, ProjectConfig)
