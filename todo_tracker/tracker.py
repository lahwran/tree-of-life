import re
import collections
import inspect
import operator
import itertools

from crow2.util import paramdecorator
from crow2.adapterutil import IString
from zope.interface import Interface

from todo_tracker.ordereddict import OrderedDict

class _NodeCreatorTracker(object):
    def __init__(self):
        self.creators = {}

    def create(self, node_type, text, parent, tracker):
        return self.creators[node_type](node_type, text, parent, tracker)

    @paramdecorator
    def __call__(self, func, name=None):
        self.creators[name] = func
        return func

nodecreator = _NodeCreatorTracker()

class _NodeListIter(object):
    def __init__(self, nodelist):
        self.nodelist = self.node = nodelist

    def __iter__(self):
        return self

    def next(self):
        if self.node._next_node is self.nodelist:
            raise StopIteration
        self.node = self.node._next_node

        return self.node

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
            print prev_n
            print next_n
            print prev_n._next_node
            raise Exception("derp")
        if next_n._prev_node is not prev_n:
            print prev_n
            print next_n
            print prev_n._next_node
            print next_n._prev_node
            raise Exception("herp")

        next_n._prev_node = child
        child._next_node = next_n

        prev_n._next_node = child
        child._prev_node = prev_n
        self.length += 1

    def remove(self, child):
        before = child._prev_node
        after = child._next_node
        child._prev_node = None
        child._next_node = None
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

    def __len__(self):
        return self.length

class Tree(object):
    multiline = False
    textless = False
    toplevel = False
    can_activate = False
    options = ()
    children_of = None
    allowed_children = None

    def __init__(self, node_type, text, parent, tracker):
        if self.toplevel and parent != tracker.root:
            raise Exception("Must be child of root node")
        if self.textless and text is not None:
            raise Exception("Must not have text")
        if self.children_of and parent.node_type not in self.children_of:
            raise Exception("Must be child of what I belong to")
        self.node_type = node_type
        self.text = text
        self.parent = parent
        self.tracker = tracker

        self._next_node = None
        self._prev_node = None

        self.children = _NodeListRoot()

    def iter_parents(self):
        node = self
        yield node

        while node.parent is not None:
            yield node.parent
            node = node.parent

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
        if self.allowed_children and child.node_type not in self.allowed_children:
            raise Exception("Herp Derp")
        self.children.insert(child, before, after)

    def createchild(self, node_type, text=None, *args, **keywords):
        node = self.tracker.nodecreator.create(node_type, text, self, self.tracker)
        self.addchild(node, *args, **keywords)
        return node

    def removechild(self, child):
        self.children.remove(child)
        child.parent = None

    def detach(self):
        if self.parent:
            self.parent.removechild(self)

    def copy(self, parent=None, tracker=None):
        if parent is None:
            parent = self.parent
        if tracker is None:
            tracker = self.tracker
        newnode = nodecreator.create(self.node_type, self.text, parent, tracker)
        for child in self.children_export():
            child_copy = child.copy(parent=newnode, tracker=tracker)
            newnode.addchild(child_copy)
        return newnode

    def setoption(self, option, value):
        options = self._option_dict()
        try:
            handler = options[option]
        except KeyError:
            raise Exception("no such option")

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
            raise Exception("multiline text not allowed")

        self.text += "\n"
        self.text += text

    def load_finished(self):
        pass

    def __str__(self):
        return todo_tracker.file_storage.serialize(self)[0]

    def __repr__(self):
        result = [self]
        while result[-1] != self.tracker.root:
            result.append(result[-1].parent)
        result_strings = []
        indent_text = " "
        for indent, item in enumerate(reversed(result)):
            result_strings.append("%s<%s %r: %r>" % (indent * indent_text, type(item).__name__, item.node_type, item.text))
        return "\n".join(result_strings)

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
        

@nodecreator("_genericnode")
class GenericNode(Tree):
    multiline = True

    def __init__(self, *args, **keywords):
        super(GenericNode, self).__init__(*args, **keywords)
        self.metadata = {}

    def setoption(self, option, value):
        self.metadata[option] = value

    def option_values(self, adapter=None):
        return [(x, y, True) for x, y in self.metadata.items()]

@nodecreator('-')
def continue_text(node_type, text, parent, root):
    parent.continue_text(text)

class LoadError(Exception):
    pass

class Tracker(object):
    def __init__(self, nodecreator=nodecreator):
        self.nodecreator = nodecreator
        self._makeroot()

        self._make_skeleton()

    def _makeroot(self):
        self.days = None
        self.active_node = None
        self.todo = None
        self.todo_review = None
        self.root = Tree("life", None, None, self)

    def _make_skeleton(self):
        if not self.days:
            self.root.createchild('days')
        if not self.active_node:
            self.activate(self.days.createchild('day', 'today'))
        if not self.todo:
            self.root.createchild('todo bucket')

    def load(self, reader):
        self._makeroot()
        stack = []
        lastnode = self.root
        lastindent = -1
        metadata_allowed_here = False
        
        for indent, is_metadata, node_type, text in IParser(reader):
            if indent > lastindent:
                if indent > lastindent + 1:
                    raise NotImplementedError()
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

        self._make_skeleton()

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
        node.start()

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
            if newnode is self.root:
                raise StopIteration
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

    def create_before(self, node_type, text, activate=True):
        self._create_related(node_type, text, "before", activate)

    def create_after(self, node_type, text, activate=True):
        self._create_related(node_type, text, "after", activate)

    def create_child(self, node_type, text, activate=True):
        newnode = self.active_node.createchild(node_type, text)
        if activate:
            self.activate(newnode)

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
