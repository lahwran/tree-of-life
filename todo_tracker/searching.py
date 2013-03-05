# Note: a lot of classes here seem to "not be classes",
# in the terms of the "stop writing classes" talk. however,
# almost all of them are *used as data* by other code, hence
# why there are classes that look like they're used as functions.
from todo_tracker import parseutil
from todo_tracker.util import HandlerList

from collections import namedtuple

_Node = namedtuple('Node', 'rel, type, text')
_TaggedPattern = namedtuple('TaggedPattern', 'pat, tags')


class JoinedSearch(object):
    def __init__(self, initial, following):
        self.segments = [initial] + list(following)

    def __call__(self, nodes):
        if getattr(nodes, "node_type", None) is not None:
            nodes = [nodes]

        for segment in self.segments:
            nodes = segment(nodes)

        return nodes

pluralities = set(["many", "first", "last"])


def split_tags(orig_tags):
    tags = set()
    plurality = None
    for tag in orig_tags:
        if tag in pluralities:
            assert plurality is None
            plurality = tag
        else:
            tags.add(tag)
    return tags, plurality

retrievers = HandlerList()


def make_segment(separator, pattern, tags):
    from todo_tracker.nodes.node import nodecreator

    tags, plurality = split_tags(tags)

    rel, type, text = pattern
    if text is None:
        if type == "*":
            matcher = None
        elif nodecreator.exists(type):
            matcher = Matcher(type, "*")
        else:
            matcher = Matcher("*", type)
    else:
        matcher = Matcher(type, text, rel=rel)

    retriever = retrievers.handlers["retriever_" + separator]

    return Segment(separator, pattern,
            retriever, matcher, tags, plurality)


class SearchGrammar(parseutil.Grammar):
    grammar = """
    ws = ' '+
    text = <(~separator ~tags_begin ~': ' anything)+>

    createrel = '+' | '-' | -> 'default'
    node_base = ws? createrel:rel ('*' | ~'*' text):node
                (~tags_begin ws? ':' ws ('*' | ~'*' text))?:text
                -> Node(rel, node, text)
                | -> Node('default', '*', None)

    tagged_node = node_base:pattern (tags | -> ()):tags -> pattern, tags
    matcher :sep = tagged_node:p -> make_segment(sep, p[0], p[1])

    tags_begin = ws? ':{'
    tags_end = ws? '}'
    tags_sep = ws? ','
    tag_text = <(~tags_end ~tags_sep anything)+>
    tag_texts = ws? tag_text:tag1 (tags_sep ws? tag_text)*:tags
                -> (tag1,) + tuple(tags)
    tags = tags_begin tag_texts:tags tags_end -> tags


    separator = (ws? '->' -> "next_peer")
                | (ws? '<-' -> "prev_peer")
                | (ws? ('>' ws?)? '**' (ws? '>')? -> "flatten")
                | (ws? '>' -> "children")
                | (ws? '<' -> "parents")

    query = (separator | -> 'children'):initial_sep
            matcher(initial_sep):initial
            (separator:sep matcher(sep))*:following
            -> JoinedSearch(initial, following)

    """
    bindings = {
        "Node": _Node,
        "TaggedPattern": _TaggedPattern,
        "JoinedSearch": JoinedSearch,
        "make_segment": make_segment
    }

query = SearchGrammar.wraprule("query")


class Creator(object):
    def __init__(self, querytext):
        self.joinedsearch = query(querytext)

        segment = joinedsearch.segments.pop()
        assert segment.matcher is not None, (
                "cannot create node without full node")
        assert segment.matcher.is_rigid, "cannot create node without full node"
        assert segment.separator != "parents", "cannot create parent node"

        rel = segment.matcher.create_relationship
        if rel == "default":
            new_tags = set(segment.tags)
            new_tags.add(segment.plurality)
            if "before" in new_tags:
                assert "after" not in tags
                new_tags.remove("before")
                self.is_before = True
            elif "after" in new_tags:
                new_tags.remove("after")
                self.is_before = False
            else:
                self.is_before = True
                new_tags.add("unstarted")
        else:
            assert not last.tags, "conflict between rel shortcut and tags"
            assert segment.plurality is None, (
                    "conflict between rel shortcut and tags")
            is_last = (rel == "+")

            if segment.separator == "prev_peer":
                # invert order for prev_peer
                is_last = not is_last

            if is_last:
                new_tags = set(["last"])
                self.is_before = False
            else:
                new_tags = set(["first"])
                self.is_before = True

        self.node_type = segment.matcher.type
        self.text = segment.matcher.text

        new_last = make_segment(last.separator, "*", new_tags)
        self.joinedsearch.segments.append(new_last)

    def __call__(self, nodes):
        nodes = list(self.joinedsearch(nodes))

        for node in nodes:
            if self.is_before:
                rel = {"before": node}
            else:
                rel = {"after": node}

            node.parent.create_child(self.node_type, **rel)


@retrievers.add()
def retriever_children(nodes):
    for node in nodes:
        for child in node.children:
            yield child


@retrievers.add()
def retriever_flatten(nodes):
    for node in nodes:
        for depth, subnode in node.iter_flat_children():
            yield subnode


@retrievers.add()
def retriever_next_peer(nodes):
    for node in nodes:
        for peer in node.iter_forward():
            assert peer is not node
            yield peer


@retrievers.add()
def retriever_prev_peer(nodes):
    for node in nodes:
        for peer in node.iter_backward():
            assert peer is not node
            yield peer


@retrievers.add()
def retriever_parents(nodes):
    for node in nodes:
        for parent in node.iter_parents():
            if parent is node:
                continue
            yield parent


def tag_filter(nodes, tags):
    tags = set(tags)
    for node in nodes:
        if tags <= set(node.search_tags()):
            yield node


class Matcher(object):
    def __init__(self, type, text, rel="default"):
        self.type = None if type == "*" else type
        self.text = None if text == "*" else text
        self.create_relationship = rel

        self.is_rigid = self.type is not None and self.text is not None
        if not self.is_rigid:
            assert rel == "default"

    def __call__(self, nodes):
        for node in nodes:
            node_types, texts = node.search_texts()
            if self.type is not None and self.type not in node_types:
                continue
            if self.text is not None and self.text not in texts:
                continue
            yield node


class Segment(object):
    def __init__(self, separator, pattern,
            retriever, matcher, tags, plurality):
        self.separator = separator
        self.pattern = pattern

        self.retriever = retriever
        self.matcher = matcher
        self.tags = tags
        self.plurality = plurality

    def __call__(self, nodes):
        nodes = self.retriever(nodes)
        if self.matcher is not None:
            nodes = self.matcher(nodes)

        if self.tags:
            nodes = tag_filter(nodes, self.tags)

        if self.plurality == "last":
            for node in nodes:
                pass
            yield node
        elif self.plurality == "first":
            for node in nodes:  # pragma: no branch
                yield node
                break
        else:
            for node in nodes:
                yield node


if __name__ == "__main__":
    todofile = "/Users/lahwran/.todo_tracker/life"
    from todo_tracker.tracker import Tracker
    tracker = Tracker()
    with open(todofile, "r") as reader:
        tracker.deserialize("file", reader)

    while True:
        querytext = raw_input("query: ")
        import subprocess
        subprocess.call(["clear"])
        print "query:", querytext
        queryer = query(querytext)


        for x in queryer(tracker.root):
            print " > ".join([str(node) for node in x.iter_parents()][::-1])
