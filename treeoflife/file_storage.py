from __future__ import unicode_literals, print_function

import string
import json
import datetime

from treeoflife.exceptions import LoadError
from treeoflife.util import HandlerDict


# would making this a set speed it up?
nodeidchars = unicode(string.letters + string.digits)


def parse_line(line):
    assert type(line) == unicode

    parsing_indent = 0
    parsing_type = 1
    parsing_id = 2
    parsing_type_text_sep = 3
    parsing_text = 4

    parsing = 0
    indent = 0
    id = None
    is_metadata = False

    node_type = u""
    text = None

    if line.strip() == u"":
        return 0, False, None, u"", None

    for char in line:
        last_parsing = parsing
        if parsing == parsing_indent:
            if char == u" ":
                indent += 1
                continue
            else:
                if indent % 4 != 0:
                    raise LoadError("bad indentation")
                indent = indent / 4.0

                parsing += 1

        if char == u"\n":  # pragma: no cover
            continue

        if parsing == parsing_type:
            if last_parsing == parsing_indent:
                if char == "@":
                    is_metadata = True
                    continue
                elif char == u"-":
                    node_type = u"-"
                    parsing = parsing_type_text_sep
                    continue
            if char == u":":
                parsing = parsing_type_text_sep
                continue
            if char == u"#":
                parsing = parsing_id
                continue

            node_type += char
            continue

        if parsing == parsing_id:
            if id is None:
                id = u""
            if char == u":":
                parsing += 1
                continue
            elif char not in nodeidchars:
                raise LoadError("node id must be a-zA-Z0-9, got: %s%s" %
                        (id, char))
            id += char
            continue

        if parsing == parsing_type_text_sep:
            if char != u" ":
                raise LoadError("must be space separated")
            parsing += 1
            continue

        if text is None:
            text = u""

        text += char

    if id is not None and len(id) != 5:
        raise LoadError("node id must be exactly 5 long")
    if id is not None and is_metadata:
        raise LoadError("cannot have node IDs on metadata")

    return indent, is_metadata, id, node_type, text


def parse_string(string):
    assert type(string) == unicode
    return FileParser(string.split(u'\n'), decode=False)


class FileParser(object):
    def __init__(self, reader, decode=True):
        self.reader = reader
        self.error_context = None
        self.decode = decode

    def __iter__(self):
        return parse_file(self.reader, self.error_context, decode=self.decode)


def parse_file(reader, error_context, decode=True):
    reader = list(reader)
    for index, line in enumerate(reader):
        error_context.line = index
        if decode:
            line = line.decode("utf-8")
        if index == len(reader) - 1 and not line:
            continue
        yield parse_line(line)


def serialize(tree, is_root=False, one_line=False):
    lines = []
    if is_root:
        indent = u""
    else:
        indent = u" " * 4

        if tree.node_type == u"":
            lines.append(u"")
        elif tree.text:
            text_lines = tree.text.split("\n")
            lines.append(u"%s#%s: %s" % (tree.node_type,
                tree.id, text_lines[0]))
            for line in text_lines[1:]:
                lines.append(indent + "- %s" % line)
        else:
            lines.append(u"%s#%s" % (tree.node_type, tree.id))

    for name, value, show in tree.option_values():
        if not show:
            continue

        if value is None:
            lines.append(u"%s@%s" % (indent, name))
        else:
            lines.append(u"%s@%s: %s" % (indent, name, value))

    for child in tree.children_export():
        for line in serialize(child):
            lines.append(indent + line)
    return lines


def serialize_to_str(root, is_root=True):
    lines = serialize(root, is_root=is_root)
    return u'\n'.join(lines) + u"\n"

def dump_log(log):
    results = []
    for entry in log:
        path, event, date = entry
        date_formatted = date.replace(microsecond=0).isoformat(' ')
        date_formatted += date.strftime(' %A')
        path_formatted = []
        for id, type, text in path:
            if text is None:
                item = '{}#{}'.format(type, id)
            else:
                item = '{}#{}: {}'.format(type, id, text)
            path_formatted.append(item)
        dumped_path = json.dumps(path_formatted)
        result = '{} - {} - {}\n'.format(date_formatted, event, dumped_path)
        results.append(result)
    return ''.join(results)

def load_log(data):
    lines = data.split('\n')
    log = []
    for line in lines:
        if line == '':
            continue
        date_formatted, event, dumped_path = line.split(' - ', 2)
        path_formatted = json.loads(dumped_path)
        path = []
        for item in path_formatted:
            type, sep, id_and_text = item.partition('#')
            id, sep, text = id_and_text.partition(': ')
            if sep == '':
                text = None
            path.append((id, type, text))
        date = datetime.datetime.strptime(date_formatted, '%Y-%m-%d %H:%M:%S %A')
        entry = path, event, date
        log.append(entry)
    return log
