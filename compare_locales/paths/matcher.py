# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import
import re
import itertools


class Matcher(object):
    '''Path pattern matcher
    Supports path matching similar to mozpath.match(), but does
    not match trailing file paths without trailing wildcards.
    Also gets a prefix, which is the path before the first wildcard,
    which is good for filesystem iterations, and allows to replace
    the own matches in a path on a different Matcher. compare-locales
    uses that to transform l10n and en-US paths back and forth.
    '''

    def __init__(self, pattern):
        '''Create regular expression similar to mozpath.match().
        '''
        prefix = ''
        last_end = 0
        p = ''
        r = ''
        backref = itertools.count(1)
        for m in re.finditer(r'(?:(^|/)\*\*(/|$))|(?P<star>\*)', pattern):
            if m.start() > last_end:
                p += re.escape(pattern[last_end:m.start()])
                r += pattern[last_end:m.start()]
                if last_end == 0:
                    prefix = pattern[last_end:m.start()]
            if m.group('star'):
                p += '([^/]*)'
                r += r'\%s' % next(backref)
            else:
                p += re.escape(m.group(1)) + r'(.+%s)?' % m.group(2)
                r += m.group(1) + r'\%s' % next(backref) + m.group(2)
            last_end = m.end()
        p += re.escape(pattern[last_end:]) + '$'
        # Now replace variable references with named group matches.
        # The regex here matches the variable regex plus escaping.
        p = re.sub(
            r'\\{(?:\\ )*([\w]+)(?:\\ )*\\}',
            lambda m: '(?P<{}>.+?)'.format(m.group(1).replace('\\', '')), p)
        r += pattern[last_end:]
        if last_end == 0:
            prefix = pattern
        self.prefix = prefix
        self.regex = re.compile(p)
        self.placable = r

    def match(self, path):
        '''
        True if the given path matches the file pattern.
        '''
        return self.regex.match(path)

    def sub(self, other, path):
        '''
        Replace the wildcard matches in this pattern into the
        pattern of the other Match object.
        '''
        if not self.match(path):
            return None
        return self.regex.sub(other.placable, path)

    variable = re.compile('{ *([\w]+) *}')

    @staticmethod
    def expand(pattern, *envs):
        def _expand(m):
            _var = m.group(1)
            for env in envs:
                if _var in env:
                    return Matcher.expand(env[_var], *envs)
            return '{{{}}}'.format(_var)
        return Matcher.variable.sub(_expand, pattern)
