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
           u'This is the first \\\nof two lines',
           r'This line ends in \\']
    i = iter(self.p)
    for r, e in zip(ref, i):
      self.assertEqual(e.val, r)
    e = i.next()
    self.assertEqual(e.key, '_junk_1_113-126')
    for r, e in zip(('This line is one of two and ends in \\\\\\\nand still has another line coming',), i):
      self.assertEqual(e.val, r)

if __name__ == '__main__':
  unittest.main()
