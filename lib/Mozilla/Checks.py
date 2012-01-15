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
import codecs
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
        return self.pattern.match(file.file)

    def check(self, refEnt, l10nEnt):
        '''Given the reference and localized Entities, performs checks.

        This is a generator yielding tuples of
        - "warning" or "error", depending on what should be reported,
        - tuple of line, column info for the error within the string
        - description string to be shown in the report
        '''
        if True:
            raise NotImplementedError, "Need to subclass"
        yield ("error", (0,0), "This is an example error", "example")

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
                yield ('warning', 0, 'not all variables used in l10n',
                       'plural')
                return
            if lpats - pats:
                yield ('error', 0, 'unreplaced variables in l10n',
                       'plural')
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
            yield ('error', e.pos, e.msg, 'printf')
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
                yield ('error', 0, ', '.join(msgs), 'printf')
            if warn is not None:
                yield ('warning', 0, warn, 'printf')

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
    """Tests to run on DTD files.

    Uses xml.sax for the heavy lifting of xml parsing.

    The code tries to parse until it doesn't find any unresolved entities
    anymore. If it finds one, it tries to grab the key, and adds an empty
    <!ENTITY key ""> definition to the header.

    Also checks for some CSS and number heuristics in the values.
    """
    pattern = re.compile('.*\.dtd$')

    eref = re.compile('&(%s);' % DTDParser.Name)
    tmpl = '''<!DOCTYPE elem [%s]>
<elem>%s</elem>
'''
    xmllist = set(('amp', 'lt', 'gt', 'apos', 'quot'))

    # Setup for XML parser, with default and text-only content handler
    class TextContent(sax.handler.ContentHandler):
        textcontent = ''
        def characters(self, content):
            self.textcontent += content

    defaulthandler = sax.handler.ContentHandler()
    texthandler = TextContent()

    numPattern = r'([0-9]+|[0-9]*\.[0-9]+)'
    num = re.compile('^%s$' % numPattern)
    lengthPattern = '%s(em|px|ch|cm|in)' % numPattern
    length = re.compile('^%s$' % lengthPattern)
    spec = re.compile(r'((?:min\-)?(?:width|height))\s*:\s*%s' % lengthPattern)
    style = re.compile(r'^%(spec)s\s*(;\s*%(spec)s\s*)*;?$' % {'spec': spec.pattern})

    processContent = None

    def __init__(self):
        self.parser = sax.make_parser()
        self.parser.setFeature(sax.handler.feature_external_ges, False)

    def check(self, refEnt, l10nEnt):
        """Try to parse the refvalue inside a dummy element, and keep
        track of entities that we need to define to make that work.

        Return a checker that offers just those entities.
        """
        refValue, l10nValue = refEnt.val, l10nEnt.val
        # find entities the refValue references,
        # reusing markup from DTDParser.
        reflist = set(m.group(1).encode('utf-8') 
                      for m in self.eref.finditer(refValue)) \
                      - self.xmllist
        entities = ''.join('<!ENTITY %s "">' % s for s in sorted(reflist))
        self.parser.setContentHandler(self.defaulthandler)
        try:
            self.parser.parse(StringIO(self.tmpl % (entities, refValue.encode('utf-8'))))
            # also catch stray %
            self.parser.parse(StringIO(self.tmpl % (refEnt.all.encode('utf-8') + entities, '&%s;' % refEnt.key.encode('utf-8'))))
        except sax.SAXParseException, e:
            yield ('warning',
                   (0,0),
                   "can't parse en-US value", 'xmlparse')

        # find entities the l10nValue references,
        # reusing markup from DTDParser.
        l10nlist = set(m.group(1).encode('utf-8') 
                       for m in self.eref.finditer(l10nValue)) \
                       - self.xmllist
        missing = sorted(l10nlist - reflist)
        _entities = entities + ''.join('<!ENTITY %s "">' % s for s in missing)
        warntmpl = u'Referencing unknown entity `%s`'
        if reflist:
            warntmpl += ' (%s known)' % ', '.join(sorted(reflist))
        if self.processContent is not None:
            self.texthandler.textcontent = ''
            self.parser.setContentHandler(self.texthandler)
        try:
            self.parser.parse(StringIO(self.tmpl % (_entities, l10nValue.encode('utf-8'))))
            # also catch stray %
            # if this fails, we need to substract the entity definition
            self.parser.setContentHandler(self.defaulthandler)
            self.parser.parse(StringIO(self.tmpl % (l10nEnt.all.encode('utf-8') + _entities, '&%s;' % l10nEnt.key.encode('utf-8'))))
        except sax.SAXParseException, e:
            # xml parse error, yield error
            # sometimes, the error is reported on our fake closing
            # element, make that the end of the last line
            lnr = e.getLineNumber() - 1
            lines = l10nValue.splitlines()
            if lnr > len(lines):
                lnr = len(lines)
                col = len(lines[lnr-1])
            else:
                col = e.getColumnNumber()
                if lnr == 1:
                    col -= len("<elem>") # first line starts with <elem>, substract
                elif lnr == 0:
                    col -= len("<!DOCTYPE elem [") # first line is DOCTYPE
            yield ('error', (lnr, col), ' '.join(e.args), 'xmlparse')

        for key in missing:
            yield ('warning', (0,0), warntmpl % key.decode('utf-8'), 'xmlparse')

        # Number check
        if self.num.match(refValue) and not self.num.match(l10nValue):
            yield ('warning', 0, 'reference is a number', 'number')
        # CSS checks
        # just a length, width="100em"
        if self.length.match(refValue) and not self.length.match(l10nValue):
            yield ('error', 0, 'reference is a CSS length', 'css')
        # real CSS spec, style="width:100px;"
        if self.style.match(refValue):
            if not self.style.match(l10nValue):
                yield ('error', 0, 'reference is a CSS spec', 'css')
            else:
                # warn if different properties or units
                refMap = dict((s, u) for s, _, u in
                              self.spec.findall(refValue))
                msgs = []
                for s, _, u in self.spec.findall(l10nValue):
                    if s not in refMap:
                        msgs.insert(0, '%s only in l10n' % s)
                        continue
                    else:
                        ru = refMap.pop(s)
                        if u != ru:
                            msgs.append("units for %s don't match "
                                        "(%s != %s)" % (s, u, ru))
                for s in refMap.iterkeys():
                    msgs.insert(0, '%s only in reference' % s)
                if msgs:
                    yield ('warning', 0, ', '.join(msgs), 'css')

        if self.processContent is not None:
            for t in self.processContent(self.texthandler.textcontent):
                yield t


class PrincessAndroid(DTDChecker):
    """Checker for the string values that Android puts into an XML container.

    http://developer.android.com/guide/topics/resources/string-resource.html#FormattingAndStyling
    has more info. Check for unescaped apostrophes and bad unicode escapes.
    """
    quoted = re.compile("(?P<q>[\"']).*(?P=q)$")
    def unicode_escape(self, str):
        """Helper method to try to decode all unicode escapes in a string.

        This code uses the standard python decode for unicode-escape, but that's
        somewhat tricky, as its input needs to be ascii. To get to ascii, the
        unicode string gets converted to ascii with backslashreplace, i.e.,
        all non-ascii unicode chars get unicode escaped. And then we try to roll
        all of that back.
        Now, when that hits an error, that's from the original string, and we need
        to search for the actual error position in the original string, as the
        backslashreplace code changes string positions quite badly. See also the
        last check in TestAndroid.test_android_dtd, with a lengthy chinese string.
        """
        val = str.encode('ascii', 'backslashreplace')
        try:
            val.decode('unicode-escape')
        except UnicodeDecodeError, e:
            args = list(e.args)
            badstring = args[1][args[2]:args[3]]
            i = str.rindex(badstring, 0, args[3])
            args[2] = i
            args[3] = i + len(badstring)
            raise UnicodeDecodeError(*args)
    def use(self, file):
        """Use this Checker only for DTD files in embedding/android."""
        return (file.module in ("embedding/android",
                                "mobile/android/base")
            and DTDChecker.pattern.match(file.file))
    def processContent(self, val):
        """Actual check code.
        Check for unicode escapes and unescaped quotes and apostrophes, if string's not quoted.
        """
        # first, try to decode unicode escapes
        try:
            self.unicode_escape(val)
        except UnicodeDecodeError, e:
            yield ('error', e.args[2], e.args[4], 'android')
        # check for unescaped single or double quotes.
        # first, see if the complete string is single or double quoted, that changes the rules
        m = self.quoted.match(val)
        if m:
            q = m.group('q')
            offset = 0
            val = val[1:-1] # strip quotes
        else:
            q = "[\"']"
            offset = -1
        stray_quot = re.compile(r"[\\\\]*(%s)" % q)
            
        for m in stray_quot.finditer(val):
            if len(m.group(0)) % 2:
                # found an unescaped single or double quote, which message?
                msg = m.group(1) == '"' and u"Quotes in Android DTDs need escaping with \\\" or \\u0022, or put string in apostrophes." \
                      or u"Apostrophes in Android DTDs need escaping with \\' or \\u0027, or use \u2019, or put string in quotes."
                yield ('error', m.end(0)+offset, msg, 'android')


class __checks:
    props = PropertiesChecker()
    android_dtd = PrincessAndroid()
    dtd = DTDChecker()

def getChecks(file):
    check = None
    if __checks.props.use(file):
        check = __checks.props.check
    elif __checks.android_dtd.use(file):
        check = __checks.android_dtd.check
    elif __checks.dtd.use(file):
        check = __checks.dtd.check
    return check

