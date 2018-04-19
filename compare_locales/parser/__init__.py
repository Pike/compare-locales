# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import
from __future__ import unicode_literals
import re

from .base import (
    CAN_NONE, CAN_COPY, CAN_SKIP, CAN_MERGE,
    EntityBase, Entity, Comment, OffsetComment, Junk, Whitespace,
    Parser
)
from .dtd import (
    DTDEntity, DTDParser
)
from .fluent import (
    FluentParser, FluentComment, FluentEntity, FluentMessage, FluentTerm,
)
from six import unichr

__all__ = [
    "CAN_NONE", "CAN_COPY", "CAN_SKIP", "CAN_MERGE",
    "Comment",
    "DTDEntity",
    "FluentComment", "FluentEntity", "FluentMessage", "FluentTerm",
]

__constructors = []


def getParser(path):
    for item in __constructors:
        if re.search(item[0], path):
            return item[1]
    raise UserWarning("Cannot find Parser")


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


__constructors = [('\\.dtd$', DTDParser()),
                  ('\\.properties$', PropertiesParser()),
                  ('\\.ini$', IniParser()),
                  ('\\.inc$', DefinesParser()),
                  ('\\.ftl$', FluentParser())]
