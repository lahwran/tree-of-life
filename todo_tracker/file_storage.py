from crow2.adapterutil import adapter_for, IString, IFile
from zope.interface import implementer

from todo_tracker.tracker import IParser, ISerializer, LoadError

parsing_indent = 0
parsing_type = 1
parsing_type_text_sep = 2
parsing_text = 3

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

#        if char == "\n":
#            continue
                
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

@adapter_for(IString)
@implementer(IParser)
def parse_string(string):
    return parse_file(string.split('\n'))

@adapter_for(IFile)
@implementer(IParser)
def parse_file(reader):
    for line in reader:
        if not line:
            continue
        yield parse_line(line)

def serialize(tree, is_root=False):
    lines = []
    if is_root:
        indent = ""
    else:
        indent = " " * 4


        if tree.text:
            text_lines = tree.text.split("\n")
            lines.append("%s: %s" % (tree.node_type, text_lines[0]))
            for line in text_lines[1:]:
                lines.append(indent + "- %s" % line)
        else:
            lines.append(tree.node_type)

    for name, value, show in tree.option_values():
        if not show:
            continue

        if value is None:
            lines.append("%s@%s" % (indent, name))
        else:
            value = IString(value)
            lines.append("%s@%s: %s" % (indent, name, value))

    for child in tree.children_export():
        for line in serialize(child):
            lines.append(indent + line)
    return lines

def serialize_to_str(root):
    lines = serialize(root, is_root=True)
    return '\n'.join(lines) + "\n"

@adapter_for(IFile)
@implementer(ISerializer)
class FileSerializer(object):
    def __init__(self, writer):
        self.writer = writer

    def serialize(self, root):
        self.writer.write(serialize_to_str(root))
