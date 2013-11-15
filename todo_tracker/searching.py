# Note: a lot of classes here seem to "not be classes",
# in the terms of the "stop writing classes" talk. however,
# almost all of them are *used as data* by other code, hence
# why there are classes that look like they're used as functions.
from todo_tracker import parseutil
from todo_tracker.util import HandlerList, memoize
from todo_tracker import file_storage

from collections import namedtuple

_Node = namedtuple('Node', 'rel, type, text')
_TaggedPattern = namedtuple('TaggedPattern', 'pat, tags')


class JoinedSearch(object):
    def __init__(self, *segments):
        self.segments = tuple(segments)

    def __call__(self, nodes, counter=None):
        if getattr(nodes, "node_type", None) is not None:
            nodes = [nodes]

        if counter is None:
            counter = TickCounter()

        for segment in self.segments:
            nodes = segment(nodes, counter=counter)

        return nodes

    def __repr__(self):
        return "<query %r>" % (self.segments,)

pluralities = set(["many", "first", "last"])


def split_tags(orig_tags):
    tags = set()
    plurality = None
    for tag in orig_tags:
        if tag in pluralities:
            if not plurality is None:
                assert False
            plurality = tag
        else:
            tags.add(tag)
    return tags, plurality

retrievers = HandlerList()


def make_segment(separator, nodeid, pattern, tags):
    from todo_tracker.nodes.node import nodecreator

    if separator == "default":
        if nodeid is None:
            separator = "children"
        else:
            separator = "self"

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
            retriever, matcher, tags, plurality, nodeid=nodeid)


class SearchGrammar(parseutil.Grammar):
    grammar = r"""
    ws = ' '+
    text = <(~separator ~tags_begin ~': ' anything)+>
    quote = ('"' | "'")
    endquote :q = quote:q2 ?(q == q2)
    node_text = ((ws? quote:q
                    (('\\' ('\\' | quote):z -> z) | ~endquote(q) anything)+:r
                    endquote(q) ws? -> ''.join(r))
                | <(~separator ~tags_begin anything)+>)
    node_text_star = ('*' node_text? -> '*') | ~'*' node_text
    text_star = ('*' text? -> '*' ) | ~'*' text

    createrel = '+' | '-' | -> 'default'
    node_base = ws? createrel:rel ~"#" (text_star:node
                (~tags_begin ws? ':' ws node_text_star)?:text
                -> Node(rel, node, text)
                | -> Node(rel, '*', None))

    tagged_node = node_base:pattern (tags | -> ()):tags -> pattern, tags
    matcher :sep :nodeid = tagged_node:p
            -> make_segment(sep, nodeid, p[0], p[1])

    tags_begin = ws? ':{'
    tags_end = ws? '}' | ~~separator
    tags_sep = ws? ','
    tag_text = <(~tags_end ~tags_sep anything)+>
    tag_texts = ws? tag_text:tag1 (tags_sep ws? tag_text)*:tags
                -> (tag1,) + tuple(tags)
    tags = tags_begin tag_texts:tags tags_end -> tags


    separator = (ws? '->' -> "next_peer")
                | (ws? '<-' -> "prev_peer")
                | (ws? '<<' -> "root")
                | (ws? ('>' ws?)? '**' (ws? '>')? -> "flatten")
                | (ws? '>' -> "children")
                | (ws? '<' -> "parents")

    nodeidchar = anything:x ?(x in nodeidchars) -> x
    nodeid = ws? '#' <nodeidchar{5}>

    query = (nodeid:n (~~separator | ~anything) -> n
                | -> None):nodeid
            (separator | -> 'default'):initial_sep
            matcher(initial_sep nodeid):initial
            (separator:sep matcher(sep None))*:following
            -> JoinedSearch(initial, *following)

    """
    bindings = {
        "Node": _Node,
        "TaggedPattern": _TaggedPattern,
        "JoinedSearch": JoinedSearch,
        "make_segment": make_segment,
        "nodeidchars": file_storage.nodeidchars
    }

Query = memoize(SearchGrammar.wraprule("query"))


@memoize
class Creator(object):
    def __init__(self, querytext=None, joinedsearch=None, do_auto_add=False):
        if joinedsearch is not None:
            self.joinedsearch = joinedsearch
        else:
            self.joinedsearch = SearchGrammar(querytext).query()

        # dememoization hack
        joinedsearch = JoinedSearch()
        joinedsearch.segments = list(self.joinedsearch.segments)
        self.joinedsearch = joinedsearch
        del joinedsearch

        segment = self.joinedsearch.segments.pop()
        if not segment.matcher is not None:
            assert False, (
                "cannot create node without full node")
        if not segment.matcher.is_rigid:
            assert False, "cannot create node without full node"
        if not segment.separator != "parents":
            assert False, "cannot create parent node"

        rel = segment.matcher.create_relationship
        if rel == "default":
            new_tags = set(segment.tags)

            if "before" in new_tags:
                if "after" in new_tags:
                    assert False
                new_tags.remove("before")
                self.is_before = True
            elif "after" in new_tags:
                new_tags.remove("after")
                self.is_before = False
            else:
                self.is_before = (segment.separator != "prev_peer")
                if not new_tags:
                    new_tags.add("can_activate")

            if segment.plurality is not None:
                new_tags.add(segment.plurality)
            else:
                new_tags.add("first")

        else:
            if segment.tags:
                assert False, "conflict between rel shortcut and tags"
            if segment.plurality is not None:
                assert False, (
                    "conflict between rel shortcut and tags")
            is_last = (rel == "+")

            if is_last:
                new_tags = set(["last"])
                self.is_before = False
            else:
                new_tags = set(["first"])
                self.is_before = True

            if segment.separator == "prev_peer":
                # invert order for prev_peer
                self.is_before = not self.is_before

        self.node_type = segment.matcher.type
        self.text = segment.matcher.text

        if segment.separator not in ("children", "next_peer", "prev_peer"):
            assert False

        new_last = make_segment(segment.separator, None,
                ("default", "*", None), new_tags)
        self.last_segment = new_last

        # is this really the right place to put auto add?
        # probably not, but where does it belong then?
        self.do_auto_add = do_auto_add

        if len(self.joinedsearch.segments):
            final = self.joinedsearch.segments[-1]
            if final.plurality is None:
                final.plurality = "first"

    def __call__(self, nodes):
        resulting_nodes = []
        evaluated_search = list(self.joinedsearch(nodes))
        if not evaluated_search:
            return

        _created_nodes = []

        def _make_node(node):
            if _created_nodes:
                return _created_nodes.pop()
            else:
                return node.root.nodecreator.create(
                        self.node_type, self.text, None, validate=False)

        for parentnode in evaluated_search:
            nodes = list(self.last_segment([parentnode]))

            if self.do_auto_add:
                node = _make_node(evaluated_search[0])
                if len(nodes) > 1:
                    assert False
                if node.auto_add(creator=parentnode, root=parentnode.root):
                    continue
                else:
                    _created_nodes.append(node)

            if nodes:
                for node in nodes:
                    if self.is_before:
                        rel = {"before": node}
                    else:
                        rel = {"after": node}

                    # node.parent may not be parentnode, for next_peer and
                    # prev_peer relationships
                    new_node = _make_node(parentnode)
                    new_node = node.parent.addchild(new_node, **rel)

                    resulting_nodes.append(new_node)
            elif self.last_segment.separator == "children":
                new_node = _make_node(parentnode)
                new_node = parentnode.addchild(new_node)
                resulting_nodes.append(new_node)

            elif self.last_segment.separator == "prev_peer":
                new_node = _make_node(parentnode)
                new_node = parentnode.parent.addchild(new_node,
                        before=parentnode)
                resulting_nodes.append(new_node)

            else:
                new_node = _make_node(parentnode)
                new_node = parentnode.parent.addchild(new_node,
                        after=parentnode.parent.children.prev_neighbor)
                resulting_nodes.append(new_node)

        return resulting_nodes


class TickCounter(object):
    "Mutable thing"
    def __init__(self):
        self.ticks = 0

try:
    import __pypy__
    MAX_TICKS = 25000
except ImportError:
    MAX_TICKS = 10000


def tick(counter):
    try:
        counter.ticks += 1
    except AttributeError:
        assert counter is None
        return

    if counter.ticks > MAX_TICKS:
        raise TooManyMatchesError()


@retrievers.add()
def retriever_children(nodes, counter=None):
    for node in nodes:
        tick(counter)
        for child in node.children:
            tick(counter)
            yield child


@retrievers.add()
def retriever_flatten(nodes, counter=None):
    for node in nodes:
        tick(counter)
        for depth, subnode in node.iter_flat_children():
            tick(counter)
            yield subnode


@retrievers.add()
def retriever_next_peer(nodes, counter=None):
    for node in nodes:
        tick(counter)
        for peer in node.iter_forward():
            tick(counter)
            yield peer


@retrievers.add()
def retriever_prev_peer(nodes, counter=None):
    for node in nodes:
        tick(counter)
        for peer in node.iter_backward():
            tick(counter)
            yield peer


@retrievers.add()
def retriever_parents(nodes, counter=None):
    for node in nodes:
        tick(counter)
        for parent in node.iter_parents():
            tick(counter)
            if parent is node:
                continue
            yield parent


@retrievers.add()
def retriever_root(nodes, counter=None):
    for node in nodes:
        tick(counter)
        yield node.root
        return


@retrievers.add()
def retriever_self(nodes, counter=None):
    for node in nodes:
        tick(counter)
        yield node
        return


def getnodeid(nodes, nodeid, counter=None):
    for node in nodes:
        tick(counter)
        yield node.root.ids[nodeid]
        return


def tag_filter(nodes, tags, counter=None):
    tags = set(tags)
    for node in nodes:
        tick(counter)
        node_tags = set(node._search_tags())
        if tags <= node_tags:
            yield node


class Matcher(object):
    def __init__(self, type, text, rel="default"):
        self.type = None if type == "*" else type
        self.text = None if text == "*" else text
        self.create_relationship = rel

        self.is_rigid = self.type is not None and self.text is not None
        if not self.is_rigid and rel != "default":
            assert False

    def __call__(self, nodes, counter=None):
        for node in nodes:
            tick(counter)
            node_types, texts = node.search_texts()
            texts_lower = []
            for text in texts:
                if text is None:
                    continue
                texts_lower.append(text.lower())

            if self.type is not None and self.type not in node_types:
                continue
            if self.text is not None and self.text.lower() not in texts_lower:
                continue
            yield node

    def __repr__(self):
        return "Matcher(%r, %r, rel=%r)" % (self.type, self.text,
                self.create_relationship)


class Segment(object):
    def __init__(self, separator, pattern,
            retriever, matcher, tags, plurality, nodeid=None):
        self.separator = separator
        self.pattern = pattern

        self.retriever = retriever
        self.matcher = matcher
        self.tags = tags
        self.plurality = plurality

        self.nodeid = nodeid

    def __call__(self, nodes, counter=None):
        if self.nodeid is not None:
            nodes = getnodeid(nodes, self.nodeid, counter=counter)
        nodes = self.retriever(nodes, counter=counter)
        if self.matcher is not None:
            nodes = self.matcher(nodes, counter=counter)

        if self.tags:
            nodes = tag_filter(nodes, self.tags, counter=counter)

        if self.plurality == "last":
            node = None
            for node in nodes:
                pass
            if node is not None:
                yield node
        elif self.plurality == "first":
            for node in nodes:  # pragma: no branch
                yield node
                break
        else:
            for node in nodes:
                tick(counter)
                yield node

    def __repr__(self):
        return "Segment(%r%s%s%s)" % (
                self.separator,
                ", m=" + repr(self.matcher) if self.matcher else "",
                ", t=" + repr(self.tags) if self.tags else "",
                ", p=" + repr(self.plurality) if self.plurality else "")


def first(iterator):
    for node in iterator:
        return node
    return None


def record_iterator(iterator, thelist):
    try:
        for node in iterator:
            thelist.append(node)
            yield node
    except TypeError:
        thelist.append(iterator)
        yield iterator


def chain(*queries):
    def run(nodes, counter=None):
        recorded = []
        to_iterate = record_iterator(nodes, recorded)
        if counter is None:
            counter = TickCounter()
        for query in queries:
            for node in query(to_iterate, counter=counter):
                yield node
            to_iterate = recorded
    return run


class TooManyMatchesError(Exception):
    pass


def ignore_overflow(query):
    try:
        for x in query:
            yield x
    except TooManyMatchesError:
        return


def list_ignore_overflow(query):
    return list(ignore_overflow(query))


if __name__ == "__main__":
    todofile = "/Users/lahwran/.todo_tracker/life"
    from todo_tracker.tracker import Tracker
    import time
    tracker = Tracker()
    with open(todofile, "r") as reader:
        tracker.deserialize("file", reader)

    while True:
        querytext = raw_input("query: ")
        import subprocess
        subprocess.call(["clear"])
        print "query:", querytext
        queryer = Query(querytext)
        print queryer

        inittime = time.time()
        results = list(queryer(tracker.root))
        finishtime = time.time()
        for x in results[:1000]:
            print " > ".join([str(node) for node in x.iter_parents()][::-1])
        print len(results), finishtime - inittime
