# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest

from compare_locales.parser import Parser, Entity
from compare_locales.paths import ProjectConfig, File, ProjectFiles, Matcher
from compare_locales import mozpath


class TestMatcher(unittest.TestCase):

    def test_matcher(self):
        one = Matcher('foo/*')
        self.assertTrue(one.match('foo/baz'))
        self.assertFalse(one.match('foo/baz/qux'))
        other = Matcher('bar/*')
        self.assertTrue(other.match('bar/baz'))
        self.assertFalse(other.match('bar/baz/qux'))
        self.assertEqual(one.sub(other, 'foo/baz'), 'bar/baz')
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


class SetupMixin(object):
    def setUp(self):
        self.cfg = ProjectConfig()
        self.file = File(
            '/tmp/somedir/de/browser/one/two/file.ftl',
            'file.ftl',
            module='browser', locale='de')
        self.other_file = File(
            '/tmp/somedir/de/toolkit/two/one/file.ftl',
            'file.ftl',
            module='toolkit', locale='de')
        key_name = 'one_entity'
        ctx = Parser.Context(key_name)
        self.entity = Entity(ctx, lambda s: s, '', (0, len(key_name)), (), (),
                             (0, len(key_name)), (), ())


class TestConfigLegacy(SetupMixin, unittest.TestCase):

    def test_filter_empty(self):
        'Test that an empty config works'
        rv = self.cfg.filter(self.file)
        self.assertEqual(rv, None)
        rv = self.cfg.filter(self.file, entity=self.entity)
        self.assertEqual(rv, None)

    def test_filter_py_true(self):
        'Test filter.py just return bool(True)'
        def filter(mod, path, entity=None):
            return True
        self.cfg.set_filter_py(filter)
        with self.assertRaises(AssertionError):
            self.cfg.add_rules({})
        rv = self.cfg.filter(self.file)
        self.assertEqual(rv, 'error')
        rv = self.cfg.filter(self.file, entity=self.entity)
        self.assertEqual(rv, 'error')

    def test_filter_py_false(self):
        'Test filter.py just return bool(False)'
        def filter(mod, path, entity=None):
            return False
        self.cfg.set_filter_py(filter)
        with self.assertRaises(AssertionError):
            self.cfg.add_rules({})
        rv = self.cfg.filter(self.file)
        self.assertEqual(rv, 'ignore')
        rv = self.cfg.filter(self.file, entity=self.entity)
        self.assertEqual(rv, 'ignore')

    def test_filter_py_error(self):
        'Test filter.py just return str("error")'
        def filter(mod, path, entity=None):
            return 'error'
        self.cfg.set_filter_py(filter)
        with self.assertRaises(AssertionError):
            self.cfg.add_rules({})
        rv = self.cfg.filter(self.file)
        self.assertEqual(rv, 'error')
        rv = self.cfg.filter(self.file, entity=self.entity)
        self.assertEqual(rv, 'error')

    def test_filter_py_ignore(self):
        'Test filter.py just return str("ignore")'
        def filter(mod, path, entity=None):
            return 'ignore'
        self.cfg.set_filter_py(filter)
        with self.assertRaises(AssertionError):
            self.cfg.add_rules({})
        rv = self.cfg.filter(self.file)
        self.assertEqual(rv, 'ignore')
        rv = self.cfg.filter(self.file, entity=self.entity)
        self.assertEqual(rv, 'ignore')

    def test_filter_py_report(self):
        'Test filter.py just return str("report") and match to "warning"'
        def filter(mod, path, entity=None):
            return 'report'
        self.cfg.set_filter_py(filter)
        with self.assertRaises(AssertionError):
            self.cfg.add_rules({})
        rv = self.cfg.filter(self.file)
        self.assertEqual(rv, 'warning')
        rv = self.cfg.filter(self.file, entity=self.entity)
        self.assertEqual(rv, 'warning')

    def test_filter_py_module(self):
        'Test filter.py to return str("error") for browser or "ignore"'
        def filter(mod, path, entity=None):
            return 'error' if mod == 'browser' else 'ignore'
        self.cfg.set_filter_py(filter)
        with self.assertRaises(AssertionError):
            self.cfg.add_rules({})
        rv = self.cfg.filter(self.file)
        self.assertEqual(rv, 'error')
        rv = self.cfg.filter(self.file, entity=self.entity)
        self.assertEqual(rv, 'error')
        rv = self.cfg.filter(self.other_file)
        self.assertEqual(rv, 'ignore')
        rv = self.cfg.filter(self.other_file, entity=self.entity)
        self.assertEqual(rv, 'ignore')


class TestConfigRules(SetupMixin, unittest.TestCase):

    def test_single_file_rule(self):
        'Test a single rule for just a single file, no key'
        self.cfg.add_rules({
            'path': '/tmp/somedir/{locale}/browser/one/two/file.ftl',
            'action': 'ignore'
        })
        rv = self.cfg.filter(self.file)
        self.assertEqual(rv, 'ignore')
        rv = self.cfg.filter(self.file, self.entity)
        self.assertEqual(rv, None)
        rv = self.cfg.filter(self.other_file)
        self.assertEqual(rv, None)
        rv = self.cfg.filter(self.other_file, self.entity)
        self.assertEqual(rv, None)

    def test_single_key_rule(self):
        'Test a single rule with file and key'
        self.cfg.add_rules({
            'path': '/tmp/somedir/{locale}/browser/one/two/file.ftl',
            'key': 'one_entity',
            'action': 'ignore'
        })
        rv = self.cfg.filter(self.file)
        self.assertEqual(rv, None)
        rv = self.cfg.filter(self.file, self.entity)
        self.assertEqual(rv, 'ignore')
        rv = self.cfg.filter(self.other_file)
        self.assertEqual(rv, None)
        rv = self.cfg.filter(self.other_file, self.entity)
        self.assertEqual(rv, None)

    def test_single_non_matching_key_rule(self):
        'Test a single key rule with regex special chars that should not match'
        self.cfg.add_rules({
            'path': '/tmp/somedir/{locale}/browser/one/two/file.ftl',
            'key': '.ne_entit.',
            'action': 'ignore'
        })
        rv = self.cfg.filter(self.file, self.entity)
        self.assertEqual(rv, None)

    def test_single_matching_re_key_rule(self):
        'Test a single key with regular expression'
        self.cfg.add_rules({
            'path': '/tmp/somedir/{locale}/browser/one/two/file.ftl',
            'key': 're:.ne_entit.$',
            'action': 'ignore'
        })
        rv = self.cfg.filter(self.file, self.entity)
        self.assertEqual(rv, 'ignore')

    def test_double_file_rule(self):
        'Test path shortcut, one for each of our files'
        self.cfg.add_rules({
            'path': [
                '/tmp/somedir/{locale}/browser/one/two/file.ftl',
                '/tmp/somedir/{locale}/toolkit/two/one/file.ftl',
            ],
            'action': 'ignore'
        })
        rv = self.cfg.filter(self.file)
        self.assertEqual(rv, 'ignore')
        rv = self.cfg.filter(self.other_file)
        self.assertEqual(rv, 'ignore')

    def test_double_file_key_rule(self):
        'Test path and key shortcut, one key matching, one not'
        self.cfg.add_rules({
            'path': [
                '/tmp/somedir/{locale}/browser/one/two/file.ftl',
                '/tmp/somedir/{locale}/toolkit/two/one/file.ftl',
            ],
            'key': [
                'one_entity',
                'other_entity',
            ],
            'action': 'ignore'
        })
        rv = self.cfg.filter(self.file)
        self.assertEqual(rv, None)
        rv = self.cfg.filter(self.file, self.entity)
        self.assertEqual(rv, 'ignore')
        rv = self.cfg.filter(self.other_file)
        self.assertEqual(rv, None)
        rv = self.cfg.filter(self.other_file, self.entity)
        self.assertEqual(rv, 'ignore')

    def test_single_wildcard_rule(self):
        'Test single wildcard'
        self.cfg.add_rules({
            'path': [
                '/tmp/somedir/{locale}/browser/one/*/*',
            ],
            'action': 'ignore'
        })
        rv = self.cfg.filter(self.file)
        self.assertEqual(rv, 'ignore')
        rv = self.cfg.filter(self.other_file)
        self.assertEqual(rv, None)

    def test_double_wildcard_rule(self):
        'Test double wildcard'
        self.cfg.add_rules({
            'path': [
                '/tmp/somedir/{locale}/**',
            ],
            'action': 'ignore'
        })
        rv = self.cfg.filter(self.file)
        self.assertEqual(rv, 'ignore')
        rv = self.cfg.filter(self.other_file)
        self.assertEqual(rv, 'ignore')


class MockProjectFiles(ProjectFiles):
    def __init__(self, mocks, locale, *projects):
        super(MockProjectFiles, self).__init__(locale, *projects)
        self.mocks = mocks

    def _files(self, base):
        for path in self.mocks.get(base, []):
            yield mozpath.join(base, path)


class TestProjectPaths(unittest.TestCase):
    def test_l10n_path(self):
        cfg = ProjectConfig()
        cfg.locales.append('de')
        cfg.add_paths({
            'l10n': '/tmp/{locale}/*'
        })
        mocks = {
            '/tmp/de/': [
                'good.ftl',
                'not/subdir/bad.ftl'
            ],
            '/tmp/fr/': [
                'good.ftl',
                'not/subdir/bad.ftl'
            ],
        }
        files = MockProjectFiles(mocks, 'de', cfg)
        self.assertListEqual(list(files), [('/tmp/de/good.ftl', None, set())])
        # 'fr' is not in the locale list, should return no files
        files = MockProjectFiles(mocks, 'fr', cfg)
        self.assertListEqual(list(files), [])

    def test_reference_path(self):
        cfg = ProjectConfig()
        cfg.locales.append('de')
        cfg.add_paths({
            'l10n': '/tmp/l10n/{locale}/*',
            'reference': '/tmp/reference/*'
        })
        mocks = {
            '/tmp/l10n/de/': [
                'good.ftl',
                'not/subdir/bad.ftl'
            ],
            '/tmp/l10n/fr/': [
                'good.ftl',
                'not/subdir/bad.ftl'
            ],
            '/tmp/reference/': [
                'ref.ftl',
                'not/subdir/bad.ftl'
            ],
        }
        files = MockProjectFiles(mocks, 'de', cfg)
        self.assertListEqual(
            list(files),
            [
                ('/tmp/l10n/de/good.ftl', '/tmp/reference/good.ftl', set()),
                ('/tmp/l10n/de/ref.ftl', '/tmp/reference/ref.ftl', set()),
            ])
        # 'fr' is not in the locale list, should return no files
        files = MockProjectFiles(mocks, 'fr', cfg)
        self.assertListEqual(list(files), [])
