# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import
from __future__ import unicode_literals
import re

try:
    from html import unescape as html_unescape
except ImportError:
    from HTMLParser import HTMLParser
    html_parser = HTMLParser()
    html_unescape = html_parser.unescape

from fluent.syntax import FluentParser as FTLParser
from fluent.syntax import ast as ftl
from .base import (
    CAN_NONE, CAN_COPY, CAN_SKIP, CAN_MERGE,
    EntityBase, Entity, Comment, OffsetComment, Junk, Whitespace,
    Parser
)
from six import unichr

__all__ = ["CAN_NONE", "CAN_COPY", "CAN_SKIP", "CAN_MERGE"]

__constructors = []


def getParser(path):
    for item in __constructors:
        if re.search(item[0], path):
            return item[1]
    raise UserWarning("Cannot find Parser")


class DTDEntity(Entity):
    @property
    def val(self):
        '''Unescape HTML entities into corresponding Unicode characters.

        Named (&amp;), decimal (&#38;), and hex (&#x26; and &#x0026;) formats
        are supported. Unknown entities are left intact.

        As of Python 2.7 and Python 3.6 the following 252 named entities are
        recognized and unescaped:

            https://github.com/python/cpython/blob/2.7/Lib/htmlentitydefs.py
            https://github.com/python/cpython/blob/3.6/Lib/html/entities.py
        '''
        return html_unescape(self.raw_val)

    def value_position(self, offset=0):
        # DTDChecker already returns tuples of (line, col) positions
        if isinstance(offset, tuple):
            line_pos, col_pos = offset
            line, col = super(DTDEntity, self).value_position()
            if line_pos == 1:
                col = col + col_pos
            else:
                col = col_pos
                line += line_pos - 1
            return line, col
        else:
            return super(DTDEntity, self).value_position(offset)


class DTDParser(Parser):
    # http://www.w3.org/TR/2006/REC-xml11-20060816/#NT-NameStartChar
    # ":" | [A-Z] | "_" | [a-z] |
    # [#xC0-#xD6] | [#xD8-#xF6] | [#xF8-#x2FF] | [#x370-#x37D] | [#x37F-#x1FFF]
    # | [#x200C-#x200D] | [#x2070-#x218F] | [#x2C00-#x2FEF] |
    # [#x3001-#xD7FF] | [#xF900-#xFDCF] | [#xFDF0-#xFFFD] |
    # [#x10000-#xEFFFF]
    CharMinusDash = '\x09\x0A\x0D\u0020-\u002C\u002E-\uD7FF\uE000-\uFFFD'
    XmlComment = '<!--(?:-?[%s])*?-->' % CharMinusDash
    NameStartChar = ':A-Z_a-z\xC0-\xD6\xD8-\xF6\xF8-\u02FF' + \
        '\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F' + \
        '\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD'
    # + \U00010000-\U000EFFFF seems to be unsupported in python

    # NameChar ::= NameStartChar | "-" | "." | [0-9] | #xB7 |
    #     [#x0300-#x036F] | [#x203F-#x2040]
    NameChar = NameStartChar + r'\-\.0-9' + '\xB7\u0300-\u036F\u203F-\u2040'
    Name = '[' + NameStartChar + '][' + NameChar + ']*'
    reKey = re.compile('<!ENTITY[ \t\r\n]+(?P<key>' + Name + ')[ \t\r\n]+'
                       '(?P<val>\"[^\"]*\"|\'[^\']*\'?)[ \t\r\n]*>',
                       re.DOTALL | re.M)
    # add BOM to DTDs, details in bug 435002
    reHeader = re.compile('^\ufeff')
    reComment = re.compile('<!--(?P<val>-?[%s])*?-->' % CharMinusDash,
                           re.S)
    rePE = re.compile('<!ENTITY[ \t\r\n]+%[ \t\r\n]+(?P<key>' + Name + ')'
                      '[ \t\r\n]+SYSTEM[ \t\r\n]+'
                      '(?P<val>\"[^\"]*\"|\'[^\']*\')[ \t\r\n]*>[ \t\r\n]*'
                      '%' + Name + ';'
                      '(?:[ \t]*(?:' + XmlComment + u'[ \t\r\n]*)*\n?)?')

    class Comment(Comment):
        @property
        def val(self):
            if self._val_cache is None:
                # Strip "<!--" and "-->" to comment contents
                self._val_cache = self.all[4:-3]
            return self._val_cache

    def getNext(self, ctx, offset):
        '''
        Overload Parser.getNext to special-case ParsedEntities.
        Just check for a parsed entity if that method claims junk.

        <!ENTITY % foo SYSTEM "url">
        %foo;
        '''
        if offset is 0 and self.reHeader.match(ctx.contents):
            offset += 1
        entity = Parser.getNext(self, ctx, offset)
        if (entity and isinstance(entity, Junk)) or entity is None:
            m = self.rePE.match(ctx.contents, offset)
            if m:
                self.last_comment = None
                entity = DTDEntity(
                    ctx, '', m.span(), m.span('key'), m.span('val'))
        return entity

    def createEntity(self, ctx, m):
        valspan = m.span('val')
        valspan = (valspan[0]+1, valspan[1]-1)
        pre_comment = self.last_comment
        self.last_comment = None
        return DTDEntity(ctx, pre_comment,
                         m.span(), m.span('key'), valspan)


class PropertiesEntity(Entity):
    escape = re.compile(r'\\((?P<uni>u[0-9a-fA-F]{1,4})|'
                        '(?P<nl>\n[ \t]*)|(?P<single>.))', re.M)
    known_escapes = {'n': '\n', 'r': '\r', 't': '\t', '\\': '\\'}

    @property
    def val(self):
        def unescape(m):
            found = m.groupdict()
            if found['uni']:
                return unichr(int(found['uni'][1:], 16))
            if found['nl']:
                return ''
            return self.known_escapes.get(found['single'], found['single'])

        return self.escape.sub(unescape, self.raw_val)


class PropertiesParser(Parser):

    Comment = OffsetComment

    def __init__(self):
        self.reKey = re.compile(
            '(?P<key>[^#! \t\r\n][^=:\n]*?)[ \t]*[:=][ \t]*', re.M)
        self.reComment = re.compile('(?:[#!][^\n]*\n)*(?:[#!][^\n]*)', re.M)
        self._escapedEnd = re.compile(r'\\+$')
        self._trailingWS = re.compile(r'[ \t\r\n]*(?:\n|\Z)', re.M)
        Parser.__init__(self)

    def getNext(self, ctx, offset):
        # overwritten to parse values line by line
        contents = ctx.contents

        m = self.reWhitespace.match(contents, offset)
        if m:
            return Whitespace(ctx, m.span())

        m = self.reComment.match(contents, offset)
        if m:
            self.last_comment = self.Comment(ctx, m.span())
            return self.last_comment

        m = self.reKey.match(contents, offset)
        if m:
            startline = offset = m.end()
            while True:
                endval = nextline = contents.find('\n', offset)
                if nextline == -1:
                    endval = offset = len(contents)
                    break
                # is newline escaped?
                _e = self._escapedEnd.search(contents, offset, nextline)
                offset = nextline + 1
                if _e is None:
                    break
                # backslashes at end of line, if 2*n, not escaped
                if len(_e.group()) % 2 == 0:
                    break
                startline = offset

            # strip trailing whitespace
            ws = self._trailingWS.search(contents, startline)
            if ws:
                endval = ws.start()

            pre_comment = self.last_comment
            self.last_comment = None
            entity = PropertiesEntity(
                ctx, pre_comment,
                (m.start(), endval),   # full span
                m.span('key'),
                (m.end(), endval))   # value span
            return entity

        return self.getJunk(ctx, offset, self.reKey, self.reComment)


class DefinesInstruction(EntityBase):
    '''Entity-like object representing processing instructions in inc files
    '''
    def __init__(self, ctx, span, val_span):
        self.ctx = ctx
        self.span = span
        self.key_span = self.val_span = val_span

    def __repr__(self):
        return self.raw_val


class DefinesParser(Parser):
    # can't merge, #unfilter needs to be the last item, which we don't support
    capabilities = CAN_COPY
    reWhitespace = re.compile('\n+', re.M)

    EMPTY_LINES = 1 << 0
    PAST_FIRST_LINE = 1 << 1

    class Comment(OffsetComment):
        comment_offset = 2

    def __init__(self):
        self.reComment = re.compile('(?:^# .*?\n)*(?:^# [^\n]*)', re.M)
        # corresponds to
        # https://hg.mozilla.org/mozilla-central/file/72ee4800d4156931c89b58bd807af4a3083702bb/python/mozbuild/mozbuild/preprocessor.py#l561  # noqa
        self.reKey = re.compile(
            '#define[ \t]+(?P<key>\w+)(?:[ \t](?P<val>[^\n]*))?', re.M)
        self.rePI = re.compile('#(?P<val>\w+[ \t]+[^\n]+)', re.M)
        Parser.__init__(self)

    def getNext(self, ctx, offset):
        contents = ctx.contents

        m = self.reWhitespace.match(contents, offset)
        if m:
            if ctx.state & self.EMPTY_LINES:
                return Whitespace(ctx, m.span())
            if ctx.state & self.PAST_FIRST_LINE and len(m.group()) == 1:
                return Whitespace(ctx, m.span())
            else:
                return Junk(ctx, m.span())

        # We're not in the first line anymore.
        ctx.state |= self.PAST_FIRST_LINE

        m = self.reComment.match(contents, offset)
        if m:
            self.last_comment = self.Comment(ctx, m.span())
            return self.last_comment
        m = self.reKey.match(contents, offset)
        if m:
            return self.createEntity(ctx, m)
        m = self.rePI.match(contents, offset)
        if m:
            instr = DefinesInstruction(ctx, m.span(), m.span('val'))
            if instr.val == 'filter emptyLines':
                ctx.state |= self.EMPTY_LINES
            if instr.val == 'unfilter emptyLines':
                ctx.state &= ~ self.EMPTY_LINES
            return instr
        return self.getJunk(
            ctx, offset, self.reComment, self.reKey, self.rePI)


class IniSection(EntityBase):
    '''Entity-like object representing sections in ini files
    '''
    def __init__(self, ctx, span, val_span):
        self.ctx = ctx
        self.span = span
        self.key_span = self.val_span = val_span

    def __repr__(self):
        return self.raw_val


class IniParser(Parser):
    '''
    Parse files of the form:
    # initial comment
    [cat]
    whitespace*
    #comment
    string=value
    ...
    '''

    Comment = OffsetComment

    def __init__(self):
        self.reComment = re.compile('(?:^[;#][^\n]*\n)*(?:^[;#][^\n]*)', re.M)
        self.reSection = re.compile('\[(?P<val>.*?)\]', re.M)
        self.reKey = re.compile('(?P<key>.+?)=(?P<val>.*)', re.M)
        Parser.__init__(self)

    def getNext(self, ctx, offset):
        contents = ctx.contents
        m = self.reWhitespace.match(contents, offset)
        if m:
            return Whitespace(ctx, m.span())
        m = self.reComment.match(contents, offset)
        if m:
            self.last_comment = self.Comment(ctx, m.span())
            return self.last_comment
        m = self.reSection.match(contents, offset)
        if m:
            return IniSection(ctx, m.span(), m.span('val'))
        m = self.reKey.match(contents, offset)
        if m:
            return self.createEntity(ctx, m)
        return self.getJunk(
            ctx, offset, self.reComment, self.reSection, self.reKey)


class FluentAttribute(EntityBase):
    ignored_fields = ['span']

    def __init__(self, entity, attr_node):
        self.ctx = entity.ctx
        self.attr = attr_node
        self.key_span = (attr_node.id.span.start, attr_node.id.span.end)
        self.val_span = (attr_node.value.span.start, attr_node.value.span.end)

    def equals(self, other):
        if not isinstance(other, FluentAttribute):
            return False
        return self.attr.equals(
            other.attr, ignored_fields=self.ignored_fields)


class FluentEntity(Entity):
    # Fields ignored when comparing two entities.
    ignored_fields = ['comment', 'span']

    def __init__(self, ctx, entry):
        start = entry.span.start
        end = entry.span.end

        self.ctx = ctx
        self.span = (start, end)

        self.key_span = (entry.id.span.start, entry.id.span.end)

        if entry.value is not None:
            self.val_span = (entry.value.span.start, entry.value.span.end)
        else:
            self.val_span = None

        self.entry = entry

        # EntityBase instances are expected to have pre_comment. It's used by
        # other formats to associate a Comment with an Entity. FluentEntities
        # don't need it because message comments are part of the entry AST and
        # are not separate Comment instances.
        self.pre_comment = None

    @property
    def root_node(self):
        '''AST node at which to start traversal for count_words.

        By default we count words in the value and in all attributes.
        '''
        return self.entry

    _word_count = None

    def count_words(self):
        if self._word_count is None:
            self._word_count = 0

            def count_words(node):
                if isinstance(node, ftl.TextElement):
                    self._word_count += len(node.value.split())
                return node

            self.root_node.traverse(count_words)

        return self._word_count

    def equals(self, other):
        return self.entry.equals(
            other.entry, ignored_fields=self.ignored_fields)

    # In Fluent we treat entries as a whole.  FluentChecker reports errors at
    # offsets calculated from the beginning of the entry.
    def value_position(self, offset=0):
        return self.position(offset)

    @property
    def attributes(self):
        for attr_node in self.entry.attributes:
            yield FluentAttribute(self, attr_node)


class FluentMessage(FluentEntity):
    pass


class FluentTerm(FluentEntity):
    # Fields ignored when comparing two terms.
    ignored_fields = ['attributes', 'comment', 'span']

    @property
    def root_node(self):
        '''AST node at which to start traversal for count_words.

        In Fluent Terms we only count words in the value. Attributes are
        private and do not count towards the word total.
        '''
        return self.entry.value


class FluentComment(Comment):
    def __init__(self, ctx, span, entry):
        super(FluentComment, self).__init__(ctx, span)
        self._val_cache = entry.content


class FluentParser(Parser):
    capabilities = CAN_SKIP

    def __init__(self):
        super(FluentParser, self).__init__()
        self.ftl_parser = FTLParser()

    def walk(self, only_localizable=False):
        if not self.ctx:
            # loading file failed, or we just didn't load anything
            return

        resource = self.ftl_parser.parse(self.ctx.contents)

        last_span_end = 0

        for entry in resource.body:
            if not only_localizable:
                if entry.span.start > last_span_end:
                    yield Whitespace(
                        self.ctx, (last_span_end, entry.span.start))

            if isinstance(entry, ftl.Message):
                yield FluentMessage(self.ctx, entry)
            elif isinstance(entry, ftl.Term):
                yield FluentTerm(self.ctx, entry)
            elif isinstance(entry, ftl.Junk):
                start = entry.span.start
                end = entry.span.end
                # strip leading whitespace
                start += re.match('[ \t\r\n]*', entry.content).end()
                # strip trailing whitespace
                ws, we = re.search('[ \t\r\n]*$', entry.content).span()
                end -= we - ws
                yield Junk(self.ctx, (start, end))
            elif isinstance(entry, ftl.BaseComment) and not only_localizable:
                span = (entry.span.start, entry.span.end)
                yield FluentComment(self.ctx, span, entry)

            last_span_end = entry.span.end

        # Yield Whitespace at the EOF.
        if not only_localizable:
            eof_offset = len(self.ctx.contents)
            if eof_offset > last_span_end:
                yield Whitespace(self.ctx, (last_span_end, eof_offset))


__constructors = [('\\.dtd$', DTDParser()),
                  ('\\.properties$', PropertiesParser()),
                  ('\\.ini$', IniParser()),
                  ('\\.inc$', DefinesParser()),
                  ('\\.ftl$', FluentParser())]
