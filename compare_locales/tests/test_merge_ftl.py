# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
from compare_locales.merge import merge_channels


class TestMergeFluent(unittest.TestCase):
    name = "foo.ftl"

    def test_no_support_for_now(self):
        channels = (b"""
foo = Foo 1
bar = Bar 1
""", b"""
foo = Foo 2
bar = Bar 2
""")
        pattern = "Fluent files \(.ftl\) are not supported \(bug 1399055\)."
        with self.assertRaisesRegexp(Exception, pattern):
            merge_channels(self.name, *channels)
