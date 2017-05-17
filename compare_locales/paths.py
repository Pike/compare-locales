# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import re
from ConfigParser import ConfigParser, NoSectionError, NoOptionError
from collections import defaultdict
import itertools
from compare_locales import util, mozpath


class Matcher(object):
    '''Path pattern matcher
    Supports path matching similar to mozpath.match(), but does
    not match trailing file paths without trailing wildcards.
    Also gets a prefix, which is the path before the first wildcard,
    which is good for filesystem iterations, and allows to replace
    the own matches in a path on a different Matcher. compare-locales
    uses that to transform l10n and en-US paths back and forth.
    '''
    _locale = re.compile(r'\{\s*locale\s*\}')

    def __init__(self, pattern, locale=None):
        '''Create regular expression similar to mozpath.match().
        '''
        if locale is not None:
            pattern = self._locale.sub(locale, pattern)
        prefix = pattern.split("*", 1)[0]
        p = re.escape(pattern)
        p = re.sub(r'(^|\\\/)\\\*\\\*\\\/', r'\1(.+/)?', p)
        p = re.sub(r'(^|\\\/)\\\*\\\*$', r'(\1.+)?', p)
        p = p.replace(r'\*', '([^/]*)') + '$'
        r = re.escape(pattern)
        r = re.sub(r'(^|\\\/)\\\*\\\*\\\/', r'\\\\0', r)
        r = re.sub(r'(^|\\\/)\\\*\\\*$', r'\\\\0', r)
        r = r.replace(r'\*', r'\\0')
        backref = itertools.count(1)
        r = re.sub(r'\\0', lambda m: '\\%s' % backref.next(), r)
        r = re.sub(r'\\(.)', r'\1', r)
        self.prefix = prefix
        self.regex = re.compile(p)
        self.placable = r

    def match(self, path):
        '''
        True if the given path matches the file pattern.
        '''
        return self.regex.match(path) is not None

    def sub(self, other, path):
        '''
        Replace the wildcard matches in this pattern into the
        pattern of the other Match object.
        '''
        if not self.match(path):
            return None
        return self.regex.sub(other.placable, path)


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
        self.projects = []  # TODO: add support for sub-projects

    def add_paths(self, *paths):
        '''Add path dictionaries to this config.
        The dictionaries must have a `l10n` key. For monolingual files,
        `reference` is also required.
        An optional key `test` is allowed to enable additional tests for this
        path pattern.
        TODO: We may support an additional locale key in the future.
        '''
        for d in paths:
            rv = {
                'l10n': d['l10n'],
                'module': d.get('module')
            }
            if 'reference' in d:
                rv['reference'] = Matcher(d['reference'])
            if 'test' in d:
                rv['test'] = d['test']
            if 'locales' in d:
                rv['locales'] = d['locales'][:]
            self.paths.append(rv)

    def set_filter_py(self, filter):
        '''Set legacy filter.py code.
        Assert that no rules are set.
        Also, normalize output already here.
        '''
        assert not self.rules

        def filter_(module, path, entity=None):
            try:
                rv = filter(module, path, entity=entity)
            except:
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

    def filter(self, l10n_file, entity=None):
        '''Filter a localization file or entities within, according to
        this configuration file.'''
        if self.filter_py is not None:
            return self.filter_py(l10n_file.module, l10n_file.file,
                                  entity=entity)
        for rule in reversed(self.rules):
            matcher = Matcher(
                rule.get('path', '.'),
                l10n_file.locale)
            if not matcher.match(l10n_file.fullpath):
                continue
            if ('key' in rule) ^ (entity is not None):
                # key/file mismatch, not a matching rule
                continue
            if 'key' in rule and not rule['key'].match(entity.key):
                continue
            return rule['action']

    def _compile_rule(self, rule):
        assert 'path' in rule
        if not isinstance(rule['path'], basestring):
            for path in rule['path']:
                _rule = rule.copy()
                _rule['path'] = path
                for __rule in self._compile_rule(_rule):
                    yield __rule
            return
        if 'key' not in rule:
            yield rule
            return
        if not isinstance(rule['key'], basestring):
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


class ProjectFiles(object):
    '''Iterator object to get all files and tests for a locale and a
    list of ProjectConfigs.
    '''
    def __init__(self, locale, *projects):
        self.locale = locale
        self.matchers = []
        for pc in projects:
            if locale not in pc.locales:
                continue
            for paths in pc.paths:
                if 'locales' in paths and locale not in paths['locales']:
                    continue
                m = {
                    'l10n': Matcher(paths['l10n'], locale),
                    'module': paths.get('module')
                }
                if 'reference' in paths:
                    m['reference'] = paths['reference']
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
        known = {}
        for matchers in self.matchers:
            matcher = matchers['l10n']
            for path in self._files(matcher.prefix):
                if matcher.match(path) and path not in known:
                    known[path] = {'test': matchers.get('test')}
                    if 'reference' in matchers:
                        known[path]['reference'] = matcher.sub(
                            matchers['reference'], path)
            if 'reference' not in matchers:
                continue
            matcher = matchers['reference']
            for path in self._files(matcher.prefix):
                if not matcher.match(path):
                    continue
                l10npath = matcher.sub(matchers['l10n'], path)
                if l10npath not in known:
                    known[l10npath] = {
                        'reference': path,
                        'test': matchers.get('test')
                    }
        for path, d in sorted(known.items()):
            yield (path, d.get('reference'), d['test'])

    def _files(self, base):
        '''Base implementation of getting all files in a hierarchy
        using the file system.
        Subclasses might replace this method to support different IO
        patterns.
        '''
        for d, dirs, files in os.walk(base):
            for f in files:
                yield mozpath.join(d, f)


class L10nConfigParser(object):
    '''Helper class to gather application information from ini files.

    This class is working on synchronous open to read files or web data.
    Subclass this and overwrite loadConfigs and addChild if you need async.
    '''
    def __init__(self, inipath, **kwargs):
        """Constructor for L10nConfigParsers

        inipath -- l10n.ini path
        Optional keyword arguments are fowarded to the inner ConfigParser as
        defaults.
        """
        self.inipath = mozpath.normpath(inipath)
        # l10n.ini files can import other l10n.ini files, store the
        # corresponding L10nConfigParsers
        self.children = []
        # we really only care about the l10n directories described in l10n.ini
        self.dirs = []
        # optional defaults to be passed to the inner ConfigParser (unused?)
        self.defaults = kwargs

    def getDepth(self, cp):
        '''Get the depth for the comparison from the parsed l10n.ini.
        '''
        try:
            depth = cp.get('general', 'depth')
        except:
            depth = '.'
        return depth

    def getFilters(self):
        '''Get the test functions from this ConfigParser and all children.

        Only works with synchronous loads, used by compare-locales, which
        is local anyway.
        '''
        filter_path = mozpath.join(mozpath.dirname(self.inipath), 'filter.py')
        try:
            l = {}
            execfile(filter_path, {}, l)
            if 'test' in l and callable(l['test']):
                filters = [l['test']]
            else:
                filters = []
        except:
            filters = []

        for c in self.children:
            filters += c.getFilters()

        return filters

    def loadConfigs(self):
        """Entry point to load the l10n.ini file this Parser refers to.

        This implementation uses synchronous loads, subclasses might overload
        this behaviour. If you do, make sure to pass a file-like object
        to onLoadConfig.
        """
        cp = ConfigParser(self.defaults)
        cp.read(self.inipath)
        depth = self.getDepth(cp)
        self.base = mozpath.join(mozpath.dirname(self.inipath), depth)
        # create child loaders for any other l10n.ini files to be included
        try:
            for title, path in cp.items('includes'):
                # skip default items
                if title in self.defaults:
                    continue
                # add child config parser
                self.addChild(title, path, cp)
        except NoSectionError:
            pass
        # try to load the "dirs" defined in the "compare" section
        try:
            self.dirs.extend(cp.get('compare', 'dirs').split())
        except (NoOptionError, NoSectionError):
            pass
        # try to set "all_path" and "all_url"
        try:
            self.all_path = mozpath.join(self.base, cp.get('general', 'all'))
        except (NoOptionError, NoSectionError):
            self.all_path = None
        return cp

    def addChild(self, title, path, orig_cp):
        """Create a child L10nConfigParser and load it.

        title -- indicates the module's name
        path -- indicates the path to the module's l10n.ini file
        orig_cp -- the configuration parser of this l10n.ini
        """
        cp = L10nConfigParser(mozpath.join(self.base, path), **self.defaults)
        cp.loadConfigs()
        self.children.append(cp)

    def dirsIter(self):
        """Iterate over all dirs and our base path for this l10n.ini"""
        for dir in self.dirs:
            yield dir, (self.base, dir)

    def directories(self):
        """Iterate over all dirs and base paths for this l10n.ini as well
        as the included ones.
        """
        for t in self.dirsIter():
            yield t
        for child in self.children:
            for t in child.directories():
                yield t

    def allLocales(self):
        """Return a list of all the locales of this project"""
        return util.parseLocales(open(self.all_path).read())


class SourceTreeConfigParser(L10nConfigParser):
    '''Subclassing L10nConfigParser to work with just the repos
    checked out next to each other instead of intermingled like
    we do for real builds.
    '''

    def __init__(self, inipath, base, redirects):
        '''Add additional arguments basepath.

        basepath is used to resolve local paths via branchnames.
        redirects is used in unified repository, mapping upstream
        repos to local clones.
        '''
        L10nConfigParser.__init__(self, inipath)
        self.base = base
        self.redirects = redirects

    def addChild(self, title, path, orig_cp):
        # check if there's a section with details for this include
        # we might have to check a different repo, or even VCS
        # for example, projects like "mail" indicate in
        # an "include_" section where to find the l10n.ini for "toolkit"
        details = 'include_' + title
        if orig_cp.has_section(details):
            branch = orig_cp.get(details, 'mozilla')
            branch = self.redirects.get(branch, branch)
            inipath = orig_cp.get(details, 'l10n.ini')
            path = mozpath.join(self.base, branch, inipath)
        else:
            path = mozpath.join(self.base, path)
        cp = SourceTreeConfigParser(path, self.base, self.redirects,
                                    **self.defaults)
        cp.loadConfigs()
        self.children.append(cp)


class File(object):

    def __init__(self, fullpath, file, module=None, locale=None):
        self.fullpath = fullpath
        self.file = file
        self.module = module
        self.locale = locale
        pass

    def getContents(self):
        # open with universal line ending support and read
        return open(self.fullpath, 'rU').read()

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

    def __cmp__(self, other):
        if not isinstance(other, File):
            raise NotImplementedError
        rv = cmp(self.module, other.module)
        if rv != 0:
            return rv
        return cmp(self.file, other.file)


class EnumerateApp(object):
    reference = 'en-US'

    def __init__(self, inipath, l10nbase, locales=None):
        self.setupConfigParser(inipath)
        self.modules = defaultdict(dict)
        self.l10nbase = mozpath.abspath(l10nbase)
        self.filters = []
        self.addFilters(*self.config.getFilters())
        self.locales = locales or self.config.allLocales()
        self.locales.sort()

    def setupConfigParser(self, inipath):
        self.config = L10nConfigParser(inipath)
        self.config.loadConfigs()

    def addFilters(self, *args):
        self.filters += args

    def asConfig(self):
        config = ProjectConfig()
        self._config_for_ini(config, self.config)
        filters = self.config.getFilters()
        if filters:
            config.set_filter_py(filters[0])
        config.locales += self.locales
        return config

    def _config_for_ini(self, projectconfig, aConfig):
        for k, (basepath, module) in aConfig.dirsIter():
            paths = {
                'module': module,
                'reference': mozpath.normpath('%s/%s/locales/en-US/**' %
                                              (basepath, module)),
                'l10n': mozpath.normpath('%s/{locale}/%s/**' %
                                         (self.l10nbase, module))
            }
            if module == 'mobile/android/base':
                paths['test'] = ['android-dtd']
            projectconfig.add_paths(paths)
        for child in aConfig.children:
            self._config_for_ini(projectconfig, child)


class EnumerateSourceTreeApp(EnumerateApp):
    '''Subclass EnumerateApp to work on side-by-side checked out
    repos, and to no pay attention to how the source would actually
    be checked out for building.
    '''

    def __init__(self, inipath, basepath, l10nbase, redirects,
                 locales=None):
        self.basepath = basepath
        self.redirects = redirects
        EnumerateApp.__init__(self, inipath, l10nbase, locales)

    def setupConfigParser(self, inipath):
        self.config = SourceTreeConfigParser(inipath, self.basepath,
                                             self.redirects)
        self.config.loadConfigs()
