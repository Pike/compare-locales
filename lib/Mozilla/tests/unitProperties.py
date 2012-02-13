# -*- coding: utf-8 -*-

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
    self.assertEqual(e.key, '_junk_1_113-126')
    for r, e in zip(('This line is one of two and ends in \\and still has another line coming',), i):
      self.assertEqual(e.val, r)
  
  def testProperties(self):
    # port of netwerk/test/PropertiesTest.cpp
    self.p.readContents(r'''# ***** BEGIN LICENSE BLOCK *****
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
# The Original Code is mozilla.org code.
#
# The Initial Developer of the Original Code is
# Netscape Communications Corporation.
# Portions created by the Initial Developer are Copyright (C) 1998
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#
# Alternatively, the contents of this file may be used under the terms of
# either of the GNU General Public License Version 2 or later (the "GPL"),
# or the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
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
    p.readContents('''# ***** BEGIN LICENSE BLOCK *****
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
# The Original Code is mozilla.org code.
#
# The Initial Developer of the Original Code is
# International Business Machines Corporation.
# Portions created by the Initial Developer are Copyright (C) 2000
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
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


if __name__ == '__main__':
  unittest.main()
