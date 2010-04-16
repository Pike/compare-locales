import unittest

from Mozilla.Checks import getChecks
from Mozilla.Parser import getParser

class TestPlurals(unittest.TestCase):
    def setUp(self):
        p = getParser('foo.properties')
        p.readContents('''# LOCALIZATION NOTE (downloadsTitleFiles): Semi-colon list of plural forms.
# See: http://developer.mozilla.org/en/docs/Localization_and_Plurals
# #1 number of files
# example: 111 files - Downloads
downloadsTitleFiles=#1 file - Downloads;#1 files - #2
''')
        self.refs = [e for e in p]

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

    def _test(self, content, refWarnOrErrors):
        p = getParser('foo.properties')
        p.readContents(content)
        l10n = [e for e in p]
        checks = getChecks('foo.properties')
        found = tuple(checks(self.refs[0], l10n[0]))
        self.assertEqual(found, refWarnOrErrors)

if __name__ == '__main__':
  unittest.main()
