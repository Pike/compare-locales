from __future__ import absolute_import, unicode_literals

import unittest
from compare_locales import parser
from parsimonious.exceptions import ParseError


class TestLangParser(unittest.TestCase):
    def test_good(self):
        p = parser.getParser('foo.lang')
        p.readUnicode('''\
# Sample comment
;Source String
Translated String

# First comment
# Second comment
;Multiple Comments
Translated Multiple Comments

;No Comments or Sources
Translated No Comments or Sources
''')
        msgs = p.parse()
        self.assertEqual(len(msgs), 3)

    def test_empty_translation(self):
        p = parser.getParser('foo.lang')
        p.readUnicode('''\
# Sample comment
;Source String

''')
        msgs = p.parse()
        self.assertEqual(len(msgs), 1)
        self.assertIsInstance(msgs[0], parser.Junk)

    def test_bad(self):
        p = parser.getParser('foo.lang')
        p.readUnicode('''\
just garbage
''')
        with self.assertRaises(ParseError):
            p.parse()
