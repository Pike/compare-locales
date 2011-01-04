# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is l10n test automation.
#
# The Initial Developer of the Original Code is
# Mozilla Foundation
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#	Axel Hecht <l10n@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

import re
import itertools
from difflib import SequenceMatcher
from xml import sax
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from Parser import DTDParser

class Checker(object):
    '''Abstract class to implement checks per file type.
    '''
    pattern = None

    def use(self, file):
        return self.pattern.match(file)

    def check(self, refEnt, l10nEnt):
        '''Given the reference and localized Entities, performs checks.

        This is a generator yielding tuples of
        - "warning" or "error", depending on what should be reported,
        - tuple of line, column info for the error within the string
        - description string to be shown in the report
        '''
        if True:
            raise NotImplementedError, "Need to subclass"
        yield ("error", (0,0), "This is an example error")

class PrintfException(Exception):
    def __init__(self, msg, pos):
        self.pos = pos
        self.msg = msg

class PropertiesChecker(Checker):
    '''Tests to run on .properties files.
    '''
    pattern = re.compile('.*\.properties$')
    printf = re.compile(r'%(?P<good>%|(?:(?P<number>[1-9][0-9]*)\$)?(?P<width>\*|[0-9]+)?(?P<prec>\.(?:\*|[0-9]+)?)?(?P<spec>[duxXosScpfg]))?')

    def check(self, refEnt, l10nEnt):
        '''Test for the different variable formats.
        '''
        refValue, l10nValue = refEnt.val, l10nEnt.val
        refSpecs = None
        # check for PluralForm.jsm stuff, should have the docs in the
        # comment
        if 'Localization_and_Plurals' in refEnt.pre_comment:
            # For plurals, common variable pattern is #1. Try that.
            pats = set(int(m.group(1)) for m in re.finditer('#([0-9]+)',
                                                            refValue))
            if len(pats)==0:
                return
            lpats = set(int(m.group(1)) for m in re.finditer('#([0-9]+)',
                                                             l10nValue))
            if pats - lpats:
                yield ('warning', 0, 'not all variables used in l10n')
                return
            if lpats - pats:
                yield ('error', 0, 'unreplaced variables in l10n')
                return
            return
        try:
            refSpecs = self.getPrintfSpecs(refValue)
        except PrintfException, e:
            refSpecs = []
        if refSpecs:
            for t in self.checkPrintf(refSpecs, l10nValue):
                yield t
            return

    def checkPrintf(self, refSpecs, l10nValue):
        try:
            l10nSpecs = self.getPrintfSpecs(l10nValue)
        except PrintfException, e:
            yield ('error', e.pos, e.msg)
            return
        if refSpecs != l10nSpecs:
            sm = SequenceMatcher()
            sm.set_seqs(refSpecs, l10nSpecs)
            msgs = []
            warn = None
            for action, ls, le, rs, re in sm.get_opcodes():
                if action == 'equal':
                    continue
                if action == 'delete':
                    # missing argument in l10n
                    if le == len(refSpecs):
                        # trailing specs missing, that's just a warning
                        warn = ', '.join('trailing argument %d `%s` missing' %
                                         (i+1, refSpecs[i]) 
                                         for i in xrange(ls, le))
                    else:
                        for i in xrange(ls, le):
                            msgs.append('argument %d `%s` missing' %
                                        (i+1, refSpecs[i]))
                    continue
                if action == 'insert':
                    # obsolete argument in l10n
                    for i in xrange(rs, re):
                        msgs.append('argument %d `%s` obsolete' %
                                    (i+1, l10nSpecs[i]))
                    continue
                if action == 'replace':
                    for i, j in zip(xrange(ls, le), xrange(rs, re)):
                        msgs.append('argument %d `%s` should be `%s`' %
                                    (j+1, l10nSpecs[j], refSpecs[i]))
            if msgs:
                yield ('error', 0, ', '.join(msgs))
            if warn is not None:
                yield ('warning', 0, warn)

    def getPrintfSpecs(self, val):
        hasNumber = False
        specs = []
        for m in self.printf.finditer(val):
            if m.group("good") is None:
                # found just a '%', signal an error
                raise PrintfException('Found single %', m.start())
            if m.group("good") == '%':
                # escaped %
                continue
            if ((hasNumber and m.group('number') is None) or
                (not hasNumber and specs and m.group('number') is not None)):
                # mixed style, numbered and not
                raise PrintfException('Mixed ordered and non-ordered args',
                                      m.start())
            hasNumber = m.group('number') is not None
            if hasNumber:
                pos = int(m.group('number')) - 1
                ls = len(specs)
                if pos >= ls:
                    # pad specs
                    nones = pos - ls
                    specs[ls:pos] = nones*[None]
                    specs.append(m.group('spec'))
                else:
                    if specs[pos] is not None:
                        raise PrintfException('Double ordered argument %d' % (pos+1),
                                              m.start())
                    specs[pos] = m.group('spec')
            else:
                specs.append(m.group('spec'))
        # check for missing args
        if hasNumber and not all(specs):
            raise PrintfException('Ordered argument missing', 0)
        return specs


class DTDChecker(Checker):
    '''Tests to run on DTD files.

    Uses xml.sax for the heavy lifting of xml parsing.

    The code tries to parse until it doesn't find any unresolved entities
    anymore. If it finds one, it tries to grab the key, and adds an empty
    <!ENTITY key ""> definition to the header.
    '''
    pattern = re.compile('.*\.dtd$')

    eref = re.compile('&(%s);' % DTDParser.Name)
    tmpl = '''<!DOCTYPE elem [%s]>
<elem>
%s
</elem>
'''
    xmllist = set(('amp', 'lt', 'gt', 'apos', 'quot'))

    def check(self, refEnt, l10nEnt):
        '''Try to parse the refvalue inside a dummy element, and keep
        track of entities that we need to define to make that work.

        Return a checker that offers just those entities.
        '''
        refValue, l10nValue = refEnt.val, l10nEnt.val
        # find entities the refValue references,
        # reusing markup from DTDParser.
        reflist = set(m.group(1).encode('utf-8') 
                      for m in self.eref.finditer(refValue)) \
                      - self.xmllist
        entities = ''.join('<!ENTITY %s "">' % s for s in sorted(reflist))
        parser = sax.make_parser()
        try:
            parser.parse(StringIO(self.tmpl % (entities, refValue.encode('utf-8'))))
        except sax.SAXParseException, e:
            yield ('warning',
                   (0,0),
                   "can't parse en-US value")

        # find entities the l10nValue references,
        # reusing markup from DTDParser.
        l10nlist = set(m.group(1).encode('utf-8') 
                       for m in self.eref.finditer(l10nValue)) \
                       - self.xmllist
        missing = sorted(l10nlist - reflist)
        _entities = entities + ''.join('<!ENTITY %s "">' % s for s in missing)
        warntmpl = 'Referencing unknown entity `%s`'
        if reflist:
            warntmpl += ' (%s known)' % ', '.join(sorted(reflist))
        try:
            parser.parse(StringIO(self.tmpl % (_entities, l10nValue.encode('utf-8'))))
        except sax.SAXParseException, e:
            # xml parse error, yield error
            # sometimes, the error is reported on our fake closing
            # element, make that the end of the last line
            lnr = e.getLineNumber() - 2
            lines = l10nValue.splitlines()
            if lnr > len(lines):
                lnr = len(lines)
                col = len(lines[lnr-1])
            else:
                col = e.getColumnNumber()
            yield ('error', (lnr, col), ' '.join(e.args))

        for key in missing:
            yield ('warning', (0,0), warntmpl % key)


__checks = [DTDChecker(), PropertiesChecker()]

def getChecks(file):
    checks = map(lambda c: c.check, filter(lambda c: c.use(file), __checks))
    def _checks(refEnt, l10nEnt):
        return itertools.chain(*[c(refEnt, l10nEnt) for c in checks])
    return _checks

