# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import
import six
import unittest

from compare_locales.paths.matcher import Matcher, ANDROID_STANDARD_MAP


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
            Matcher('foo/**').prefix, 'foo/'
        )
        self.assertEqual(
            Matcher('foo/*/bar').prefix, 'foo/'
        )
        self.assertEqual(
            Matcher('foo/**/bar').prefix, 'foo/'
        )
        self.assertEqual(
            Matcher('foo/**/bar/*').prefix, 'foo/'
        )
        self.assertEqual(
            Matcher('foo/{v}/bar', {'v': 'expanded'}).prefix,
            'foo/expanded/bar'
        )
        self.assertEqual(
            Matcher('foo/{v}/*/bar', {'v': 'expanded'}).prefix,
            'foo/expanded/'
        )

    def test_variables(self):
        self.assertDictEqual(
            Matcher('foo/bar.file').match('foo/bar.file'),
            {}
        )
        self.assertDictEqual(
            Matcher('{path}/bar.file').match('foo/bar.file'),
            {
                'path': 'foo'
            }
        )
        self.assertDictEqual(
            Matcher('{ path }/bar.file').match('foo/bar.file'),
            {
                'path': 'foo'
            }
        )
        self.assertIsNone(
            Matcher('{ var }/foopy/{ var }/bears')
            .match('one/foopy/other/bears')
        )
        self.assertDictEqual(
            Matcher('{ var }/foopy/{ var }/bears')
            .match('same_value/foopy/same_value/bears'),
            {
                'var': 'same_value'
            }
        )
        self.assertIsNone(
            Matcher('{ var }/foopy/bears', {'var': 'other'})
            .match('one/foopy/bears')
        )
        self.assertDictEqual(
            Matcher('{ var }/foopy/bears', {'var': 'one'})
            .match('one/foopy/bears'),
            {
                'var': 'one'
            }
        )
        self.assertDictEqual(
            Matcher('{one}/{two}/something', {
                'one': 'some/segment',
                'two': 'with/a/lot/of'
            }).match('some/segment/with/a/lot/of/something'),
            {
                'one': 'some/segment',
                'two': 'with/a/lot/of'
            }
        )

    def test_variables_sub(self):
        one = Matcher('{base}/{loc}/*', {'base': 'ONE_BASE'})
        other = Matcher('{base}/somewhere/*', {'base': 'OTHER_BASE'})
        self.assertEqual(
            one.sub(other, 'ONE_BASE/ab-CD/special'),
            'OTHER_BASE/somewhere/special'
        )

    def test_copy(self):
        one = Matcher('{base}/{loc}/*', {
            'base': 'ONE_BASE',
            'generic': 'keep'
        })
        other = Matcher(one, {'base': 'OTHER_BASE'})
        self.assertEqual(
            one.sub(other, 'ONE_BASE/ab-CD/special'),
            'OTHER_BASE/ab-CD/special'
        )
        self.assertDictEqual(
            one.env,
            {
                'base': ['ONE_BASE'],
                'generic': ['keep']
            }
        )
        self.assertDictEqual(
            other.env,
            {
                'base': ['OTHER_BASE'],
                'generic': ['keep']
            }
        )


class TestAndroid(unittest.TestCase):
    '''special case handling for `android_locale` to handle the funky
    locale codes in Android apps
    '''
    def test_match(self):
        # test matches as well as groupdict aliasing.
        one = Matcher('values-{android_locale}/strings.xml')
        self.assertEqual(
            one.match('values-de/strings.xml'),
            {
                'android_locale': 'de',
                'locale': 'de'
            }
        )
        self.assertEqual(
            one.match('values-de-rDE/strings.xml'),
            {
                'android_locale': 'de-rDE',
                'locale': 'de-DE'
            }
        )
        self.assertEqual(
            one.match('values-b+sr+Latn/strings.xml'),
            {
                'android_locale': 'b+sr+Latn',
                'locale': 'sr-Latn'
            }
        )
        self.assertEqual(
            one.with_env(
                {'locale': 'de'}
            ).match('values-de/strings.xml'),
            {
                'android_locale': 'de',
                'locale': 'de'
            }
        )
        self.assertEqual(
            one.with_env(
                {'locale': 'de-DE'}
            ).match('values-de-rDE/strings.xml'),
            {
                'android_locale': 'de-rDE',
                'locale': 'de-DE'
            }
        )
        self.assertEqual(
            one.with_env(
                {'locale': 'sr-Latn'}
            ).match('values-b+sr+Latn/strings.xml'),
            {
                'android_locale': 'b+sr+Latn',
                'locale': 'sr-Latn'
            }
        )

    def test_repeat(self):
        self.assertEqual(
            Matcher('{android_locale}/{android_locale}').match(
                'b+sr+Latn/b+sr+Latn'
            ),
            {
                'android_locale': 'b+sr+Latn',
                'locale': 'sr-Latn'
            }
        )
        self.assertEqual(
            Matcher(
                '{android_locale}/{android_locale}',
                env={'locale': 'sr-Latn'}
            ).match(
                'b+sr+Latn/b+sr+Latn'
            ),
            {
                'android_locale': 'b+sr+Latn',
                'locale': 'sr-Latn'
            }
        )

    def test_mismatch(self):
        # test failed matches
        one = Matcher('values-{android_locale}/strings.xml')
        self.assertIsNone(
            one.with_env({'locale': 'de'}).match(
                'values-fr.xml'
            )
        )
        self.assertIsNone(
            one.with_env({'locale': 'de-DE'}).match(
                'values-de-DE.xml'
            )
        )
        self.assertIsNone(
            one.with_env({'locale': 'sr-Latn'}).match(
                'values-sr-Latn.xml'
            )
        )
        self.assertIsNone(
            Matcher('{android_locale}/{android_locale}').match(
                'b+sr+Latn/de-rDE'
            )
        )

    def test_prefix(self):
        one = Matcher('values-{android_locale}/strings.xml')
        self.assertEqual(
            one.with_env({'locale': 'de'}).prefix,
            'values-de/strings.xml'
        )
        self.assertEqual(
            one.with_env({'locale': 'de-DE'}).prefix,
            'values-de-rDE/strings.xml'
        )
        self.assertEqual(
            one.with_env({'locale': 'sr-Latn'}).prefix,
            'values-b+sr+Latn/strings.xml'
        )

    def test_aliases(self):
        # test legacy locale code mapping
        # he <-> iw, id <-> in, yi <-> ji
        one = Matcher('values-{android_locale}/strings.xml')
        for legacy, standard in six.iteritems(ANDROID_STANDARD_MAP):
            self.assertDictEqual(
                one.match('values-{}/strings.xml'.format(legacy)),
                {
                    'android_locale': legacy,
                    'locale': standard
                }
            )
            self.assertEqual(
                one.with_env({'locale': standard}).prefix,
                'values-{}/strings.xml'.format(legacy)
            )


class TestRootedMatcher(unittest.TestCase):
    def test_root_path(self):
        one = Matcher('some/path', root='/rooted/dir')
        self.assertIsNone(one.match('some/path'))
        self.assertIsNotNone(one.match('/rooted/dir/some/path'))

    def test_copy(self):
        one = Matcher('some/path', root='/rooted/dir')
        other = Matcher(one, root='/different-rooted/dir')
        self.assertIsNone(other.match('some/path'))
        self.assertIsNone(other.match('/rooted/dir/some/path'))
        self.assertIsNotNone(other.match('/different-rooted/dir/some/path'))

    def test_rooted(self):
        one = Matcher('/rooted/full/path', root='/different-root')
        self.assertIsNone(one.match('/different-root/rooted/full/path'))
        self.assertIsNotNone(one.match('/rooted/full/path'))

    def test_variable(self):
        one = Matcher(
            '{var}/path',
            env={'var': 'relative-dir'},
            root='/rooted/dir'
        )
        self.assertIsNone(one.match('relative-dir/path'))
        self.assertIsNotNone(one.match('/rooted/dir/relative-dir/path'))
        other = Matcher(one, env={'var': '/different/rooted-dir'})
        self.assertIsNone(other.match('/rooted/dir/relative-dir/path'))
        self.assertIsNotNone(other.match('/different/rooted-dir/path'))
