# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import
from __future__ import unicode_literals
import re

from .base import (
    CAN_COPY,
    EntityBase, OffsetComment, Junk, Whitespace,
    Parser
)


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

    class Comment(OffsetComment):
        comment_offset = 2

    def __init__(self):
        self.reComment = re.compile('(?:^# .*?\n)*(?:^# [^\n]*)', re.M)
        # corresponds to
        # https://hg.mozilla.org/mozilla-central/file/72ee4800d4156931c89b58bd807af4a3083702bb/python/mozbuild/mozbuild/preprocessor.py#l561  # noqa
        self.reKey = re.compile(
            r'#define[ \t]+(?P<key>\w+)(?:[ \t](?P<val>[^\n]*))?', re.M)
        self.rePI = re.compile(r'#(?P<val>\w+[ \t]+[^\n]+)', re.M)
        Parser.__init__(self)

    def getNext(self, ctx, offset):
        junk_offset = offset
        contents = ctx.contents

        m = self.reComment.match(ctx.contents, offset)
        if m:
            current_comment = self.Comment(ctx, m.span())
            offset = m.end()
        else:
            current_comment = None

        m = self.reWhitespace.match(contents, offset)
        if m:
            # leading whitespace or blank lines outside of EMPTY_LINES are bad
            if (
                offset == 0 or
                not (len(m.group()) == 1 or ctx.state & self.EMPTY_LINES)
            ):
                if current_comment:
                    return current_comment
                return Junk(ctx, m.span())
            white_space = Whitespace(ctx, m.span())
            offset = m.end()
            if current_comment is None:
                return white_space
        else:
            white_space = None

        m = self.reKey.match(contents, offset)
        if m:
            return self.createEntity(ctx, m, current_comment, white_space)
        m = self.rePI.match(contents, offset)
        if m:
            if current_comment:
                return current_comment
            if white_space:
                return white_space
            instr = DefinesInstruction(ctx, m.span(), m.span('val'))
            if instr.val == 'filter emptyLines':
                ctx.state |= self.EMPTY_LINES
            if instr.val == 'unfilter emptyLines':
                ctx.state &= ~ self.EMPTY_LINES
            return instr
        return self.getJunk(
            ctx, junk_offset, self.reComment, self.reKey, self.rePI)
