# -*- coding: utf-8 -*-

import unittest

from Mozilla.Parser import getParser

class TestLineWraps(unittest.TestCase):

    def setUp(self):
	self.p = getParser('foo.ini')

    def tearDown(self):
	del self.p

    def testSimpleHeader(self):
	self.p.readContents('''; This file is in the UTF-8 encoding
[Strings]
TitleText=Some Title
''')
	for e in self.p:
	    self.assertEqual(e.key, 'TitleText')
	    self.assertEqual(e.val, 'Some Title')
	self.assert_('UTF-8' in self.p.header)

    def testMPL2_Space_UTF(self):
	self.p.readContents('''; This Source Code Form is subject to the terms of the Mozilla Public
; License, v. 2.0. If a copy of the MPL was not distributed with this file,
; You can obtain one at http://mozilla.org/MPL/2.0/.

; This file is in the UTF-8 encoding
[Strings]
TitleText=Some Title
''')
	for e in self.p:
	    self.assertEqual(e.key, 'TitleText')
	    self.assertEqual(e.val, 'Some Title')
	self.assert_('MPL' in self.p.header)

    def testMPL2_Space(self):
	self.p.readContents('''; This Source Code Form is subject to the terms of the Mozilla Public
; License, v. 2.0. If a copy of the MPL was not distributed with this file,
; You can obtain one at http://mozilla.org/MPL/2.0/.

[Strings]
TitleText=Some Title
''')
	for e in self.p:
	    self.assertEqual(e.key, 'TitleText')
	    self.assertEqual(e.val, 'Some Title')
	self.assert_('MPL' in self.p.header)

    def testMPL2_MultiSpace(self):
	self.p.readContents('''; This Source Code Form is subject to the terms of the Mozilla Public
; License, v. 2.0. If a copy of the MPL was not distributed with this file,
; You can obtain one at http://mozilla.org/MPL/2.0/.

; more comments

[Strings]
TitleText=Some Title
''')
	for e in self.p:
	    self.assertEqual(e.key, 'TitleText')
	    self.assertEqual(e.val, 'Some Title')
	self.assert_('MPL' in self.p.header)

    def testMPL2_Junk(self):
	self.p.readContents('''; This Source Code Form is subject to the terms of the Mozilla Public
; License, v. 2.0. If a copy of the MPL was not distributed with this file,
; You can obtain one at http://mozilla.org/MPL/2.0/.
Junk
[Strings]
TitleText=Some Title
''')
	self.assertEqual([
	    ('_junk_1_0-213', '''; This Source Code Form is subject to the terms of the Mozilla Public
; License, v. 2.0. If a copy of the MPL was not distributed with this file,
; You can obtain one at http://mozilla.org/MPL/2.0/.
Junk
[Strings]'''),
	    ('TitleText', 'Some Title')
	    ],
	    [(e.key, e.val) for e in self.p])
	self.assert_('MPL' not in self.p.header)

if __name__ == '__main__':
  unittest.main()
