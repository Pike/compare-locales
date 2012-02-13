import unittest
import re

from Mozilla.Parser import getParser, Junk

class TestDTD(unittest.TestCase):

    def testGood(self):
        self._test('''<!ENTITY foo.label "stuff">''',
                   (('foo.label','stuff'),))


    quoteContent = '''<!ENTITY good.one "one">
<!ENTITY bad.one "bad " quote">
<!ENTITY good.two "two">
<!ENTITY bad.two "bad "quoted" word">
<!ENTITY good.three "three">
<!ENTITY good.four "good ' quote">
<!ENTITY good.five "good 'quoted' word">
'''
    quoteRef = (
        ('good.one', 'one'),
        ('_junk_1_25-56', '<!ENTITY bad.one "bad " quote">'),
        ('good.two', 'two'),
        ('_junk_2_82-119', '<!ENTITY bad.two "bad "quoted" word">'),
        ('good.three', 'three'),
        ('good.four', 'good \' quote'),
        ('good.five', 'good \'quoted\' word'),
        )
    def testQuote(self):
        self._test(self.quoteContent, self.quoteRef)

    def testApos(self):
        qr = re.compile('[\'"]', re.M)
        def quot2apos(s):
            return qr.sub(lambda m: m.group(0)=='"' and "'" or '"', s)
            
        self._test(quot2apos(self.quoteContent), 
                   map(lambda t: (t[0], quot2apos(t[1])), self.quoteRef))

    def testDTD(self):
        self._test('''<!ENTITY % fooDTD SYSTEM "chrome://brand.dtd">
  %fooDTD;
''',
                   (('fooDTD', '"chrome://brand.dtd"'),))

    def _test(self, content, refs):
        p = getParser('foo.dtd')
        Junk.junkid = 0
        p.readContents(content)
        entities = [e for e in p]
        self.assertEqual(len(entities), len(refs))
        for e, ref in zip(entities, refs):
            self.assertEqual(e.val, ref[1])
            self.assertEqual(e.key, ref[0])

    def testLicenseHeader(self):
        p = getParser('foo.dtd')
        p.readContents('''<!-- ***** BEGIN LICENSE BLOCK *****
#if 0
   - Version: MPL 1.1/GPL 2.0/LGPL 2.1
   -
   - The contents of this file are subject to the Mozilla Public License Version
   - 1.1 (the "License"); you may not use this file except in compliance with
   - the License. You may obtain a copy of the License at
   - http://www.mozilla.org/MPL/
   -
   - Software distributed under the License is distributed on an "AS IS" basis,
   - WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
   - for the specific language governing rights and limitations under the
   - License.
   -
   - The Original Code is mozilla.org Code.
   -
   - The Initial Developer of the Original Code is dummy.
   - Portions created by the Initial Developer are Copyright (C) 2005
   - the Initial Developer. All Rights Reserved.
   -
   - Contributor(s):
   -
   - Alternatively, the contents of this file may be used under the terms of
   - either the GNU General Public License Version 2 or later (the "GPL"), or
   - the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
   - in which case the provisions of the GPL or the LGPL are applicable instead
   - of those above. If you wish to allow use of your version of this file only
   - under the terms of either the GPL or the LGPL, and not to allow others to
   - use your version of this file under the terms of the MPL, indicate your
   - decision by deleting the provisions above and replace them with the notice
   - and other provisions required by the LGPL or the GPL. If you do not delete
   - the provisions above, a recipient may use your version of this file under
   - the terms of any one of the MPL, the GPL or the LGPL.
   -
#endif
   - ***** END LICENSE BLOCK ***** -->

<!ENTITY foo "value">
''')
        for e in p:
            self.assertEqual(e.key, 'foo')
            self.assertEqual(e.val, 'value')
        self.assert_('MPL' in p.header)
        p.readContents('''<!-- This Source Code Form is subject to the terms of the Mozilla Public
   - License, v. 2.0. If a copy of the MPL was not distributed with this file,
   - You can obtain one at http://mozilla.org/MPL/2.0/.  -->
<!ENTITY foo "value">
''')
        for e in p:
            self.assertEqual(e.key, 'foo')
            self.assertEqual(e.val, 'value')
        self.assert_('MPL' in p.header)

if __name__ == '__main__':
  unittest.main()
