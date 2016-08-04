# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import os
from tempfile import mkdtemp
import shutil

from compare_locales.parser import getParser
from compare_locales.paths import File
from compare_locales.compare import ContentComparer


class ContentMixin(object):
    maxDiff = None  # we got big dictionaries to compare
    extension = None  # OVERLOAD

    def reference(self, content):
        self.ref = os.path.join(self.tmp, "en-reference" + self.extension)
        open(self.ref, "w").write(content)

    def localized(self, content):
        self.l10n = os.path.join(self.tmp, "l10n" + self.extension)
        open(self.l10n, "w").write(content)


class TestProperties(unittest.TestCase, ContentMixin):
    extension = '.properties'

    def setUp(self):
        self.tmp = mkdtemp()
        os.mkdir(os.path.join(self.tmp, "merge"))

    def tearDown(self):
        shutil.rmtree(self.tmp)
        del self.tmp

    def testGood(self):
        self.assertTrue(os.path.isdir(self.tmp))
        self.reference("""foo = fooVal
bar = barVal
eff = effVal""")
        self.localized("""foo = lFoo
bar = lBar
eff = lEff
""")
        cc = ContentComparer()
        cc.set_merge_stage(os.path.join(self.tmp, "merge"))
        cc.compare(File(self.ref, "en-reference.properties", ""),
                   File(self.l10n, "l10n.properties", ""))
        self.assertDictEqual(
            cc.observer.toJSON(),
            {'summary':
                {None: {
                    'changed': 3
                }},
             'details': {}
             }
        )
        self.assert_(not os.path.exists(os.path.join(cc.merge_stage,
                                                     'l10n.properties')))

    def testMissing(self):
        self.assertTrue(os.path.isdir(self.tmp))
        self.reference("""foo = fooVal
bar = barVal
eff = effVal""")
        self.localized("""bar = lBar
""")
        cc = ContentComparer()
        cc.set_merge_stage(os.path.join(self.tmp, "merge"))
        cc.compare(File(self.ref, "en-reference.properties", ""),
                   File(self.l10n, "l10n.properties", ""))
        self.assertDictEqual(
            cc.observer.toJSON(),
            {'summary':
                {None: {
                    'changed': 1, 'missing': 2
                }},
             'details': {
                 'children': [
                     ('l10n.properties',
                         {'value': {'missingEntity': [u'eff', u'foo']}}
                      )
                 ]}
             }
        )
        mergefile = os.path.join(self.tmp, "merge", "l10n.properties")
        self.assertTrue(os.path.isfile(mergefile))
        p = getParser(mergefile)
        p.readFile(mergefile)
        [m, n] = p.parse()
        self.assertEqual(map(lambda e: e.key,  m), ["bar", "eff", "foo"])


class TestDTD(unittest.TestCase, ContentMixin):
    extension = '.dtd'

    def setUp(self):
        self.tmp = mkdtemp()
        os.mkdir(os.path.join(self.tmp, "merge"))

    def tearDown(self):
        shutil.rmtree(self.tmp)
        del self.tmp

    def testGood(self):
        self.assertTrue(os.path.isdir(self.tmp))
        self.reference("""<!ENTITY foo 'fooVal'>
<!ENTITY bar 'barVal'>
<!ENTITY eff 'effVal'>""")
        self.localized("""<!ENTITY foo 'lFoo'>
<!ENTITY bar 'lBar'>
<!ENTITY eff 'lEff'>
""")
        cc = ContentComparer()
        cc.set_merge_stage(os.path.join(self.tmp, "merge"))
        cc.compare(File(self.ref, "en-reference.dtd", ""),
                   File(self.l10n, "l10n.dtd", ""))
        self.assertDictEqual(
            cc.observer.toJSON(),
            {'summary':
                {None: {
                    'changed': 3
                }},
             'details': {}
             }
        )
        self.assert_(
            not os.path.exists(os.path.join(cc.merge_stage, 'l10n.dtd')))

    def testMissing(self):
        self.assertTrue(os.path.isdir(self.tmp))
        self.reference("""<!ENTITY foo 'fooVal'>
<!ENTITY bar 'barVal'>
<!ENTITY eff 'effVal'>""")
        self.localized("""<!ENTITY bar 'lBar'>
""")
        cc = ContentComparer()
        cc.set_merge_stage(os.path.join(self.tmp, "merge"))
        cc.compare(File(self.ref, "en-reference.dtd", ""),
                   File(self.l10n, "l10n.dtd", ""))
        self.assertDictEqual(
            cc.observer.toJSON(),
            {'summary':
                {None: {
                    'changed': 1, 'missing': 2
                }},
             'details': {
                 'children': [
                     ('l10n.dtd',
                         {'value': {'missingEntity': [u'eff', u'foo']}}
                      )
                 ]}
             }
        )
        mergefile = os.path.join(self.tmp, "merge", "l10n.dtd")
        self.assertTrue(os.path.isfile(mergefile))
        p = getParser(mergefile)
        p.readFile(mergefile)
        [m, n] = p.parse()
        self.assertEqual(map(lambda e: e.key,  m), ["bar", "eff", "foo"])

if __name__ == '__main__':
    unittest.main()
