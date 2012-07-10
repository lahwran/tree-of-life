import re
import collections

from crow2.util import paramdecorator

class _NodeCreatorTracker(object):
    def __init__(self):
        self.creators = {}

    def create(self, node_type, text, parent):
        return self.creators[node_type](node_type, text, parent, self)

    @paramdecorator
    def __call__(self, func, name=None):
        self.creators[name] = func
        return func

nodecreator = _NodeCreatorTracker()

@nodecreator('category')
class Tree(object):
    multiline = False
    options = ()

    def __init__(self, node_type, text, parent, tracker=None):
        self.text = text
        self.parent = parent
        self.metadata = None
        self.tracker = tracker

        self.node_type = node_type

        self.children = []

    def addchild(self, child):
        self.children.append(child)

    def setoption(self, option, value):
        if option not in self.options:
            raise Exception("no such option")
        setattr(self, option, value)

    def options_pairs(self):
        return [(name, getattr(self, name)) for name in self.options]

    def continue_text(self, text):
        if not self.multiline:
            raise Exception("multiline text not allowed")

        self.text += "\n"
        self.text += text

    def _serialize(self):
        indent = " " * 4

        lines = []

        if self.text:
            text_lines = self.text.split("\n")
            lines.append("%s: %s" % (self.node_type, text_lines[0]))
            for line in text_lines[1:]:
                lines.append(indent + "- %s" % line)
        else:
            lines.append(self.node_type)

        for item in self.metadata.items():
            lines.append("%s@%s: %s" % (indent, item[0], item[1]))

        for child in self.children:
            for line in child.serialize():
                lines.append(indent + line)
        return lines

    def __str__(self): # pragma: no cover
        return "Tree(%r, %r, ...)" % (self.node_type, self.text)

    def __repr__(self): # pragma: no cover
        selfrepr = "Tree(%r, %r, %s)\n    metadata: %r" % (self.node_type,
                self.text, self.parent, self.metadata)
        lines = []
        for child in self.children:
            for line in repr(child).split('\n'):
                lines.append(' '*4 + line)
        return "%s\n%s" % (selfrepr, "\n".join(lines))

@nodecreator("_genericnode")
class GenericNode(Tree):
    multiline = True

    def __init__

@nodecreator('-')
def continue_text(node_type, text, parent, self):
    parent.continue_text(text)

parsing_indent = 0
parsing_type = 1
parsing_type_text_sep = 2
parsing_text = 3

class LoadError(Exception):
    pass

def parse_line(line):
    parsing = 0
    indent = 0
    is_metadata = False

    node_type = ""
    text = None

    for char in line:
        last_parsing = parsing
        if parsing == parsing_indent:
            if char == " ":
                indent += 1
                continue
            else:
                if indent % 4 != 0:
                    raise LoadError("bad indentation")
                indent = indent / 4.0

                parsing += 1

        if char == "\n":
            continue
                
        if parsing == parsing_type:
            if last_parsing == parsing_indent:
                if char == "@":
                    is_metadata = True
                    continue
                elif char == "-":
                    node_type = "-"
                    parsing += 1
                    continue
            if char == ":":
                parsing += 1
                continue
                
            node_type += char
            continue

        if parsing == parsing_type_text_sep:
            if char != " ":
                raise LoadError("must be space separated")
            parsing += 1
            continue

        if text is None:
            text = ""

        text += char 
    return indent, is_metadata, node_type, text

class Tracker(object):
    def __init__(self, nodecreator=nodecreator):
        self.nodecreator = nodecreator
        self.root = Tree("root", "root", None, self)

    def load(self, reader):
        self.root.children = []
        stack = collections.deque()
        lastnode = self.root
        lastindent = -1
        metadata_allowed_here = False
        
        for line in reader:
            indent, is_metadata, node_type, text = parse_line(line)
            if indent > lastindent:
                stack.append(lastnode)
                metadata_allowed_here = True
            elif indent < lastindent:
                stack.pop()
            lastindent = indent

            parent = stack[-1]
        
            if is_metadata:
                if not metadata_allowed_here:
                    raise LoadError('metadata in the wrong place')
                parent.setoption(node_type, text)
                lastnode = None
            else:
                if node_type != "-":
                    metadata_allowed_here = False

                node = self.nodecreator.create(node_type, text, parent)
                if node is not None:
                    parent.addchild(node)
                lastnode = node

    def save(self, writer):
        lines = []
        for child in self.root.children:
            lines.extend(child.serialize())
        writer.write('\n'.join(lines))

import todo_tracker.nodes
