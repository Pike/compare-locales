"""
Parser for the .lang translation format.
"""
from __future__ import absolute_import

import re

from parsimonious.grammar import Grammar
from parsimonious.nodes import NodeVisitor

from compare_locales.parser.base import Comment, LiteralEntity, Junk, Parser
from compare_locales.paths import File


BLANK_LINE = 'blank_line'
TAG_REGEX = re.compile(r'\{(ok)\}', re.I)


class LangComment(Comment):
    def __init__(self, marker, content, end):
        self.marker = marker
        self.raw_content = content
        self.end = end

    @property
    def content(self):
        return self.raw_content.strip()

    @property
    def raw(self):
        return self.marker + self.raw_content + self.end


class LangEntity(LiteralEntity):
    def __init__(self, source_string, translation_string, all, tags):
        super(LangEntity, self).__init__(
            key=source_string,  # .lang files use the source as the key.
            val=translation_string,
            all=all,
        )

        self.tags = set(tags)

    @property
    def localized(self):
        return self.key != self.val or 'ok' in self.tags

    @property
    def extra(self):
        return {'tags': list(self.tags)}


class LangVisitor(NodeVisitor):
    grammar = Grammar(r"""
        lang_file = (comment / entity / blank_line)*

        comment = "#"+ line_content line_ending
        line_content = ~r".*"
        line_ending = ~r"$\n?"m # Match at EOL and EOF without newline.

        blank_line = ~r"((?!\n)\s)*" line_ending

        entity = string translation
        string = ";" line_content line_ending
        translation = line_content line_ending
    """)

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx

    def visit_lang_file(self, node, children):
        """
        Find comments that are associated with an entity and add them
        to the entity's comments list. Also assign order to entities.
        """
        comments = []
        order = 0
        for child in children:
            if isinstance(child, LangComment):
                comments.append(child)
                continue

            if isinstance(child, LangEntity):
                child.comments = [c.content for c in comments]
                child.order = order
                order += 1

            comments = []

        return children

    def visit_comment(self, node, node_info):
        marker, content, end = node_info
        return LangComment(
            node_text(marker), node_text(content), node_text(end)
        )

    def visit_blank_line(self, node, _):
        return BLANK_LINE

    def visit_entity(self, node, node_info):
        string, translation = node_info

        # Strip tags out of translation if they exist.
        tags = []
        tag_matches = list(re.finditer(TAG_REGEX, translation))
        if tag_matches:
            tags = [m.group(1).lower() for m in tag_matches]
            translation = translation[:tag_matches[0].start()].strip()

        if translation == '':
            return Junk(self.ctx, (0, 0))

        return LangEntity(string, translation, node.text, tags)

    def visit_string(self, node, node_info):
        marker, content, end = node_info
        return content.text.strip()

    def visit_translation(self, node, node_info):
        content, end = node_info
        return content.text.strip()

    def generic_visit(self, node, children):
        if children and len(children) == 1:
            return children[0]
        else:
            return children or node


def node_text(node):
    """
    Convert a Parsimonious node into text, including nodes that may
    actually be a list of nodes due to repetition.
    """
    if node is None:
        return u''
    elif isinstance(node, list):
        return ''.join([n.text for n in node])
    else:
        return node.text


class LangParser(Parser):
    def use(self, path):
        if isinstance(path, File):
            path = path.fullpath
        return path.endswith('.lang')

    def walk(self, only_localizable=False):
        if not self.ctx:
            # loading file failed, or we just didn't load anything
            return
        ctx = self.ctx
        contents = ctx.contents
        for c in LangVisitor(ctx).parse(contents):
            if not only_localizable or isinstance(c, (LangEntity, Junk)):
                yield c
