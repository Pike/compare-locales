import unittest
import re

from Mozilla.Parser import getParser, Junk

class TestDTD(unittest.TestCase):

    def testGood(self):
        self._test('''<!ENTITY foo.label "stuff">''',
                   (('foo.label','stuff'),))


    quoteContent = '''<!ENTITY good.one "one">
<!ENTITY bad.one "bad " quote">
<!ENTITY good.two "two">
<!ENTITY bad.two "bad "quoted" word">
<!ENTITY good.three "three">
<!ENTITY good.four "good ' quote">
<!ENTITY good.five "good 'quoted' word">
'''
    quoteRef = (
        ('good.one', 'one'),
        ('_junk_1_25-56', '<!ENTITY bad.one "bad " quote">'),
        ('good.two', 'two'),
        ('_junk_2_82-119', '<!ENTITY bad.two "bad "quoted" word">'),
        ('good.three', 'three'),
        ('good.four', 'good \' quote'),
        ('good.five', 'good \'quoted\' word'),
        )
    def testQuote(self):
        self._test(self.quoteContent, self.quoteRef)

    def testApos(self):
        qr = re.compile('[\'"]', re.M)
        def quot2apos(s):
            return qr.sub(lambda m: m.group(0)=='"' and "'" or '"', s)
            
        self._test(quot2apos(self.quoteContent), 
                   map(lambda t: (t[0], quot2apos(t[1])), self.quoteRef))

    def _test(self, content, refs):
        p = getParser('foo.dtd')
        Junk.junkid = 0
        p.readContents(content)
        entities = [e for e in p]
        self.assertEqual(len(entities), len(refs))
        for e, ref in zip(entities, refs):
            self.assertEqual(e.val, ref[1])
            self.assertEqual(e.key, ref[0])

if __name__ == '__main__':
  unittest.main()
