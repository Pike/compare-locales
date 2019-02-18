# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import
from __future__ import unicode_literals
import textwrap
import unittest

from compare_locales.tests import BaseHelper
from compare_locales.paths import File


def dedent_ftl(text):
    return textwrap.dedent(text.rstrip() + "\n").encode("utf-8")


REFERENCE = b'''\
simple = value
term_ref = some { -term }
  .attr = is simple
msg-attr-ref = some {button.label}
mixed-attr = value
  .and = attribute
only-attr =
  .one = exists
-term = value need
  .attrs = can differ
'''


class TestFluent(BaseHelper):
    file = File('foo.ftl', 'foo.ftl')
    refContent = REFERENCE

    def test_simple(self):
        self._test(b'''simple = localized''',
                   tuple())


class TestMessage(BaseHelper):
    file = File('foo.ftl', 'foo.ftl')
    refContent = REFERENCE

    def test_excess_attribute(self):
        self._test(
            dedent_ftl('''\
            simple = value with
                .obsolete = attribute
            '''),
            (
                (
                    'error', 24,
                    'Obsolete attribute: obsolete', 'fluent'
                ),
            )
        )

    def test_duplicate_attribute(self):
        self._test(
            dedent_ftl('''\
            only-attr =
                .one = attribute
                .one = again
                .one = three times
            '''),
            (
                (
                    'warning', 54,
                    'Attribute "one" occurs 3 times', 'fluent'
                ),
            )
        )

    def test_only_attributes(self):
        self._test(
            dedent_ftl('''\
            only-attr = obsolete value
            '''),
            (
                (
                    'error', 0,
                    'Missing attribute: one', 'fluent'
                ),
                (
                    'error', 12,
                    'Obsolete value', 'fluent'
                ),
            )
        )

    def test_missing_value(self):
        self._test(
            dedent_ftl('''\
            mixed-attr =
                .and = attribute exists
            '''),
            (
                (
                    'error', 0,
                    'Missing value', 'fluent'
                ),
            )
        )


class TestTerm(BaseHelper):
    file = File('foo.ftl', 'foo.ftl')
    refContent = REFERENCE

    def test_mismatching_attribute(self):
        self._test(
            dedent_ftl('''\
            -term = value with
                .different = attribute
            '''),
            tuple()
        )

    def test_duplicate_attribute(self):
        self._test(
            dedent_ftl('''\
            -term = need value
                .one = attribute
                .one = again
                .one = three times
            '''),
            (
                (
                    'warning', 61,
                    'Attribute "one" occurs 3 times', 'fluent'
                ),
            )
        )


class TestMessageReference(BaseHelper):
    file = File('foo.ftl', 'foo.ftl')
    refContent = REFERENCE

    def test_msg_attr(self):
        self._test(
            b'''msg-attr-ref = Nice {button.label}''',
            tuple()
        )
        self._test(
            b'''msg-attr-ref = not at all''',
            (
                (
                    'warning', 0,
                    'Missing message reference: button.label', 'fluent'
                ),
            )
        )
        self._test(
            b'''msg-attr-ref = {button} is not a label''',
            (
                (
                    'warning', 0,
                    'Missing message reference: button.label', 'fluent'
                ),
                (
                    'warning', 16,
                    'Obsolete message reference: button', 'fluent'
                ),
            )
        )
        self._test(
            b'''msg-attr-ref = {button.tooltip} is not a label''',
            (
                (
                    'warning', 0,
                    'Missing message reference: button.label', 'fluent'
                ),
                (
                    'warning', 16,
                    'Obsolete message reference: button.tooltip', 'fluent'
                ),
            )
        )


class TestTermReference(BaseHelper):
    file = File('foo.ftl', 'foo.ftl')
    refContent = REFERENCE

    def test_good_term_ref(self):
        self._test(
            dedent_ftl('''\
            term_ref = localized to {-term}
                .attr = is plain
            '''),
            tuple()
        )

    def test_missing_term_ref(self):
        self._test(
            dedent_ftl('''\
            term_ref = localized
                .attr = should not refer to {-term}
            '''),
            (
                (
                    'warning', 0,
                    'Missing term reference: -term', 'fluent'
                ),
                (
                    'warning', 54,
                    'Obsolete term reference: -term', 'fluent'
                ),
            )
        )

    def test_l10n_only_term_ref(self):
        self._test(
            b'''simple = localized with { -term }''',
            (
               (
                    u'warning', 26,
                    u'Obsolete term reference: -term', u'fluent'
                ),
            )
        )

    def test_term_attr(self):
        self._test(
            dedent_ftl('''\
            term_ref = Depends on { -term.prop ->
                *[some] Term prop, doesn't reference the term value, though.
              }
              .attr = still simple
            '''),
            (
                (
                    u'warning', 0,
                    u'Missing term reference: -term', u'fluent'
                ),
            )
        )

    def test_message_ref_variant(self):
        self._test(
            dedent_ftl('''\
            term_ref = localized with { -term[variant] }
                .attr = is simple
            '''),
            tuple()
        )


if __name__ == '__main__':
    unittest.main()
