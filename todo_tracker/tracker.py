import re
import collections
import inspect

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

class Tree(object):
    multiline = False
    textless = False
    toplevel = False
    options = ()
    children_of = None
    allowed_children = None

    def __init__(self, node_type, text, parent, tracker):
        if self.toplevel and parent != tracker.root:
            raise Exception("Days must be child of root node")
        if self.textless and text is not None:
            raise Exception("Days must not have text")
        if self.children_of and parent.node_type not in self.children_of:
            raise Exception("Must be child of what I belong to")
        self.text = text
        self.parent = parent
        self.next_neighbor = None
        self.previous_neighbor = None
        self.tracker = tracker

        self.node_type = node_type


        self.children = []

    def addchild(self, child):
        if self.allowed_children and child.node_type not in self.allowed_children:
            raise Exception("Herp Derp")

        if self.children:
            previous = self.children[-1]
        else:
            previous = None

        self.children.append(child)

        if previous is not None:
            previous.next_neighbor = child
            child.previous_neighbor = previous

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
        return self.children

    def continue_text(self, text):
        if not self.multiline:
            raise Exception("multiline text not allowed")

        self.text += "\n"
        self.text += text

#    def __str__(self):
#        return todo_tracker.file_storage.serialize(self)

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
        self.root = Tree("root", "root", None, self)
        self.active_node = None

    def load(self, reader):
        self.root.children = []
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

    def save(self, writer):
        serializer = ISerializer(writer)
        serializer.serialize(self.root)

    def activate(self, node):
        # jump to a particular node as active
        if self.active_node:
            self.active_node.active = False

        node.active = True
        self.active_node = node

    def activate_next(self, ascend=True, descend=True):
        #TODO: does not take skipping already-done ones into account
        node = self.active_node
        seen = set()
        if ascend:
            while node.next_neighbor is None and id(node) not in seen:
                seen.add(id(node))
                node = node.parent
        if node is self.root:
            raise NotImplementedError()

        node = node.next_neighbor

        if descend:
            while len(node.children) and id(node) not in seen:
                node = node.children[0]
                seen.add(node)

        self.activate(node)


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
