# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import os
from tempfile import mkdtemp
import shutil

from compare_locales.parser import getParser
from compare_locales.paths import File
from compare_locales.compare import ContentComparer, Observer
from compare_locales import mozpath


class ContentMixin(object):
    extension = None  # OVERLOAD

    def reference(self, content):
        self.ref = mozpath.join(self.tmp, "en-reference" + self.extension)
        open(self.ref, "w").write(content)

    def localized(self, content):
        self.l10n = mozpath.join(self.tmp, "l10n" + self.extension)
        open(self.l10n, "w").write(content)


class TestProperties(unittest.TestCase, ContentMixin):
    extension = '.properties'

    def setUp(self):
        self.maxDiff = None
        self.tmp = mkdtemp()
        os.mkdir(mozpath.join(self.tmp, "merge"))

    def tearDown(self):
        shutil.rmtree(self.tmp)
        del self.tmp

    def testGood(self):
        self.assertTrue(os.path.isdir(self.tmp))
        self.reference("""foo = fooVal word
bar = barVal word
eff = effVal""")
        self.localized("""foo = lFoo
bar = lBar
eff = lEff word
""")
        cc = ContentComparer([Observer()])
        cc.compare(File(self.ref, "en-reference.properties", ""),
                   File(self.l10n, "l10n.properties", ""),
                   mozpath.join(self.tmp, "merge", "l10n.properties"))
        self.assertDictEqual(
            cc.observers[0].toJSON(),
            {'summary':
                {None: {
                    'changed': 3,
                    'changed_w': 5
                }},
             'details': {}
             }
        )
        self.assert_(not os.path.exists(mozpath.join(self.tmp, "merge",
                                                     'l10n.properties')))

    def testMissing(self):
        self.assertTrue(os.path.isdir(self.tmp))
        self.reference("""foo = fooVal
bar = barVal
eff = effVal""")
        self.localized("""bar = lBar
""")
        cc = ContentComparer([Observer()])
        cc.compare(File(self.ref, "en-reference.properties", ""),
                   File(self.l10n, "l10n.properties", ""),
                   mozpath.join(self.tmp, "merge", "l10n.properties"))
        self.assertDictEqual(
            cc.observers[0].toJSON(),
            {'summary':
                {None: {
                    'changed': 1,
                    'changed_w': 1,
                    'missing': 2,
                    'missing_w': 2
                }},
             'details': {
                 'l10n.properties': [
                     {'missingEntity': u'foo'},
                     {'missingEntity': u'eff'}]
                }
             })
        mergefile = mozpath.join(self.tmp, "merge", "l10n.properties")
        self.assertTrue(os.path.isfile(mergefile))
        p = getParser(mergefile)
        p.readFile(mergefile)
        [m, n] = p.parse()
        self.assertEqual(map(lambda e: e.key,  m), ["bar", "foo", "eff"])

    def testError(self):
        self.assertTrue(os.path.isdir(self.tmp))
        self.reference("""foo = fooVal
bar = %d barVal
eff = effVal""")
        self.localized("""\
bar = %S lBar
eff = leffVal
""")
        cc = ContentComparer([Observer()])
        cc.compare(File(self.ref, "en-reference.properties", ""),
                   File(self.l10n, "l10n.properties", ""),
                   mozpath.join(self.tmp, "merge", "l10n.properties"))
        self.assertDictEqual(
            cc.observers[0].toJSON(),
            {'summary':
                {None: {
                    'changed': 2,
                    'changed_w': 3,
                    'errors': 1,
                    'missing': 1,
                    'missing_w': 1
                }},
             'details': {
                 'l10n.properties': [
                     {'missingEntity': u'foo'},
                     {'error': u'argument 1 `S` should be `d` '
                               u'at line 1, column 7 for bar'}]
                }
             })
        mergefile = mozpath.join(self.tmp, "merge", "l10n.properties")
        self.assertTrue(os.path.isfile(mergefile))
        p = getParser(mergefile)
        p.readFile(mergefile)
        [m, n] = p.parse()
        self.assertEqual([e.key for e in m], ["eff", "foo", "bar"])
        self.assertEqual(m[n['bar']].val, '%d barVal')

    def testObsolete(self):
        self.assertTrue(os.path.isdir(self.tmp))
        self.reference("""foo = fooVal
eff = effVal""")
        self.localized("""foo = fooVal
other = obsolete
eff = leffVal
""")
        cc = ContentComparer([Observer()])
        cc.compare(File(self.ref, "en-reference.properties", ""),
                   File(self.l10n, "l10n.properties", ""),
                   mozpath.join(self.tmp, "merge", "l10n.properties"))
        self.assertDictEqual(
            cc.observers[0].toJSON(),
            {'summary':
                {None: {
                    'changed': 1,
                    'changed_w': 1,
                    'obsolete': 1,
                    'unchanged': 1,
                    'unchanged_w': 1
                }},
             'details': {
                 'l10n.properties': [
                     {'obsoleteEntity': u'other'}]
                }
             })


class TestDTD(unittest.TestCase, ContentMixin):
    extension = '.dtd'

    def setUp(self):
        self.maxDiff = None
        self.tmp = mkdtemp()
        os.mkdir(mozpath.join(self.tmp, "merge"))

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
        cc = ContentComparer([Observer()])
        cc.compare(File(self.ref, "en-reference.dtd", ""),
                   File(self.l10n, "l10n.dtd", ""),
                   mozpath.join(self.tmp, "merge", "l10n.dtd"))
        self.assertDictEqual(
            cc.observers[0].toJSON(),
            {'summary':
                {None: {
                    'changed': 3,
                    'changed_w': 3
                }},
             'details': {}
             }
        )
        self.assert_(
            not os.path.exists(mozpath.join(self.tmp, "merge", 'l10n.dtd')))

    def testMissing(self):
        self.assertTrue(os.path.isdir(self.tmp))
        self.reference("""<!ENTITY foo 'fooVal'>
<!ENTITY bar 'barVal'>
<!ENTITY eff 'effVal'>""")
        self.localized("""<!ENTITY bar 'lBar'>
""")
        cc = ContentComparer([Observer()])
        cc.compare(File(self.ref, "en-reference.dtd", ""),
                   File(self.l10n, "l10n.dtd", ""),
                   mozpath.join(self.tmp, "merge", "l10n.dtd"))
        self.assertDictEqual(
            cc.observers[0].toJSON(),
            {'summary':
                {None: {
                    'changed': 1,
                    'changed_w': 1,
                    'missing': 2,
                    'missing_w': 2
                }},
             'details': {
                 'l10n.dtd': [
                     {'missingEntity': u'foo'},
                     {'missingEntity': u'eff'}]
                }
             })
        mergefile = mozpath.join(self.tmp, "merge", "l10n.dtd")
        self.assertTrue(os.path.isfile(mergefile))
        p = getParser(mergefile)
        p.readFile(mergefile)
        [m, n] = p.parse()
        self.assertEqual(map(lambda e: e.key,  m), ["bar", "foo", "eff"])

    def testJunk(self):
        self.assertTrue(os.path.isdir(self.tmp))
        self.reference("""<!ENTITY foo 'fooVal'>
<!ENTITY bar 'barVal'>
<!ENTITY eff 'effVal'>""")
        self.localized("""<!ENTITY foo 'fooVal'>
<!ENTY bar 'gimmick'>
<!ENTITY eff 'effVal'>
""")
        cc = ContentComparer([Observer()])
        cc.compare(File(self.ref, "en-reference.dtd", ""),
                   File(self.l10n, "l10n.dtd", ""),
                   mozpath.join(self.tmp, "merge", "l10n.dtd"))
        self.assertDictEqual(
            cc.observers[0].toJSON(),
            {'summary':
                {None: {
                    'errors': 1,
                    'missing': 1,
                    'missing_w': 1,
                    'unchanged': 2,
                    'unchanged_w': 2
                }},
             'details': {
                 'l10n.dtd': [
                     {'missingEntity': u'bar'},
                     {'error': u'Unparsed content "<!ENTY bar '
                               u'\'gimmick\'>" '
                               u'from line 2 column 1 to '
                               u'line 2 column 22'}]
                }
             })
        mergefile = mozpath.join(self.tmp, "merge", "l10n.dtd")
        self.assertTrue(os.path.isfile(mergefile))
        p = getParser(mergefile)
        p.readFile(mergefile)
        [m, n] = p.parse()
        self.assertEqual(map(lambda e: e.key,  m), ["foo", "eff", "bar"])


if __name__ == '__main__':
    unittest.main()
