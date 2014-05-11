from __future__ import unicode_literals, print_function

import itertools
import functools
from collections import deque, namedtuple

# Note: a lot of classes here seem to "not be classes",
# in the terms of the "stop writing classes" talk. however,
# almost all of them are *used as data* by other code, hence
# why there are classes that look like they're used as functions.
from treeoflife import parseutil
from treeoflife.util import HandlerDict, HandlerList, memoize
from treeoflife import file_storage
from treeoflife.exceptions import LoadError


_Node = namedtuple('Node', 'rel, type, text')
_TaggedPattern = namedtuple('TaggedPattern', 'pat, tags')


class Queries(object):
    """
    A super-query made of other queries.
    AST + execution
    """
    def __init__(self, *queries):
        self.queries = queries

    def __call__(self, node, counter=None):
        return QueriesResults(self.queries, node, counter=counter)

    def __eq__(self, other):
        return self.queries == getattr(other, "queries", None)

    def __repr__(self):
        joined = "\n".join(("    " + repr(q)) for q in self.queries)
        return "<queries\n%s\n>" % (joined,)


class Query(object):
    """
    A whole query.
    AST + execution
    """
    def __init__(self, *segments):
        self.segments = tuple(segments)

        self.mincreate = 0
        for index, segment in enumerate(reversed(self.segments)):
            realindex = len(self.segments) - (index + 1)
            assert segments[realindex] is segment
            if not segment.can_create:
                self.mincreate = realindex + 1
                break

    def copy(self):
        return Query(*(segment.copy() for segment in self.segments))

    def __call__(self, node, counter=None):
        return QueryResults(self.segments, self.mincreate, node, counter)

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
            if plurality is not None:
                assert False
            plurality = tag
        else:
            tags.add(tag)
    return tags, plurality

retrievers = HandlerDict()


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

    return Segment(separator, pattern,
            matcher, tags, plurality, nodeid=nodeid)


class SearchGrammar(parseutil.Grammar):
    # parsley weirdness. should not be a class, but w/e
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


parsecreatefilters = HandlerList()


@memoize
def parse(string=None, query=None):
    assert (string is not None) != (query is not None)
    query = parse_single(string) if string is not None else query
    queries = [query.copy()]

    for filter_ in parsecreatefilters:
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
    def __init__(self, queries=None, creators=None, do_auto_add=False):
        if creators is not None:
            self.creators = list(creators)
            return

        self.creators = []
        errors = []
        for query in queries:
            try:
                creator = _Creator(query, do_auto_add=do_auto_add)
            except CantCreateError as e:
                errors.append(e)
            else:
                self.creators.append(creator)
        if not self.creators:
            if len(errors) == 1:
                raise errors[0]

            raise CantCreateError(
                "Can't create multi, do to all being errors:\n%s" % (
                    "\n".join(str(x) for x in errors),
                )
            )

    def __call__(self, basenode):
        assert basenode.node_type, "Please provide a single node"
        for creator in self.creators:
            node = creator(basenode)
            if node is not None:
                return node
        raise NodeNotCreated

    def __repr__(self):
        return "<creators\n%s\n>" % (
            "\n".join(("    " + repr(q)) for q in self.creators),
        )

    def __eq__(self, other):
        return self.creators == getattr(other, "creators", None)


class CantCreateError(Exception):
    pass


class _Creator(object):
    def __init__(self, query, do_auto_add=None):
        self.query = query.copy()
        self.segment = self.query.segments[-1]
        self.query.segments = self.query.segments[:-1]
        if not self.segment.can_create:
            raise CantCreateError(self.segment._no_create_reason)

    def __eq__(self, other):
        return self.query == other.query

    def __call__(self, basenode):
        node = self.query(basenode).first()
        if node is None:
            return
        return self.segment.create(node)

    def __repr__(self):
        return "<creator %r -> %r>" % (self.query, self.segment)


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
    """
    The text portion of a segment
    AST + execution code
    """
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
    """
    A segment of a search
    AST + execution code
    """
    def __init__(self, separator, pattern,
            matcher, tags, plurality, nodeid=None):
        self.separator = separator  # string (informational only)
        self.pattern = pattern  # instance of _Node (informational only)

        retriever = retrievers.handlers["retriever_" + separator]
        self.retriever = retriever  # function
        self.matcher = matcher  # instance of Matcher
        self.tags = tags  # set
        self.plurality = plurality  # string

        self.nodeid = nodeid  # string or None

        self.setup_create()

    def setup_create(self):
        r = None
        if self.matcher is None:
            r = "cannot create node without full node"
        elif not self.matcher.is_rigid:
            r = "cannot create node without full node"
        elif self.separator == "parents":
            r = "cannot create parent node"
        elif self.nodeid:
            r = "cannot create node with set id"
        elif self.plurality is not None:
            r = "cannot create anything but one node, but plurality is set"
        elif self.separator not in ("children", "next_peer", "prev_peer"):
            r = "cannot create with this separator"

        self.can_create = r is None
        self._no_create_reason = r
        if r:
            return

        rel = self.matcher.create_relationship
        self.create_activate_hack = False

        if rel == "default":
            self.create_is_before = (self.separator != "prev_peer")
            is_last = False
            self.create_activate_hack = True
        else:
            #TODO: if createrel is set, mark this segment as preferring create?
            if self.tags:
                assert False, "conflict between rel shortcut and tags"
            is_last = (rel == "+")
            self.create_is_before = not is_last

            if self.separator == "prev_peer":
                # invert order for prev_peer, to be intuitive
                self.create_is_before = not self.create_is_before
        self.create_plurality = "last" if is_last else "first"

    def create(self, parentnode):
        assert self.can_create, self._no_create_reason
        assert parentnode.node_type, "Please provide a single node"

        node_type = self.matcher.type
        text = self.matcher.text

        new_node = parentnode.root.nodecreator.create(
                        node_type, text, None, validate=False)
        existing_nodes = list(self(parentnode, createprep=True))
        try:
            parent = new_node.auto_add(creator=parentnode,
                    root=parentnode.root)
            if parent:
                return new_node

            if existing_nodes:
                assert len(existing_nodes) == 1
                node = existing_nodes[0]

                if self.create_is_before:
                    rel = {"before": node}
                else:
                    rel = {"after": node}

                new_node = node.parent.addchild(new_node, **rel)
            elif self.separator == "children":
                new_node = parentnode.addchild(new_node)
            elif self.separator == "prev_peer":
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

    def __call__(self, node, counter=None, createprep=None):
        """
        segment = Segment()
        nodes_iterator = segment(
            node -> node to search from,
            counter=None -> TickCounter,
            createprep=False  -> skip self.matcher; for use in preparing
                                 for createrel
        )
        """
        if self.nodeid is not None:
            try:
                node = getnodeid(node, self.nodeid, counter)
            except KeyError:
                # since this function is a generator,
                # simply returning gives us the result we want:
                # no nodes yielded. it'll still be an iterator.
                return

        nodes = self.retriever(node, counter)
        if self.matcher is not None and not createprep:
            nodes = self.matcher(nodes, counter)

        if self.tags:
            nodes = tag_filter(nodes, self.tags, counter)
        elif createprep and self.create_activate_hack:
            # TODO XXX FIXME EW WRONG BAD
            # separate dem concerns
            nodes = tag_filter(nodes, {"can_activate"}, counter)

        if createprep:
            plurality = self.create_plurality
        else:
            plurality = self.plurality

        if plurality == "last":
            node = None
            for node in nodes:
                pass
            if node is not None:
                yield node
        elif plurality == "first":
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
        return _FancyIterator(_ignore_overflow(self.__iter__()))


def _ignore_overflow(iterator):
    try:
        for x in iterator:
            yield x
    except TooManyMatchesError:
        return


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


class _NodeResult(object):
    def __init__(self, node, actions=()):
        self.exists = True
        self.node = node
        self.actions = list(actions)
        self.can_activate = node.can_activate

    def __eq__(self, other):
        sentinel = object()
        return (
                self.node == getattr(other, "node", sentinel)
            and self.actions == getattr(other, "actions", sentinel)
            and getattr(other, "createposition", sentinel) == sentinel
        )

    def preview(self):
        return {
            "node": {"existing": self.node.id},
            "actions": self.actions
        }

    def produce_node(self):
        return self.node

    def __repr__(self):
        return "<_NodeResult %r; %r>" % (self.node, self.actions)


class _CreateResult(object):
    # TODO: with empty createsegments this is the same as NodeResult
    def __init__(self, segments, createposition, parentnode,
            actions=("do_nothing",)):
        self.exists = False
        self.segments = segments  # [createposition:]
        self.createsegments = segments[createposition:]
        assert all(segment.can_create for segment in self.createsegments)
        self.createposition = createposition
        self.parentnode = parentnode
        self.actions = list(actions)

        # hacky heuristic
        creators = parentnode.root.nodecreator.creators
        last = creators[self.createsegments[-1].matcher.type]
        self.can_activate = last.can_activate

    def __eq__(self, other):
        sentinel = object()
        return (
                self.segments == getattr(other, "segments", sentinel)
            and self.createposition
                    == getattr(other, "createposition", sentinel)
            and self.parentnode == getattr(other, "parentnode", sentinel)
            and self.actions == getattr(other, "actions", sentinel)
        )

    def preview(self):
        return {
            "node": {
                "existing": self.parentnode.id,
                "create": [{
                    "direction": segment.separator,
                    "type": segment.matcher.type,
                    "text": segment.matcher.text,
                    "rel": segment.matcher.create_relationship
                } for segment in self.createsegments]
            },
            "actions": self.actions
        }

    def produce_node(self):
        created = []
        lastresult = self.parentnode
        for segment in self.createsegments:
            try:
                lastresult = segment.create(lastresult)
                lastresult.user_creation()
            except LoadError:  # fake transactionality
                for x in created:
                    x.detach()
                raise

            created.append(lastresult)

        return lastresult

    def __repr__(self):
        return "<_CreateResult %r (%r); %r>" % (
                self.parentnode, self.createposition, self.actions)


class QueryResults(_FancyIterator):
    def __init__(self, segments, mincreate, basenode, counter=None):
        assert basenode.node_type, "Please provide a single node"
        self.segments = segments
        self.basenode = basenode
        self.mincreate = mincreate

        if counter is None:
            counter = TickCounter()
        self.counter = counter

    @fancify
    def nodes(self):
        return (x[2] for x in self._search(True, False))

    @fancify
    def actions(self, matches=True, creates=True):
        for is_found, createposition, node in self._search(matches, creates):
            if is_found:
                result = _NodeResult(node)
            elif createposition >= self.mincreate:
                result = _CreateResult(self.segments, createposition, node)
            else:
                # can't produce a node here :(
                continue
            yield result

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
            # #(because of initial frame)
            # stacksegments = len(stack) - 1
            # # to 0-based
            # currentposition = stacksegments - 1
            # lastsuccessfulmatch = currentposition - 1
            # # 0-based index following current one
            # nextposition = currentposition + 1
            # # currentposition would be 0-based index of
            # # last successfully matched segment
            # # that all simplifies to:
            nextposition = len(stack) - 1

            try:
                node = frame.iterator.next()
            except StopIteration:
                if not frame.found and errors:
                    # yield False, currentposition, frame.node
                    yield False, nextposition - 1, frame.node
                stack.pop()
                continue
            frame.found = True

            if nextposition >= seglen:
                if successes:
                    yield True, None, node
                continue

            n_seg = self.segments[nextposition]
            stack.append(_Frame(node, n_seg(node, self.counter)))


class QueriesResults(_FancyIterator):
    """
    Very fancy iterator over results of a Queries()
    """
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

    @fancify
    def actions(self, matches=True, creates=True):
        return self._makechain(lambda q: q.actions(matches, creates))

    def _search(self, successes, errors):
        return self._makechain(lambda q: q._search(successes, errors))

    def __iter__(self):
        return iter(self.nodes())


def one(iterator):
    return _FancyIterator(iterator).one()


class NoMatchesError(Exception):
    pass


class NodeNotCreated(NoMatchesError):
    pass


class TooManyMatchesError(Exception):
    pass
