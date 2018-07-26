# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import
import unittest

from compare_locales.paths import Matcher


class TestMatcher(unittest.TestCase):

    def test_matcher(self):
        one = Matcher('foo/*')
        self.assertTrue(one.match('foo/baz'))
        self.assertFalse(one.match('foo/baz/qux'))
        other = Matcher('bar/*')
        self.assertTrue(other.match('bar/baz'))
        self.assertFalse(other.match('bar/baz/qux'))
        self.assertEqual(one.sub(other, 'foo/baz'), 'bar/baz')
        self.assertIsNone(one.sub(other, 'bar/baz'))
        one = Matcher('foo/**')
        self.assertTrue(one.match('foo/baz'))
        self.assertTrue(one.match('foo/baz/qux'))
        other = Matcher('bar/**')
        self.assertTrue(other.match('bar/baz'))
        self.assertTrue(other.match('bar/baz/qux'))
        self.assertEqual(one.sub(other, 'foo/baz'), 'bar/baz')
        self.assertEqual(one.sub(other, 'foo/baz/qux'), 'bar/baz/qux')
        one = Matcher('foo/*/one/**')
        self.assertTrue(one.match('foo/baz/one/qux'))
        self.assertFalse(one.match('foo/baz/bez/one/qux'))
        other = Matcher('bar/*/other/**')
        self.assertTrue(other.match('bar/baz/other/qux'))
        self.assertFalse(other.match('bar/baz/bez/other/qux'))
        self.assertEqual(one.sub(other, 'foo/baz/one/qux'),
                         'bar/baz/other/qux')
        self.assertEqual(one.sub(other, 'foo/baz/one/qux/zzz'),
                         'bar/baz/other/qux/zzz')
        self.assertIsNone(one.sub(other, 'foo/baz/bez/one/qux'))
        one = Matcher('foo/**/bar/**')
        self.assertTrue(one.match('foo/bar/baz.qux'))
        self.assertTrue(one.match('foo/tender/bar/baz.qux'))
        self.assertFalse(one.match('foo/nobar/baz.qux'))
        self.assertFalse(one.match('foo/tender/bar'))

    def test_prefix(self):
        self.assertEqual(
            Matcher('foo/bar.file').prefix, 'foo/bar.file'
        )
        self.assertEqual(
            Matcher('foo/*').prefix, 'foo/'
        )
        self.assertEqual(
            Matcher('foo/**').prefix, 'foo'
        )
        self.assertEqual(
            Matcher('foo/*/bar').prefix, 'foo/'
        )
        self.assertEqual(
            Matcher('foo/**/bar').prefix, 'foo'
        )

    def test_variables(self):
        self.assertDictEqual(
            Matcher('foo/bar.file').match('foo/bar.file').groupdict(),
            {}
        )
        self.assertDictEqual(
            Matcher('{path}/bar.file').match('foo/bar.file').groupdict(),
            {
                'path': 'foo'
            }
        )
        self.assertDictEqual(
            Matcher('{ path }/bar.file').match('foo/bar.file').groupdict(),
            {
                'path': 'foo'
            }
        )
