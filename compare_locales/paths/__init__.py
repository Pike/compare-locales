# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import
import errno
import logging
import warnings
from compare_locales import mozpath
from .files import ProjectFiles, REFERENCE_LOCALE
from .ini import (
    L10nConfigParser, SourceTreeConfigParser,
    EnumerateApp, EnumerateSourceTreeApp,
)
from .matcher import Matcher
from .project import ProjectConfig
import pytoml as toml
import six


__all__ = [
    'Matcher',
    'ProjectConfig',
    'L10nConfigParser', 'SourceTreeConfigParser',
    'EnumerateApp', 'EnumerateSourceTreeApp',
    'ProjectFiles', 'REFERENCE_LOCALE',
]


class ConfigNotFound(EnvironmentError):
    def __init__(self, path):
        super(ConfigNotFound, self).__init__(
            errno.ENOENT,
            'Configuration file not found',
            path)


class TOMLParser(object):
    @classmethod
    def parse(cls, path, env=None, ignore_missing_includes=False):
        parser = cls(path, env=env,
                     ignore_missing_includes=ignore_missing_includes)
        parser.load()
        parser.processEnv()
        parser.processPaths()
        parser.processFilters()
        parser.processIncludes()
        parser.processLocales()
        return parser.asConfig()

    def __init__(self, path, env=None, ignore_missing_includes=False):
        self.path = path
        self.env = env if env is not None else {}
        self.ignore_missing_includes = ignore_missing_includes
        self.data = None
        self.pc = ProjectConfig()
        self.pc.PATH = path

    def load(self):
        try:
            with open(self.path, 'rb') as fin:
                self.data = toml.load(fin)
        except (toml.TomlError, IOError):
            raise ConfigNotFound(self.path)

    def processEnv(self):
        assert self.data is not None
        self.pc.add_environment(**self.data.get('env', {}))

    def processLocales(self):
        assert self.data is not None
        if 'locales' in self.data:
            self.pc.set_locales(self.data['locales'])

    def processPaths(self):
        assert self.data is not None
        for data in self.data.get('paths', []):
            l10n = data['l10n']
            if not l10n.startswith('{'):
                # l10n isn't relative to a variable, expand
                l10n = self.resolvepath(l10n)
            paths = {
                "l10n": l10n,
            }
            if 'locales' in data:
                paths['locales'] = data['locales']
            if 'reference' in data:
                paths['reference'] = self.resolvepath(data['reference'])
            self.pc.add_paths(paths)

    def processFilters(self):
        assert self.data is not None
        for data in self.data.get('filters', []):
            paths = data['path']
            if isinstance(paths, six.string_types):
                paths = [paths]
            # expand if path isn't relative to a variable
            paths = [
                self.resolvepath(path) if not path.startswith('{')
                else path
                for path in paths
            ]
            rule = {
                "path": paths,
                "action": data['action']
            }
            if 'key' in data:
                rule['key'] = data['key']
            self.pc.add_rules(rule)

    def processIncludes(self):
        assert self.data is not None
        if 'includes' not in self.data:
            return
        for include in self.data['includes']:
            p = include['path']
            p = self.resolvepath(p)
            try:
                child = self.parse(
                    p, env=self.env,
                    ignore_missing_includes=self.ignore_missing_includes
                )
            except ConfigNotFound as e:
                if not self.ignore_missing_includes:
                    raise
                (logging
                    .getLogger('compare-locales.io')
                    .error('%s: %s', e.strerror, e.filename))
                continue
            self.pc.add_child(child)

    def resolvepath(self, path):
        path = self.pc.expand(path, env=self.env)
        path = mozpath.join(
            mozpath.dirname(self.path),
            self.data.get('basepath', '.'),
            path)
        return mozpath.normpath(path)

    def asConfig(self):
        return self.pc


class File(object):

    def __init__(self, fullpath, file, module=None, locale=None):
        self.fullpath = fullpath
        self.file = file
        self.module = module
        self.locale = locale
        pass

    def getContents(self):
        # open with universal line ending support and read
        # ignore universal newlines deprecation
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with open(self.fullpath, 'rbU') as f:
                return f.read()

    @property
    def localpath(self):
        f = self.file
        if self.module:
            f = mozpath.join(self.module, f)
        return f

    def __hash__(self):
        return hash(self.localpath)

    def __str__(self):
        return self.fullpath

    def __eq__(self, other):
        if not isinstance(other, File):
            return False
        return vars(self) == vars(other)

    def __ne__(self, other):
        return not (self == other)
