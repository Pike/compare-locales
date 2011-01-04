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

import unittest
import os
from tempfile import mkdtemp
import shutil

from Mozilla.Parser import getParser
from Mozilla.Paths import File
from Mozilla.CompareLocales import ContentComparer, Observer

class TestProperties(unittest.TestCase):
    def setUp(self):
        self.tmp = mkdtemp()
        os.mkdir(os.path.join(self.tmp, "merge"))
        self.ref = os.path.join(self.tmp, "en-reference.properties")
        open(self.ref, "w").write("""foo = fooVal
bar = barVal
eff = effVal""")
    def tearDown(self):
        shutil.rmtree(self.tmp)
        del self.tmp
    def testGood(self):
        self.assertTrue(os.path.isdir(self.tmp))
        l10n = os.path.join(self.tmp, "l10n.properties")
        open(l10n, "w").write("""foo = lFoo
bar = lBar
eff = lEff
""")
        obs = Observer()
        cc = ContentComparer(obs)
        cc.set_merge_stage(os.path.join(self.tmp, "merge"))
        cc.compare(File(self.ref, "en-reference.properties", ""),
                   File(l10n, "l10n.properties", ""))
        print obs.serialize()
    def testMissing(self):
        self.assertTrue(os.path.isdir(self.tmp))
        l10n = os.path.join(self.tmp, "l10n.properties")
        open(l10n, "w").write("""bar = lBar
""")
        obs = Observer()
        cc = ContentComparer(obs)
        cc.set_merge_stage(os.path.join(self.tmp, "merge"))
        cc.compare(File(self.ref, "en-reference.properties", ""),
                   File(l10n, "l10n.properties", ""))
        print obs.serialize()
        mergefile = os.path.join(self.tmp, "merge", "l10n.properties")
        self.assertTrue(os.path.isfile(mergefile))
        p = getParser(mergefile)
        p.readFile(mergefile)
        [m,n] = p.parse()
        self.assertEqual(map(lambda e:e.key,m), ["bar", "eff", "foo"])

class TestDTD(unittest.TestCase):
    def setUp(self):
        self.tmp = mkdtemp()
        os.mkdir(os.path.join(self.tmp, "merge"))
        self.ref = os.path.join(self.tmp, "en-reference.dtd")
        open(self.ref, "w").write("""<!ENTITY foo 'fooVal'>
<!ENTITY bar 'barVal'>
<!ENTITY eff 'effVal'>""")
    def tearDown(self):
        shutil.rmtree(self.tmp)
        del self.tmp
    def testGood(self):
        self.assertTrue(os.path.isdir(self.tmp))
        l10n = os.path.join(self.tmp, "l10n.dtd")
        open(l10n, "w").write("""<!ENTITY foo 'lFoo'>
<!ENTITY bar 'lBar'>
<!ENTITY eff 'lEff'>
""")
        obs = Observer()
        cc = ContentComparer(obs)
        cc.set_merge_stage(os.path.join(self.tmp, "merge"))
        cc.compare(File(self.ref, "en-reference.dtd", ""),
                   File(l10n, "l10n.dtd", ""))
        print obs.serialize()
    def testMissing(self):
        self.assertTrue(os.path.isdir(self.tmp))
        l10n = os.path.join(self.tmp, "l10n.dtd")
        open(l10n, "w").write("""<!ENTITY bar 'lBar'>
""")
        obs = Observer()
        cc = ContentComparer(obs)
        cc.set_merge_stage(os.path.join(self.tmp, "merge"))
        cc.compare(File(self.ref, "en-reference.dtd", ""),
                   File(l10n, "l10n.dtd", ""))
        print obs.serialize()
        mergefile = os.path.join(self.tmp, "merge", "l10n.dtd")
        self.assertTrue(os.path.isfile(mergefile))
        p = getParser(mergefile)
        p.readFile(mergefile)
        [m,n] = p.parse()
        self.assertEqual(map(lambda e:e.key,m), ["bar", "eff", "foo"])

if __name__ == '__main__':
  unittest.main()
