import unittest
import os
import tempfile
import shutil

from compare_locales import mozpath
from compare_locales.paths import EnumerateApp

MAIL_INI = '''\
[general]
depth = ../..
all = mail/locales/all-locales

[compare]
dirs = mail

[includes]
# non-central apps might want to use %(topsrcdir)s here, or other vars
# RFE: that needs to be supported by compare-locales, too, though
toolkit = mozilla/toolkit/locales/l10n.ini

[include_toolkit]
type = hg
mozilla = mozilla-central
repo = http://hg.mozilla.org/
l10n.ini = toolkit/locales/l10n.ini
'''


MAIL_ALL_LOCALES = '''af
de
fr
'''

MAIL_FILTER_PY = '''
def test(mod, path, entity = None):
    if mod == 'toolkit' and path == 'ignored_path':
        return 'ignore'
    return 'error'
'''

TOOLKIT_INI = '''[general]
depth = ../..

[compare]
dirs = toolkit
'''


class TestApp(unittest.TestCase):
    def setUp(self):
        self.stage = tempfile.mkdtemp()
        mail = mozpath.join(self.stage, 'comm', 'mail', 'locales')
        toolkit = mozpath.join(
            self.stage, 'comm', 'mozilla', 'toolkit', 'locales')
        os.makedirs(mail)
        os.makedirs(toolkit)
        with open(mozpath.join(mail, 'l10n.ini'), 'w') as f:
            f.write(MAIL_INI)
        with open(mozpath.join(mail, 'all-locales'), 'w') as f:
            f.write(MAIL_ALL_LOCALES)
        with open(mozpath.join(mail, 'filter.py'), 'w') as f:
            f.write(MAIL_FILTER_PY)
        with open(mozpath.join(toolkit, 'l10n.ini'), 'w') as f:
            f.write(TOOLKIT_INI)

    def tearDown(self):
        shutil.rmtree(self.stage)

    def test_app(self):
        'Test parsing a App'
        app = EnumerateApp(
            mozpath.join(self.stage, 'comm', 'mail', 'locales', 'l10n.ini'),
            mozpath.join(self.stage, 'l10n-central'))
        self.assertListEqual(app.locales, ['af', 'de', 'fr'])
        self.assertEqual(len(app.config.children), 1)
