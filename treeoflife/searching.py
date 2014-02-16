from __future__ import unicode_literals, print_function

import itertools
import functools
from collections import deque, namedtuple

# Note: a lot of classes here seem to "not be classes",
# in the terms of the "stop writing classes" talk. however,
# almost all of them are *used as data* by other code, hence
# why there are classes that look like they're used as functions.
from treeoflife import parseutil
from treeoflife.util import HandlerList, memoize
from treeoflife import file_storage
from treeoflife.exceptions import LoadError


_Node = namedtuple('Node', 'rel, type, text')
_TaggedPattern = namedtuple('TaggedPattern', 'pat, tags')


class Queries(object):
    def __init__(self, *queries):
        self.queries = queries

    def __call__(self, node, counter=None):
        return QueriesResults(self.queries, node)

    def __eq__(self, other):
        return self.queries == getattr(other, "queries", None)


class Query(object):
    def __init__(self, *segments):
        self.segments = tuple(segments)

    def copy(self):
        return Query(*(segment.copy() for segment in self.segments))

    def __call__(self, node, counter=None):
        return QueryResults(self.segments, node, counter)

    def __repr__(self):
        return "<query %r>" % (self.segments,)

    def __eq__(self, other):
        return self.segments == getattr(other, "segments", None)

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
    from treeoflife.nodes.node import nodecreator

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
            -> Query(initial, *following)

    """
    bindings = {
        "Node": _Node,
        "TaggedPattern": _TaggedPattern,
        "Query": Query,
        "make_segment": make_segment,
        "nodeidchars": file_storage.nodeidchars
    }

parse_single = memoize(SearchGrammar.wraprule("query"))

parsecreatefilters = []
parseonlyfilters = []


@memoize
def parse(string=None, query=None):
    assert (string is not None) != (query is not None)
    query = parse_single(string) if string is not None else query
    queries = [query.copy()]

    for filter_ in parsecreatefilters:
        queries = filter_(queries)
    for filter_ in parseonlyfilters:
        queries = filter_(queries)

    return Queries(*queries)


@memoize
def parse_create(string=None, query=None, do_auto_add=False):
    assert (string is not None) != (query is not None)
    query = parse_single(string) if string is not None else query
    queries = [query.copy()]

    for filter_ in parsecreatefilters:
        queries = filter_(queries)

    return _Creators(queries, do_auto_add=do_auto_add)


def parse_create_single(string=None, query=None, do_auto_add=False):
    assert (string is not None) != (query is not None)
    query = parse_single(string) if string is not None else query
    query = query.copy()
    return _Creator(query, do_auto_add)


class _Creators(object):
    def __init__(self, queries, do_auto_add=False):
        self.creators = []
        for query in queries:
            self.creators.append(_Creator(query, do_auto_add=do_auto_add))

    def __call__(self, basenode):
        assert basenode.node_type, "Please provide a single node"
        for creator in self.creators:
            node = creator(basenode)
            if node is not None:
                return node
        raise NodeNotCreated


class _Creator(object):
    def __init__(self, query, do_auto_add=False):
        self.query = query.copy()
        segment = self.query.segments[-1]
        self.query.segments = self.query.segments[:-1]

        if not segment.matcher is not None:
            assert False, (
                "cannot create node without full node")
        if not segment.matcher.is_rigid:
            assert False, "cannot create node without full node"
        if segment.separator == "parents":
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
                assert segment.plurality != "many"
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

    def __call__(self, basenode):
        assert basenode.node_type, "Please provide a single node"
        parentnode = self.query(basenode).first()
        if parentnode is None:
            return

        new_node = parentnode.root.nodecreator.create(
                        self.node_type, self.text, None, validate=False)
        existing_nodes = list(self.last_segment(parentnode))
        try:
            if self.do_auto_add:
                parent = new_node.auto_add(creator=parentnode,
                        root=parentnode.root)
                if parent:
                    return new_node

            if existing_nodes:
                assert len(existing_nodes) == 1
                node = existing_nodes[0]

                if self.is_before:
                    rel = {"before": node}
                else:
                    rel = {"after": node}

                new_node = node.parent.addchild(new_node, **rel)
            elif self.last_segment.separator == "children":
                new_node = parentnode.addchild(new_node)
            elif self.last_segment.separator == "prev_peer":
                new_node = parentnode.parent.addchild(new_node,
                        before=parentnode)
            else:
                new_node = parentnode.parent.addchild(new_node,
                        after=parentnode.parent.children.prev_neighbor)
            new_node._validate()
        except LoadError:
            new_node.detach()
            raise

        return new_node


class TickCounter(object):
    "Mutable thing"
    def __init__(self):
        self.ticks = 0

try:
    import __pypy__
    MAX_TICKS = 100000
except ImportError:
    MAX_TICKS = 3500


def tick(counter):
    try:
        counter.ticks += 1
    except AttributeError:
        assert counter is None
        return

    if counter.ticks > MAX_TICKS:
        raise TooManyMatchesError()


@retrievers.add()
def retriever_children(node, counter=None):
    for child in node.children:
        tick(counter)
        yield child


@retrievers.add()
def retriever_flatten(node, counter=None):
    for depth, subnode in node.iter_flat_children():
        tick(counter)
        yield subnode


@retrievers.add()
def retriever_next_peer(node, counter=None):
    for peer in node.iter_forward():
        tick(counter)
        yield peer


@retrievers.add()
def retriever_prev_peer(node, counter=None):
    for peer in node.iter_backward():
        tick(counter)
        yield peer


@retrievers.add()
def retriever_parents(node, counter=None):
    for parent in node.iter_parents():
        tick(counter)
        if parent is node:
            continue
        yield parent


@retrievers.add()
def retriever_root(node, counter=None):
    tick(counter)
    yield node.root


@retrievers.add()
def retriever_self(node, counter=None):
    return [node]


def getnodeid(node, nodeid, counter=None):
    tick(counter)
    return node.root.ids[nodeid]


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

    def copy(self):
        return Matcher(self.type, self.text, self.create_relationship)

    def __eq__(self, other):
        sentinel = object()
        return (
                self.type == getattr(other, "type", sentinel)
            and self.text == getattr(other, "text", sentinel)
        )


class Segment(object):
    def __init__(self, separator, pattern,
            retriever, matcher, tags, plurality, nodeid=None):
        self.separator = separator  # string
        self.pattern = pattern  # instance of _Node

        self.retriever = retriever  # function
        self.matcher = matcher  # instance of Matcher
        self.tags = tags  # set
        self.plurality = plurality  # string

        self.nodeid = nodeid  # string or None

    def __call__(self, node, counter=None):
        if self.nodeid is not None:
            try:
                node = getnodeid(node, self.nodeid, counter)
            except KeyError:
                # since this function is a generator,
                # simply returning gives us the result we want:
                # no nodes yielded. it'll still be an iterator.
                return

        nodes = self.retriever(node, counter)
        if self.matcher is not None:
            nodes = self.matcher(nodes, counter)

        if self.tags:
            nodes = tag_filter(nodes, self.tags, counter)

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

    def copy(self):
        return Segment(
            self.separator,
            self.pattern,
            self.retriever,
            self.matcher.copy() if self.matcher is not None else None,
            set(self.tags) if self.tags is not None else None,
            self.plurality,
            self.nodeid
        )

    def __repr__(self):
        return "Segment(%r%s%s%s)" % (
                self.separator,
                ", m=" + repr(self.matcher) if self.matcher else "",
                ", t=" + repr(self.tags) if self.tags else "",
                ", p=" + repr(self.plurality) if self.plurality else "")

    def __eq__(self, other):
        sentinel = object()
        return (
                self.retriever == getattr(other, "retriever", sentinel)
            and self.matcher == getattr(other, "matcher", sentinel)
            and self.tags == getattr(other, "tags", sentinel)
            and self.plurality == getattr(other, "plurality", sentinel)
            and self.nodeid == getattr(other, "nodeid", sentinel)
        )


class _FancyIterator(object):
    def __init__(self, iterator):
        self.iterator = iterator

    def __iter__(self):
        return iter(self.iterator)

    def one(self):
        for x in self:
            return x
        raise NoMatchesError()

    def first(self):
        for x in self:
            return x
        return None

    def list(self):
        return list(self)

    def limit(self, length):
        return _FancyIterator(itertools.islice(self, length))

    def ignore_overflow(self):
        return _FancyIterator(ignore_overflow(self.__iter__()))


def fancify(func):
    @functools.wraps(func)
    def wrapper(*a, **kw):
        iterator = func(*a, **kw)
        return _FancyIterator(iterator)
    return wrapper


class _Frame(object):
    def __init__(self, node, iterator):
        self.node = node
        self.iterator = iter(iterator)
        self.found = False


class QueryResults(_FancyIterator):
    def __init__(self, segments, basenode, counter=None):
        assert basenode.node_type, "Please provide a single node"
        self.segments = segments
        self.basenode = basenode

        if counter is None:
            counter = TickCounter()
        self.counter = counter

    @fancify
    def nodes(self):
        return (x[2] for x in self._search(True, False))

    def __iter__(self):
        return iter(self.nodes())

    def _search(self, successes, errors):
        stack = deque()
        node = self.basenode
        stack.append(_Frame(node, [node]))
        # +1 for the initial frame
        seglen = len(self.segments)

        while stack:
            frame = stack[-1]
            position = len(stack) - 1

            try:
                node = frame.iterator.next()
            except StopIteration:
                if not frame.found and errors:
                    yield False, position, frame.node
                stack.pop()
                continue
            frame.found = True

            if position >= seglen:
                if successes:
                    yield True, None, node
                continue

            n_seg = self.segments[position]
            stack.append(_Frame(node, n_seg(node, self.counter)))


class QueriesResults(_FancyIterator):
    def __init__(self, queries, basenode, counter=None):
        assert basenode.node_type, "Please provide a single node"

        self.basenode = basenode

        if counter is None:
            counter = TickCounter()
        self.counter = counter

        self.queries = []
        for query in queries:
            self.queries.append(query(basenode, counter))

    def _makechain(self, func):
        return itertools.chain.from_iterable(
                func(query) for query in self.queries)

    @fancify
    def nodes(self):
        return self._makechain(lambda q: q.nodes())

    def _search(self, successes, errors):
        return self._makechain(lambda q: q._search(successes, errors))

    def __iter__(self):
        return iter(self.nodes())


def first(iterator):
    return _FancyIterator(iterator).first()


def one(iterator):
    return _FancyIterator(iterator).one()


def chain(*queries):
    def run(basenode, counter=None):
        assert basenode.node_type, "Please provide a single node"
        if counter is None:
            counter = TickCounter()
        for query in queries:
            for result in query(basenode, counter):
                yield result
    return run


class NoMatchesError(Exception):
    pass


class NodeNotCreated(NoMatchesError):
    pass


class TooManyMatchesError(Exception):
    pass


def ignore_overflow(iterator):
    try:
        for x in iterator:
            yield x
    except TooManyMatchesError:
        return


def list_ignore_overflow(query):
    return list(ignore_overflow(query))


if __name__ == "__main__":
    todofile = "/Users/lahwran/.treeoflife/life"
    from treeoflife.tracker import Tracker
    import time
    tracker = Tracker()
    with open(todofile, "r") as reader:
        tracker.deserialize("file", reader)

    while True:
        querytext = raw_input("query: ")
        import subprocess
        subprocess.call(["clear"])
        print("query:", querytext)
        queryer = parse(querytext)
        print(queryer)

        inittime = time.time()
        results = list(queryer(tracker.root))
        finishtime = time.time()
        for x in results[:1000]:
            print( " > ".join([str(node) for node in x.iter_parents()][::-1]))
        print(len(results), finishtime - inittime)
