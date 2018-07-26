# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import
import os
import errno
import logging
import warnings
from compare_locales import mozpath
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

]

REFERENCE_LOCALE = 'en-x-moz-reference'


class ProjectFiles(object):
    '''Iterable object to get all files and tests for a locale and a
    list of ProjectConfigs.

    If the given locale is None, iterate over reference files as
    both reference and locale for a reference self-test.
    '''
    def __init__(self, locale, projects, mergebase=None):
        self.locale = locale
        self.matchers = []
        self.mergebase = mergebase
        configs = []
        for project in projects:
            configs.extend(project.configs)
        for pc in configs:
            if locale and locale not in pc.locales:
                continue
            for paths in pc.paths:
                if (
                    locale and
                    'locales' in paths and
                    locale not in paths['locales']
                ):
                    continue
                m = {
                    'l10n': paths['l10n']({
                        "locale": locale or REFERENCE_LOCALE
                    }),
                    'module': paths.get('module'),
                }
                if 'reference' in paths:
                    m['reference'] = paths['reference']
                if self.mergebase is not None:
                    m['merge'] = paths['l10n']({
                        "locale": locale,
                        "l10n_base": self.mergebase
                    })
                m['test'] = set(paths.get('test', []))
                if 'locales' in paths:
                    m['locales'] = paths['locales'][:]
                self.matchers.append(m)
        self.matchers.reverse()  # we always iterate last first
        # Remove duplicate patterns, comparing each matcher
        # against all other matchers.
        # Avoid n^2 comparisons by only scanning the upper triangle
        # of a n x n matrix of all possible combinations.
        # Using enumerate and keeping track of indexes, as we can't
        # modify the list while iterating over it.
        drops = set()  # duplicate matchers to remove
        for i, m in enumerate(self.matchers[:-1]):
            if i in drops:
                continue  # we're dropping this anyway, don't search again
            for i_, m_ in enumerate(self.matchers[(i+1):]):
                if (mozpath.realpath(m['l10n'].prefix) !=
                        mozpath.realpath(m_['l10n'].prefix)):
                    # ok, not the same thing, continue
                    continue
                # check that we're comparing the same thing
                if 'reference' in m:
                    if (mozpath.realpath(m['reference'].prefix) !=
                            mozpath.realpath(m_.get('reference').prefix)):
                        raise RuntimeError('Mismatch in reference for ' +
                                           mozpath.realpath(m['l10n'].prefix))
                drops.add(i_ + i + 1)
                m['test'] |= m_['test']
        drops = sorted(drops, reverse=True)
        for i in drops:
            del self.matchers[i]

    def __iter__(self):
        # The iteration is pretty different when we iterate over
        # a localization vs over the reference. We do that latter
        # when running in validation mode.
        inner = self.iter_locale() if self.locale else self.iter_reference()
        for t in inner:
            yield t

    def iter_locale(self):
        '''Iterate over locale files.'''
        known = {}
        for matchers in self.matchers:
            matcher = matchers['l10n']
            for path in self._files(matcher):
                if path not in known:
                    known[path] = {'test': matchers.get('test')}
                    if 'reference' in matchers:
                        known[path]['reference'] = matcher.sub(
                            matchers['reference'], path)
                    if 'merge' in matchers:
                        known[path]['merge'] = matcher.sub(
                            matchers['merge'], path)
            if 'reference' not in matchers:
                continue
            matcher = matchers['reference']
            for path in self._files(matcher):
                l10npath = matcher.sub(matchers['l10n'], path)
                if l10npath not in known:
                    known[l10npath] = {
                        'reference': path,
                        'test': matchers.get('test')
                    }
                    if 'merge' in matchers:
                        known[l10npath]['merge'] = \
                            matcher.sub(matchers['merge'], path)
        for path, d in sorted(known.items()):
            yield (path, d.get('reference'), d.get('merge'), d['test'])

    def iter_reference(self):
        '''Iterate over reference files.'''
        known = {}
        for matchers in self.matchers:
            if 'reference' not in matchers:
                continue
            matcher = matchers['reference']
            for path in self._files(matcher):
                refpath = matcher.sub(matchers['reference'], path)
                if refpath not in known:
                    known[refpath] = {
                        'reference': path,
                        'test': matchers.get('test')
                    }
        for path, d in sorted(known.items()):
            yield (path, d.get('reference'), None, d['test'])

    def _files(self, matcher):
        '''Base implementation of getting all files in a hierarchy
        using the file system.
        Subclasses might replace this method to support different IO
        patterns.
        '''
        base = matcher.prefix
        if os.path.isfile(base):
            if matcher.match(base):
                yield base
            return
        for d, dirs, files in os.walk(base):
            for f in files:
                p = mozpath.join(d, f)
                if matcher.match(p):
                    yield p

    def match(self, path):
        '''Return the tuple of l10n_path, reference, mergepath, tests
        if the given path matches any config, otherwise None.

        This routine doesn't check that the files actually exist.
        '''
        for matchers in self.matchers:
            matcher = matchers['l10n']
            if matcher.match(path):
                ref = merge = None
                if 'reference' in matchers:
                    ref = matcher.sub(matchers['reference'], path)
                if 'merge' in matchers:
                    merge = matcher.sub(matchers['merge'], path)
                return path, ref, merge, matchers.get('test')
            if 'reference' not in matchers:
                continue
            matcher = matchers['reference']
            if matcher.match(path):
                merge = None
                l10n = matcher.sub(matchers['l10n'], path)
                if 'merge' in matchers:
                    merge = matcher.sub(matchers['merge'], path)
                return l10n, path, merge, matchers.get('test')


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
