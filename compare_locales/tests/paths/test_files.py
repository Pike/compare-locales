# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import
import unittest

from compare_locales.paths import (
    ProjectConfig
)
from . import (
    MockProjectFiles,
    MockTOMLParser,
)


class TestProjectPaths(unittest.TestCase):
    def test_l10n_path(self):
        cfg = ProjectConfig(None)
        cfg.add_environment(l10n_base='/tmp')
        cfg.locales.append('de')
        cfg.add_paths({
            'l10n': '{l10n_base}/{locale}/*'
        })
        mocks = [
            '/tmp/de/good.ftl',
            '/tmp/de/not/subdir/bad.ftl',
            '/tmp/fr/good.ftl',
            '/tmp/fr/not/subdir/bad.ftl',
        ]
        files = MockProjectFiles(mocks, 'de', [cfg])
        self.assertListEqual(
            list(files), [('/tmp/de/good.ftl', None, None, set())])
        self.assertTupleEqual(
            files.match('/tmp/de/something.ftl'),
            ('/tmp/de/something.ftl', None, None, set()))
        self.assertIsNone(files.match('/tmp/fr/something.ftl'))
        files = MockProjectFiles(mocks, 'de', [cfg], mergebase='merging')
        self.assertListEqual(
            list(files),
            [('/tmp/de/good.ftl', None, 'merging/de/good.ftl', set())])
        self.assertTupleEqual(
            files.match('/tmp/de/something.ftl'),
            ('/tmp/de/something.ftl', None, 'merging/de/something.ftl', set()))
        # 'fr' is not in the locale list, should return no files
        files = MockProjectFiles(mocks, 'fr', [cfg])
        self.assertListEqual(list(files), [])

    def test_single_reference_path(self):
        cfg = ProjectConfig(None)
        cfg.add_environment(l10n_base='/tmp/l10n')
        cfg.locales.append('de')
        cfg.add_paths({
            'l10n': '{l10n_base}/{locale}/good.ftl',
            'reference': '/tmp/reference/good.ftl'
        })
        mocks = [
            '/tmp/reference/good.ftl',
            '/tmp/reference/not/subdir/bad.ftl',
        ]
        files = MockProjectFiles(mocks, 'de', [cfg])
        self.assertListEqual(
            list(files),
            [
                ('/tmp/l10n/de/good.ftl', '/tmp/reference/good.ftl', None,
                 set()),
            ])

    def test_reference_path(self):
        cfg = ProjectConfig(None)
        cfg.add_environment(l10n_base='/tmp/l10n')
        cfg.locales.append('de')
        cfg.add_paths({
            'l10n': '{l10n_base}/{locale}/*',
            'reference': '/tmp/reference/*'
        })
        mocks = [
            '/tmp/l10n/de/good.ftl',
            '/tmp/l10n/de/not/subdir/bad.ftl',
            '/tmp/l10n/fr/good.ftl',
            '/tmp/l10n/fr/not/subdir/bad.ftl',
            '/tmp/reference/ref.ftl',
            '/tmp/reference/not/subdir/bad.ftl',
        ]
        files = MockProjectFiles(mocks, 'de', [cfg])
        self.assertListEqual(
            list(files),
            [
                ('/tmp/l10n/de/good.ftl', '/tmp/reference/good.ftl', None,
                 set()),
                ('/tmp/l10n/de/ref.ftl', '/tmp/reference/ref.ftl', None,
                 set()),
            ])
        self.assertTupleEqual(
            files.match('/tmp/l10n/de/good.ftl'),
            ('/tmp/l10n/de/good.ftl', '/tmp/reference/good.ftl', None,
             set()),
            )
        self.assertTupleEqual(
            files.match('/tmp/reference/good.ftl'),
            ('/tmp/l10n/de/good.ftl', '/tmp/reference/good.ftl', None,
             set()),
            )
        self.assertIsNone(files.match('/tmp/l10n/de/subdir/bad.ftl'))
        self.assertIsNone(files.match('/tmp/reference/subdir/bad.ftl'))
        files = MockProjectFiles(mocks, 'de', [cfg], mergebase='merging')
        self.assertListEqual(
            list(files),
            [
                ('/tmp/l10n/de/good.ftl', '/tmp/reference/good.ftl',
                 'merging/de/good.ftl', set()),
                ('/tmp/l10n/de/ref.ftl', '/tmp/reference/ref.ftl',
                 'merging/de/ref.ftl', set()),
            ])
        self.assertTupleEqual(
            files.match('/tmp/l10n/de/good.ftl'),
            ('/tmp/l10n/de/good.ftl', '/tmp/reference/good.ftl',
             'merging/de/good.ftl', set()),
            )
        self.assertTupleEqual(
            files.match('/tmp/reference/good.ftl'),
            ('/tmp/l10n/de/good.ftl', '/tmp/reference/good.ftl',
             'merging/de/good.ftl', set()),
            )
        # 'fr' is not in the locale list, should return no files
        files = MockProjectFiles(mocks, 'fr', [cfg])
        self.assertListEqual(list(files), [])

    def test_partial_l10n(self):
        cfg = ProjectConfig(None)
        cfg.locales.extend(['de', 'fr'])
        cfg.add_paths({
            'l10n': '/tmp/{locale}/major/*'
        }, {
            'l10n': '/tmp/{locale}/minor/*',
            'locales': ['de']
        })
        mocks = [
            '/tmp/de/major/good.ftl',
            '/tmp/de/major/not/subdir/bad.ftl',
            '/tmp/de/minor/good.ftl',
            '/tmp/fr/major/good.ftl',
            '/tmp/fr/major/not/subdir/bad.ftl',
            '/tmp/fr/minor/good.ftl',
        ]
        files = MockProjectFiles(mocks, 'de', [cfg])
        self.assertListEqual(
            list(files),
            [
                ('/tmp/de/major/good.ftl', None, None, set()),
                ('/tmp/de/minor/good.ftl', None, None, set()),
            ])
        self.assertTupleEqual(
            files.match('/tmp/de/major/some.ftl'),
            ('/tmp/de/major/some.ftl', None, None, set()))
        self.assertIsNone(files.match('/tmp/de/other/some.ftl'))
        # 'fr' is not in the locale list of minor, should only return major
        files = MockProjectFiles(mocks, 'fr', [cfg])
        self.assertListEqual(
            list(files),
            [
                ('/tmp/fr/major/good.ftl', None, None, set()),
            ])
        self.assertIsNone(files.match('/tmp/fr/minor/some.ftl'))

    def test_validation_mode(self):
        cfg = ProjectConfig(None)
        cfg.add_environment(l10n_base='/tmp/l10n')
        cfg.locales.append('de')
        cfg.add_paths({
            'l10n': '{l10n_base}/{locale}/*',
            'reference': '/tmp/reference/*'
        })
        mocks = [
            '/tmp/l10n/de/good.ftl',
            '/tmp/l10n/de/not/subdir/bad.ftl',
            '/tmp/l10n/fr/good.ftl',
            '/tmp/l10n/fr/not/subdir/bad.ftl',
            '/tmp/reference/ref.ftl',
            '/tmp/reference/not/subdir/bad.ftl',
        ]
        # `None` switches on validation mode
        files = MockProjectFiles(mocks, None, [cfg])
        self.assertListEqual(
            list(files),
            [
                ('/tmp/reference/ref.ftl', '/tmp/reference/ref.ftl', None,
                 set()),
            ])


class TestL10nMerge(unittest.TestCase):
    # need to go through TOMLParser, as that's handling most of the
    # environment
    def test_merge_paths(self):
        parser = MockTOMLParser({
            "base.toml":
            '''\
basepath = "."
locales = [
    "de",
]
[env]
    l = "{l10n_base}/{locale}/"
[[paths]]
    reference = "reference/*"
    l10n = "{l}*"
'''})
        cfg = parser.parse(
            '/tmp/base.toml',
            env={'l10n_base': '/tmp/l10n'}
        )
        mocks = [
            '/tmp/l10n/de/good.ftl',
            '/tmp/l10n/de/not/subdir/bad.ftl',
            '/tmp/l10n/fr/good.ftl',
            '/tmp/l10n/fr/not/subdir/bad.ftl',
            '/tmp/reference/ref.ftl',
            '/tmp/reference/not/subdir/bad.ftl',
        ]
        files = MockProjectFiles(mocks, 'de', [cfg], '/tmp/mergers')
        self.assertListEqual(
            list(files),
            [
                ('/tmp/l10n/de/good.ftl', '/tmp/reference/good.ftl',
                 '/tmp/mergers/de/good.ftl',
                 set()),
                ('/tmp/l10n/de/ref.ftl', '/tmp/reference/ref.ftl',
                 '/tmp/mergers/de/ref.ftl',
                 set()),
            ])
