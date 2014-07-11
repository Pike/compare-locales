# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re
import unittest

from Mozilla.Parser import getParser

class TestLineWraps(unittest.TestCase):

  def setUp(self):
    self.p = getParser('foo.properties')

  def tearDown(self):
    del self.p

  def testBackslashes(self):
    self.p.readContents(r'''one_line = This is one line
two_line = This is the first \
of two lines
one_line_trailing = This line ends in \\
and has junk
two_lines_triple = This line is one of two and ends in \\\
and still has another line coming
''')
    ref = ['This is one line',
           u'This is the first of two lines',
           u'This line ends in \\']
    i = iter(self.p)
    for r, e in zip(ref, i):
      self.assertEqual(e.val, r)
    e = i.next()
    self.assertTrue(re.match('_junk_\\d+_113-126$', e.key))
    for r, e in zip(('This line is one of two and ends in \\and still has another line coming',), i):
      self.assertEqual(e.val, r)
  
  def testProperties(self):
    # port of netwerk/test/PropertiesTest.cpp
    self.p.readContents(r'''# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
1=1
 2=2
3 =3
 4 =4
5=5
6= 6
7=7 
8= 8 
# this is a comment
9=this is the first part of a continued line \
 and here is the 2nd part
'''.encode('utf-8'))
    ref = ['1', '2', '3', '4', '5', '6', '7', '8', 'this is the first part of a continued line and here is the 2nd part']
    i = iter(self.p)
    for r, e in zip(ref, i):
      self.assertEqual(e.val, r)

  def test_bug121341(self):
    # port of xpcom/tests/unit/test_bug121341.js
    self.p.readContents(r'''# simple check
1=abc
# test whitespace trimming in key and value
  2	=   xy	
# test parsing of escaped values
3 = \u1234\t\r\n\uAB\
\u1\n
# test multiline properties
4 = this is \
multiline property
5 = this is \
	   another multiline property
# property with DOS EOL
6 = test\u0036
# test multiline property with with DOS EOL
7 = yet another multi\
    line propery
# trimming should not trim escaped whitespaces
8 =	\ttest5\u0020	
# another variant of #8
9 =     \ test6\t	    
# test UTF-8 encoded property/value
10aሴb = c췯d
# next property should test unicode escaping at the boundary of parsing buffer
# buffer size is expected to be 4096 so add comments to get to this offset
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
################################################################################
###############################################################################
11 = \uABCD
'''
      .replace('\r\n', '\n').replace('\r', '\n')  # fake universal line endings
      )
    ref = ['abc', 'xy', u"\u1234\t\r\n\u00AB\u0001\n","this is multiline property",
           "this is another multiline property", u"test\u0036",
           "yet another multiline propery", u"\ttest5\u0020", " test6\t",
           u"c\uCDEFd", u"\uABCD"]
    i = iter(self.p)
    for r, e in zip(ref, i):
      self.assertEqual(e.val, r)

  def test_commentInMulti(self):
    self.p.readContents(r'''bar=one line with a \
# part that looks like a comment \
and an end''')
    entities = list(self.p)
    self.assertEqual(len(entities), 1)
    self.assertEqual(entities[0].val, 'one line with a # part that looks like a comment and an end')

  def testLicenseHeader(self):
    p = getParser('foo.properties')
    p.readContents('''# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

foo=value
''')
    for e in p:
       self.assertEqual(e.key, 'foo')
       self.assertEqual(e.val, 'value')
    self.assert_('MPL' in p.header)
    p.readContents('''# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

foo=value
''')
    for e in p:
        self.assertEqual(e.key, 'foo')
        self.assertEqual(e.val, 'value')
    self.assert_('MPL' in p.header)

  def test_escapes(self):
    self.p.readContents(r'''
# unicode escapes
zero = some \unicode
one = \u0
two = \u41
three = \u042
four = \u0043
five = \u0044a
six = \a
seven = \n\r\t\\
''')
    ref = ['some unicode', chr(0), 'A', 'B', 'C', 'Da', 'a', '\n\r\t\\']
    for r, e in zip(ref, self.p):
      self.assertEqual(e.val, r)


if __name__ == '__main__':
  unittest.main()
