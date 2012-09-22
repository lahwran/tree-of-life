import re
import collections
import inspect
import operator
import itertools

from crow2.util import paramdecorator
from crow2.adapterutil import IString
from zope.interface import Interface

from todo_tracker.ordereddict import OrderedDict
from todo_tracker.exceptions import ListIntegrityError, LoadError, CantStartNodeError

class _NodeCreatorTracker(object):
    def __init__(self):
        self.creators = {}

    def create(self, node_type, text, parent, tracker):
        try:
            creator = self.creators[node_type]
        except KeyError:
            raise LoadError("No such node type: %r" % node_type)
        return creator(node_type, text, parent, tracker)

    def exists(self, node_type):
        return node_type in self.creators

    @paramdecorator
    def __call__(self, func, name):
        self.creators[name] = func
        return func

nodecreator = _NodeCreatorTracker()

class _NodeListIter(object):
    def __init__(self, nodelist, reverse=False):
        self.nodelist = self.node = nodelist
        self.reverse = reverse

    def __iter__(self):
        return self

    def _prev(self):
        if self.node._prev_node is self.nodelist:
            raise StopIteration
        self.node = self.node._prev_node

        return self.node

    def _next(self):
        if self.node._next_node is self.nodelist:
            raise StopIteration
        self.node = self.node._next_node

        return self.node

    def next(self):
        if self.reverse:
            return self._prev()
        else:
            return self._next()


class _NodeListRoot(object):
    def __init__(self):
        self._next_node = self
        self._prev_node = self
        self.length = 0

    def insert(self, child, before=None, after=None):
        # note: this method makes a lot of assumptions about valid state!
        next_n = before
        prev_n = after

        if not next_n and not prev_n:
            next_n = self
            prev_n = self._prev_node

        elif next_n and not prev_n:
            prev_n = next_n._prev_node
        elif prev_n and not next_n:
            next_n = prev_n._next_node

        if prev_n._next_node is not next_n:
            raise ListIntegrityError(("prev_node %r has next neighbor %r, "
                    "but next_n is %r and has prev neighbor %r") %
                    (prev_n, prev_n._next_node, next_n, next_n._prev_node))
        if next_n._prev_node is not prev_n:
            raise ListIntegrityError(("next_node %r has prev neighbor %r, "
                    "but prev_n is %r and has next neighbor %r") %
                    (next_n, next_n._prev_node, prev_n, prev_n._next_node))

        next_n._prev_node = child
        child._next_node = next_n

        prev_n._next_node = child
        child._prev_node = prev_n
        self.length += 1

    def remove(self, child):
        before = child._prev_node
        after = child._next_node
#        child._prev_node = None
#        child._next_node = None
        before._next_node = after
        after._prev_node = before
        self.length -= 1

    @property
    def next_neighbor(self):
        if self._next_node is not self:
            return self._next_node
        return None

    @property
    def prev_neighbor(self):
        if self._prev_node is not self:
            return self._prev_node
        return None

    def __iter__(self):
        return _NodeListIter(self)

    def __reversed__(self):
        return _NodeListIter(self, reverse=True)

    def __len__(self):
        return self.length

class Tree(object):
    multiline = False
    textless = False
    text_required = False
    toplevel = False
    can_activate = False
    options = ()
    children_of = None
    allowed_children = None

    def __init__(self, node_type, text, parent, tracker):
        self._init_children()

        self.tracker = tracker
        self.parent = parent
        self.node_type = node_type
        self.text = text


        if self.toplevel and parent != tracker.root:
            raise LoadError("%r node must be child of root node" % self)

        if self.textless and text is not None:
            raise LoadError("%r node cannot have text" % self)

        if self.text_required and text is None:
            raise LoadError("%r node must have text" % self)

        if self.children_of and parent.node_type not in self.children_of:
            raise LoadError("%s cannot be child of %s node" % (self._do_repr(parent=False), self.parent._do_repr(parent=False)))

        if not self.multiline and text is not None and "\n" in text:
            raise LoadError("%r node cannot have newlines in text" % self)

    def _init_children(self):
        self.children = _NodeListRoot()

        self._next_node = None
        self._prev_node = None


    def iter_parents(self, skip_root=False):
        node = self

        while True:
            yield node
            node = node.parent
            if node is None:
                break
            if skip_root and node is self.tracker.root:
                break

    def iter_flat_children(self):
        stack = [iter(self.children)]
        while len(stack):
            try:
                item = next(stack[-1])
            except StopIteration:
                stack.pop()
            else:
                yield len(stack), item
                stack.append(iter(item.children))

    @property
    def next_neighbor(self):
        if self._next_node and self._next_node is self.parent.children:
            return None
        return self._next_node

    @property
    def prev_neighbor(self):
        if self._prev_node and self._prev_node is self.parent.children:
            return None
        return self._prev_node

    def addchild(self, child, before=None, after=None):
        if self.allowed_children is not None and child.node_type not in self.allowed_children:
            raise LoadError("node %s cannot be child of %r" % (child._do_repr(parent=False), self))
        if child.parent is not self:
            raise LoadError("node %r does not expect to be a child of %r" % (child, self))
        if before and before.parent is not self:
            raise LoadError("node %r cannot be before node %r as child of %r" % (child, before, self))
        if after and after.parent is not self:
            raise LoadError("node %r cannot be after node %r as child of %r" % (child, after, self))
        self.children.insert(child, before, after)
        return child

    def createchild(self, node_type, text=None, *args, **keywords):
        node = self.tracker.nodecreator.create(node_type, text, self, self.tracker)
        return self.addchild(node, *args, **keywords)

    def removechild(self, child):
        self.children.remove(child)
        child.parent = None

    def detach(self):
        if self.parent:
            self.parent.removechild(self)

    def copy(self, parent=None, tracker=None):
        if tracker is None:
            tracker = self.tracker
            if parent is None:
                parent = self.parent
        elif parent is None:
            raise LoadError("cannot copy to different tracker using old parent")

        newnode = tracker.nodecreator.create(self.node_type, self.text, parent, tracker)
        for child in self.children_export():
            child_copy = child.copy(parent=newnode, tracker=tracker)
            newnode.addchild(child_copy)
        return newnode

    def setoption(self, option, value):
        options = self._option_dict()
        try:
            handler = options[option]
        except KeyError:
            raise LoadError("node %r has no such option %r" % (self, option))

        try:
            handler.set(self, option, value)
        except: # haw haw
            print repr(self)
            print option
            print value
            raise

    def _option_dict(self):
        # note: this will redo some elements, but that's not a problem
        try:
            return self._option_dict_cache
        except AttributeError:
            pass
        
        result = OrderedDict()
        mro = [self] + list(inspect.getmro(type(self)))
        seen = set()
        for resolve_element in reversed(mro):
            try:
                options = resolve_element.options
            except AttributeError:
                continue

            if id(options) in seen:
                continue
            seen.add(id(options))

            for name, handler in options:
                result[name] = handler
        return result

    def option_values(self):
        result = []
        for name, handler in self._option_dict().items():
            show, item = handler.get(self, name)
            result.append((name, item, show))
        return result

    def children_export(self):
        return list(self.children)

    def continue_text(self, text):
        if not self.multiline:
            raise LoadError("%r node cannot have newline in text" % self)
        if self.text is None:
            raise LoadError("Cannot add new line to text of node %r, since it has no text set" % self)

        self.text += "\n"
        self.text += text

    def start(self):
        if not self.can_activate:
            raise CantStartNodeError("can't start node %r" % self)

    def finish(self):
        pass

    def load_finished(self):
        pass

    def __str__(self):
        return todo_tracker.file_storage.serialize(self, one_line=True)[0]

    def _do_repr(self, parent=True):
        if parent:
            parent_repr = "None"
            if getattr(self, "parent", None):
                parent_repr = str(self.parent)
            return "<%s (%s) %r: %r>" % (type(self).__name__, parent_repr, getattr(self, "node_type", None), getattr(self, "text", None))
        else:
            return "<%s %r: %r>" % (type(self).__name__, getattr(self, "node_type", None), getattr(self, "text", None))

    def __repr__(self):
        return self._do_repr()

    def find_node(self, path, offset=0):
        if offset >= len(path):
            return self
        segment = path[offset]

        matcher = _NodeMatcher(self.tracker.nodecreator, segment, self, self.tracker)
        for child in matcher.iter_results():
            node = child.find_node(path, offset+1)

            if node is not None:
                return node

        return None

class _NodeMatcher(object):
    def __init__(self, nodecreator, segment, node, tracker):
        self.flatten = (segment == "**")

        if not self.flatten:
            self.find_parents = False
            if segment.startswith("<"):
                self.find_parents = True
                segment = segment[1:]

            from todo_tracker.file_storage import parse_line
            indent, is_metadata, node_type, text = parse_line(segment)
            assert not indent
            assert not is_metadata

            exists = nodecreator.exists(node_type)
            if text is None and (exists or node_type == "*"):
                # *
                # days
                text = "*"
                # *: *
                # days: *
            elif text is None and not (exists or node_type == "*"):
                # herp derp
                # text with no decoration
                text = node_type
                node_type = "*"
                # *: herp derp
                # *: text with no decoration
            elif text != "*" and node_type != "*" and exists:
                # day: today
                # reference: whatever>herp>derp
                temp_node = nodecreator.create(node_type, text, node, tracker)
                node_type = temp_node.node_type
                text = temp_node.text
                # day: <today's actual date>
                # reference: whatever > herp > derp

            self.node_type = node_type
            self.text = text
        self.node = node
        
    def _filter(self, iterator):
        for child in iterator:
            if self.node_type != "*" and self.node_type != child.node_type:
                continue
            if self.text != "*" and self.text != child.text:
                continue
            yield child

    def iter_results(self):
        if self.flatten:
            return self.node.iter_flat_children()
        if self.node_type == "*" and self.text == "*":
            return self.node.children
        elif self.find_parents:
            iterator = self._filter(self.node.iter_parents())
            try:
                result = [iterator.next()]
            except StopIteration:
                result = []
            return iter(result)
        else:
            return self._filter(self.node.children)

class SimpleOption(object):
    def __init__(self, adapter):
        self.adapter = adapter

    def set(self, node, name, value):
        value = self.adapter(value)
        setattr(node, name, value)

    def get(self, node, name):
        try:
            value = getattr(node, name)
        except AttributeError:
            return False, None

        show = True
        if value is None:
            show = False

        return show, value

class BooleanOption(object):
    def set(self, node, name, value):
        setattr(node, name, True)

    def get(self, node, name):
        value = getattr(node, name)
        show = bool(value)
        return show, None


@nodecreator('-')
def continue_text(node_type, text, parent, root):
    parent.continue_text(text)

class ErrorContext(object):
    def __init__(self):
        self.line = None

class Tracker(object):
    def __init__(self, nodecreator=nodecreator, auto_skeleton=True):
        self.nodecreator = nodecreator
        self._makeroot()

        self.auto_skeleton = auto_skeleton
        if auto_skeleton:
            self.make_skeleton()

        self.editor_callback = None

    def _makeroot(self):
        self.days = None
        self.active_node = None
        self.todo = None
        self.todo_review = None
        self.root = Tree("life", None, None, self)

    def make_skeleton(self):
        self.days = self.root.find_node(["days"]) or self.root.createchild('days')
        today = self.root.find_node(["days", "day: today"])
        if not today:
            today = self.days.createchild('day', 'today')
        if not self.active_node or today not in list(self.active_node.iter_parents()):
            self.activate(today)

        self.todo = self.root.find_node(["todo bucket"]) or self.root.createchild("todo bucket")

    def load(self, reader):
        self._makeroot()
        stack = []
        lastnode = self.root
        lastindent = -1
        metadata_allowed_here = False

        error_context = ErrorContext() # mutable thingy
        
        try:
            parser = IParser(reader)
            parser.error_context = error_context
            for indent, is_metadata, node_type, text in parser:
                if indent > lastindent:
                    if indent > lastindent + 1:
                        raise LoadError("indented too far")
                    stack.append(lastnode)
                    metadata_allowed_here = True
                elif indent < lastindent:
                    stack = stack[:int(indent)+1]
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

                    node = self.nodecreator.create(node_type, text, parent, self)
                    if node is not None:
                        parent.addchild(node)
                    lastnode = node
        except LoadError as e:
            e.error_context = error_context
            raise
        except Exception as e:
            new_e = LoadError("UNHANDLED ERROR: %s: %s" % (type(e), e))
            new_e.error_context = error_context
            raise new_e

        if self.auto_skeleton:
            self.make_skeleton()

        for depth, node in self.root.iter_flat_children():
            node.load_finished()
        

    def save(self, writer):
        serializer = ISerializer(writer)
        serializer.serialize(self.root)

    def activate(self, node):
        # jump to a particular node as active
        if self.active_node:
            self.active_node.active = False

        node.active = True
        self.active_node = node
        for parent_node in list(node.iter_parents())[::-1]:
            try:
                parent_node.start()
            except CantStartNodeError:
                if parent_node is node:
                    raise

    def _skip_ignored(self, peergetter, node):
        while node is not None:
            if node.can_activate:
                return node
            node = peergetter(node)
        return None

    def _descend(self, peergetter, node):
        while peergetter(node.children):
            next_node = peergetter(node.children)
            next_node = self._skip_ignored(peergetter, next_node)
            if next_node:
                node = next_node
            else:
                break
        return node

    def _navigate(self, peerattr):
        #TODO: does not take skipping already-done ones into account
        peergetter = operator.attrgetter(peerattr)

        node = self.active_node

        newnode = self._descend(peergetter, node)
        if newnode is not node:
            self.activate(newnode)
            return

        newnode = self._skip_ignored(peergetter, peergetter(node))
        if newnode is not None:
            self.activate(newnode)
            node.finish()
            return

        newnode = self._skip_ignored(peergetter, node.parent)
        if newnode:
            self.activate(newnode)
            node.finish()
            return

    def activate_next(self, *args, **keywords):
        return self._navigate("next_neighbor", *args, **keywords)

    def activate_prev(self, *args, **keywords):
        return self._navigate("prev_neighbor", *args, **keywords)

    def _create_related(self, node_type, text, relation, activate):
        newnode = self.active_node.parent.createchild(node_type, text,
                **{relation: self.active_node})
        if activate:
            self.activate(newnode)
        return newnode

    def create_before(self, node_type, text=None, activate=True):
        return self._create_related(node_type, text, "before", activate)

    def create_after(self, node_type, text=None, activate=True):
        return self._create_related(node_type, text, "after", activate)

    def create_child(self, node_type, text=None, activate=True):
        newnode = self.active_node.createchild(node_type, text)
        if activate:
            self.activate(newnode)
        return newnode

    def start_editor(self):
        if self.editor_callback:
            self.editor_callback()

class IParser(Interface):
    def __iter__():
        pass

    def next():
        pass

class ISerializer(Interface):
    def serialize(tree):
        pass

import todo_tracker.nodes
import todo_tracker.file_storage
