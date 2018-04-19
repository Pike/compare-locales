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
from .defines import (
    DefinesParser, DefinesInstruction
)
from .dtd import (
    DTDEntity, DTDParser
)
from .fluent import (
    FluentParser, FluentComment, FluentEntity, FluentMessage, FluentTerm,
)
from .properties import (
    PropertiesParser, PropertiesEntity
)

__all__ = [
    "CAN_NONE", "CAN_COPY", "CAN_SKIP", "CAN_MERGE",
    "Junk", "Entity", "Comment",
    "DefinesParser", "DefinesInstruction",
    "DTDEntity",
    "FluentComment", "FluentEntity", "FluentMessage", "FluentTerm",
    "PropertiesEntity",
]

__constructors = []


def getParser(path):
    for item in __constructors:
        if re.search(item[0], path):
            return item[1]
    raise UserWarning("Cannot find Parser")


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
