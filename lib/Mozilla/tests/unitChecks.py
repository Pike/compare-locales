import unittest

from Mozilla.Checks import getChecks
from Mozilla.Parser import getParser


class BaseHelper(unittest.TestCase):
    filename = None
    refContent = None

    def setUp(self):
        p = getParser(self.filename)
        p.readContents(self.refContent)
        self.refs = [e for e in p]

    def _test(self, content, refWarnOrErrors):
        p = getParser(self.filename)
        p.readContents(content)
        l10n = [e for e in p]
        checks = getChecks(self.filename)
        found = tuple(checks(self.refs[0], l10n[0]))
        self.assertEqual(found, refWarnOrErrors)


class TestPlurals(BaseHelper):
    filename = 'foo.properties'
    refContent = '''# LOCALIZATION NOTE (downloadsTitleFiles): Semi-colon list of plural forms.
# See: http://developer.mozilla.org/en/docs/Localization_and_Plurals
# #1 number of files
# example: 111 files - Downloads
downloadsTitleFiles=#1 file - Downloads;#1 files - #2
'''

    def testGood(self):
        self._test('''# LOCALIZATION NOTE (downloadsTitleFiles): Semi-colon list of plural forms.
# See: http://developer.mozilla.org/en/docs/Localization_and_Plurals
# #1 number of files
# example: 111 files - Downloads
downloadsTitleFiles=#1 file - Downloads;#1 files - #2;#1 filers
''',
                   tuple())

    def testNotUsed(self):
        self._test('''# LOCALIZATION NOTE (downloadsTitleFiles): Semi-colon list of plural forms.
# See: http://developer.mozilla.org/en/docs/Localization_and_Plurals
# #1 number of files
# example: 111 files - Downloads
downloadsTitleFiles=#1 file - Downloads;#1 files - Downloads;#1 filers
''',
                   (('warning', 0, 'not all variables used in l10n'),))

    def testNotDefined(self):
        self._test('''# LOCALIZATION NOTE (downloadsTitleFiles): Semi-colon list of plural forms.
# See: http://developer.mozilla.org/en/docs/Localization_and_Plurals
# #1 number of files
# example: 111 files - Downloads
downloadsTitleFiles=#1 file - Downloads;#1 files - #2;#1 #3
''',
                   (('error', 0, 'unreplaced variables in l10n'),))


class TestDTDs(BaseHelper):
    filename = 'foo.dtd'
    refContent = '''<!ENTITY foo "This is &apos;good&apos;">
'''
    def testWarning(self):
        self._test('''<!ENTITY foo "This is &not; good">
''',
                   (('warning',(0,0),'Referencing unknown entity `not`'),))
    def testXMLEntity(self):
        self._test('''<!ENTITY foo "This is &quot;good&quot;">
''',
                   tuple())


if __name__ == '__main__':
    unittest.main()
