# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import

from compare_locales.paths import (
    ProjectConfig, File, ProjectFiles, TOMLParser
)
from compare_locales import mozpath
import pytoml as toml


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


class MockProjectFiles(ProjectFiles):
    def __init__(self, mocks, locale, projects, mergebase=None):
        (super(MockProjectFiles, self)
            .__init__(locale, projects, mergebase=mergebase))
        self.mocks = mocks

    def _files(self, matcher):
        base = matcher.prefix
        for path in self.mocks.get(base, []):
            p = mozpath.join(base, path)
            if matcher.match(p):
                yield p


class MockTOMLParser(TOMLParser):
    def __init__(self, path_data, env=None, ignore_missing_includes=False):
        # mock, use the path as data. Yeah, not nice
        super(MockTOMLParser, self).__init__(
            '/tmp/base.toml',
            env=env, ignore_missing_includes=ignore_missing_includes
        )
        self.data = toml.loads(path_data)

    def load(self):
        # we mocked this
        pass
