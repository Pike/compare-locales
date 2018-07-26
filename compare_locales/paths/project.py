# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import
import re
from .matcher import Matcher
import six


class ProjectConfig(object):
    '''Abstraction of l10n project configuration data.
    '''

    def __init__(self):
        self.filter_py = None  # legacy filter code
        # {
        #  'l10n': pattern,
        #  'reference': pattern,  # optional
        #  'locales': [],  # optional
        #  'test': [],  # optional
        # }
        self.paths = []
        self.rules = []
        self.locales = []
        self.environ = {}
        self.children = []
        self._cache = None

    def expand(self, path, env=None):
        envs = [self.environ]
        if env:
            envs.insert(0, env)
        return Matcher.expand(path, *envs)

    def lazy_expand(self, pattern):
        def lazy_l10n_expanded_pattern(env):
            return Matcher(self.expand(pattern, env))
        return lazy_l10n_expanded_pattern

    def add_global_environment(self, **kwargs):
        self.add_environment(**kwargs)
        for child in self.children:
            child.add_global_environment(**kwargs)

    def add_environment(self, **kwargs):
        self.environ.update(kwargs)

    def add_paths(self, *paths):
        '''Add path dictionaries to this config.
        The dictionaries must have a `l10n` key. For monolingual files,
        `reference` is also required.
        An optional key `test` is allowed to enable additional tests for this
        path pattern.
        '''

        for d in paths:
            rv = {
                'l10n': self.lazy_expand(d['l10n']),
                'module': d.get('module')
            }
            if 'reference' in d:
                rv['reference'] = Matcher(d['reference'])
            if 'test' in d:
                rv['test'] = d['test']
            if 'locales' in d:
                rv['locales'] = d['locales'][:]
            self.paths.append(rv)

    def set_filter_py(self, filter_function):
        '''Set legacy filter.py code.
        Assert that no rules are set.
        Also, normalize output already here.
        '''
        assert not self.rules

        def filter_(module, path, entity=None):
            try:
                rv = filter_function(module, path, entity=entity)
            except BaseException:  # we really want to handle EVERYTHING here
                return 'error'
            rv = {
                True: 'error',
                False: 'ignore',
                'report': 'warning'
            }.get(rv, rv)
            assert rv in ('error', 'ignore', 'warning', None)
            return rv
        self.filter_py = filter_

    def add_rules(self, *rules):
        '''Add rules to filter on.
        Assert that there's no legacy filter.py code hooked up.
        '''
        assert self.filter_py is None
        for rule in rules:
            self.rules.extend(self._compile_rule(rule))

    def add_child(self, child):
        self.children.append(child)

    def set_locales(self, locales, deep=False):
        self.locales = locales
        for child in self.children:
            if not child.locales or deep:
                child.set_locales(locales, deep=True)
            else:
                locs = [loc for loc in locales if loc in child.locales]
                child.set_locales(locs)

    @property
    def configs(self):
        'Recursively get all configs in this project and its children'
        yield self
        for child in self.children:
            for config in child.configs:
                yield config

    def filter(self, l10n_file, entity=None):
        '''Filter a localization file or entities within, according to
        this configuration file.'''
        if self.filter_py is not None:
            return self.filter_py(l10n_file.module, l10n_file.file,
                                  entity=entity)
        rv = self._filter(l10n_file, entity=entity)
        if rv is None:
            return 'ignore'
        return rv

    class FilterCache(object):
        def __init__(self, locale):
            self.locale = locale
            self.rules = []
            self.l10n_paths = []

    def cache(self, locale):
        if self._cache and self._cache.locale == locale:
            return self._cache
        self._cache = self.FilterCache(locale)
        for paths in self.paths:
            self._cache.l10n_paths.append(paths['l10n']({
                "locale": locale
            }))
        for rule in self.rules:
            cached_rule = rule.copy()
            cached_rule['path'] = rule['path']({
                "locale": locale
            })
            self._cache.rules.append(cached_rule)
        return self._cache

    def _filter(self, l10n_file, entity=None):
        actions = set(
            child._filter(l10n_file, entity=entity)
            for child in self.children)
        if 'error' in actions:
            # return early if we know we'll error
            return 'error'

        cached = self.cache(l10n_file.locale)
        if any(p.match(l10n_file.fullpath) for p in cached.l10n_paths):
            action = 'error'
            for rule in reversed(cached.rules):
                if not rule['path'].match(l10n_file.fullpath):
                    continue
                if ('key' in rule) ^ (entity is not None):
                    # key/file mismatch, not a matching rule
                    continue
                if 'key' in rule and not rule['key'].match(entity):
                    continue
                action = rule['action']
                break
            actions.add(action)
        if 'error' in actions:
            return 'error'
        if 'warning' in actions:
            return 'warning'
        if 'ignore' in actions:
            return 'ignore'

    def _compile_rule(self, rule):
        assert 'path' in rule
        if isinstance(rule['path'], list):
            for path in rule['path']:
                _rule = rule.copy()
                _rule['path'] = self.lazy_expand(path)
                for __rule in self._compile_rule(_rule):
                    yield __rule
            return
        if isinstance(rule['path'], six.string_types):
            rule['path'] = self.lazy_expand(rule['path'])
        if 'key' not in rule:
            yield rule
            return
        if not isinstance(rule['key'], six.string_types):
            for key in rule['key']:
                _rule = rule.copy()
                _rule['key'] = key
                for __rule in self._compile_rule(_rule):
                    yield __rule
            return
        rule = rule.copy()
        key = rule['key']
        if key.startswith('re:'):
            key = key[3:]
        else:
            key = re.escape(key) + '$'
        rule['key'] = re.compile(key)
        yield rule
