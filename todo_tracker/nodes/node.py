import inspect
import operator

from twisted.python import log

from todo_tracker.ordereddict import OrderedDict
from todo_tracker.exceptions import (ListIntegrityError, LoadError,
        CantStartNodeError)
from todo_tracker.util import HandlerList
from todo_tracker import file_storage


class _NodeCreatorTracker(HandlerList):
    name = "creators"
    autodetect = False

    def create(self, node_type, text, parent, validate=True):
        try:
            creator = self.creators[node_type]
        except KeyError:
            raise LoadError("No such node type: %r" % node_type)
        result = creator(node_type, text, parent)
        if result and validate:
            result._validate()
        return result

    def exists(self, node_type):
        return node_type in self.creators

    def __call__(self, name):
        return self.add(name)


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


class Node(object):
    multiline = False
    textless = False
    text_required = False
    toplevel = False
    can_activate = False
    options = ()
    children_of = None
    allowed_children = None
    preferred_parent = None

    def __init__(self, node_type, text, parent):
        self._init_children()

        self.parent = parent
        self.node_type = node_type
        self.text = text

        if self.textless and text is not None:
            raise LoadError("%r node cannot have text" % self)

        if self.text_required and text is None:
            raise LoadError("%r node must have text" % self)

        if not self.multiline and text is not None and "\n" in text:
            raise LoadError("%r node cannot have newlines in text" % self)

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, newparent):
        self._parent = newparent
        if self._parent is not None:
            self.root = self._parent.root

    def _validate(self):
        if self.toplevel and self.parent != self.root:
            raise LoadError("%r node must be child of root node" % self)

        if self.children_of and self.parent.node_type not in self.children_of:
            raise LoadError("%s cannot be child of %s node" % (
                self._do_repr(parent=False),
                self.parent._do_repr(parent=False)
            ))

    def _init_children(self):
        self.children = _NodeListRoot()
        self.referred_to = set()

        self._next_node = None
        self._prev_node = None

    def iter_parents(self, skip_root=False):
        node = self

        while True:
            if skip_root and node is self.root:
                break
            if node is None:
                break
            yield node
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
        if (self.allowed_children is not None and
                child.node_type not in self.allowed_children):
            raise LoadError("node %s cannot be child of %r" %
                    (child._do_repr(parent=False), self))
        if child.parent is None:
            child.parent = self
            child._validate()
        if child.parent is not self:
            raise LoadError("node %r does not expect to be a child of %r" %
                    (child, self))
        if before and before.parent is not self:
            raise LoadError("node %r cannot be before node %r as child of %r" %
                    (child, before, self))
        if after and after.parent is not self:
            raise LoadError("node %r cannot be after node %r as child of %r" %
                    (child, after, self))
        self.children.insert(child, before, after)
        return child

    def createchild(self, node_type, text=None, *args, **keywords):
        node = self.root.nodecreator.create(node_type, text, self)
        return self.addchild(node, *args, **keywords)

    def removechild(self, child):
        self.children.remove(child)
        child.parent = None

    def detach(self):
        if self.parent:
            self.parent.removechild(self)

    def copy(self, parent=None):
        if parent is None:
            parent = self.parent

        newnode = self.root.nodecreator.create(self.node_type, self.text,
                parent)
        for child in self.children_export():
            child_copy = child.copy(parent=newnode)
            newnode.addchild(child_copy)
        return newnode

    def setoption(self, option, value):
        options = self._option_dict()
        try:
            handler = options[option]
        except KeyError:
            raise LoadError("node %r has no such option %r" % (self, option))

        try:
            handler.set(self, value)
        except:  # haw haw
            print repr(self)
            print option
            print value
            raise

    def _option_dict(self):
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

            for option in options:
                result[option.name] = option
        return result

    def option_values(self):
        result = []
        for name, handler in self._option_dict().items():
            show, item = handler.get(self)
            result.append((name, item, show))
        return result

    def children_export(self):
        return list(self.children)

    def continue_text(self, text):
        if not self.multiline:
            raise LoadError("%r node cannot have newline in text" % self)
        if self.text is None:
            raise LoadError("Cannot add new line to text of node %r,"
                    " since it has no text set" % self)

        self.text += "\n"
        self.text += text

    def start(self):
        if not self.can_activate:
            raise CantStartNodeError("can't start node %r" % self)

    def finish(self):
        pass

    def load_finished(self):
        pass

    def auto_add(self, creator, root):
        self.root = root
        if self.preferred_parent is not None:
            parent = self.root.find_node(self.preferred_parent)
            parent.addchild(self)
            return parent
        else:
            return None

    def __str__(self):
        return file_storage.serialize(self, one_line=True)[0]

    def _do_repr(self, parent=True):
        if parent:
            parent_repr = "None"
            if getattr(self, "parent", None):
                parent_repr = str(self.parent)
            return "<%s (%s) %r: %r>" % (
                    type(self).__name__,
                    parent_repr,
                    getattr(self, "node_type", None),
                    getattr(self, "text", None)
            )
        else:
            return "<%s %r: %r>" % (
                    type(self).__name__,
                    getattr(self, "node_type", None),
                    getattr(self, "text", None)
            )

    def __repr__(self):
        return self._do_repr()

    def find_node(self, path, offset=0):
        if offset >= len(path):
            return self
        segment = path[offset]

        matcher = _NodeMatcher(self.root.nodecreator, segment, self, self.root)
        for child in matcher.iter_results():
            node = child.find_node(path, offset + 1)

            if node is not None:
                return node

        return None

    def ui_serialize(self, result=None):
        if result is None:
            result = {}

        if "options" not in result:
            options = [dict(zip(["type", "text"], option)) for option
                    in self.option_values() if option[-1]]
            if options:
                result["options"] = options
        if "children" not in result:
            children = [child.ui_serialize() for child in self.children]
            if children:
                result["children"] = children
        result["type"] = self.node_type
        result["text"] = self.text
        return result


@nodecreator('-')
def continue_text(node_type, text, parent):
    parent.continue_text(text)


class _NodeMatcher(object):
    def __init__(self, nodecreator, segment, node, root):
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
                temp_node = nodecreator.create(node_type, text, node)
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

    def _flat_children(self, node):
        for depth, child in node.iter_flat_children():
            yield child

    def iter_results(self):
        if self.flatten:
            return self._flat_children(self.node)
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


class Option(object):
    incoming = None
    outgoing = None

    def __init__(self, name=None, incoming=None, outgoing=None):
        if name:
            self.name = name
        if incoming:
            self.incoming = incoming
        if outgoing:
            self.outgoing = outgoing
        assert self.name is not None, "name by arg or class-attr pls"

    def set(self, node, value):
        if self.incoming is not None:
            value = self.incoming(value)
        setattr(node, self.name, value)

    def get(self, node):
        try:
            value = getattr(node, self.name)
        except AttributeError:
            return False, None

        show = True
        if value is None:
            show = False

        if self.outgoing is not None and show:
            value = self.outgoing(value)

        return show, value


class BooleanOption(object):
    def __init__(self, name=None):
        if name:
            self.name = name
        assert self.name is not None, "name by arg or class-attr pls"

    def set(self, node, value):
        setattr(node, self.name, True)

    def get(self, node):
        value = getattr(node, self.name)
        show = bool(value)
        return show, None


class TreeRootNode(Node):
    def __init__(self, tracker, nodecreator):
        self.nodecreator = nodecreator
        self.tracker = tracker
        super(TreeRootNode, self).__init__("life", None, None)
        self.root = self

        self.editor_callback = None

        self.days = None
        self.active_node = None
        self.todo = None
        self.todo_review = None

    def make_skeleton(self):
        self.days = self.find_node(["days"]) or self.createchild('days')
        today = self.find_node(["days", "day: today"])
        if not today:
            today = self.days.createchild('day', 'today')
        if (not self.active_node or
                today not in list(self.active_node.iter_parents())):
            self.activate(today)

        self.todo = self.find_node(["todo bucket"])
        if not self.todo:
            self.createchild("todo bucket")
        self.fitness_log = self.find_node(["fitness log"])
        if not self.fitness_log:
            self.fitness_log = self.createchild("fitness log")

    def activate(self, node):
        # jump to a particular node as active
        if not node.can_activate:
            log.msg("Attempted to activate node: %r" % node)
            return

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
        #TODO: it doesn't?
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

    def ui_serialize(self):
        result = super(TreeRootNode, self).ui_serialize()
        for child in result["children"]:
            child["is_toplevel"] = True
        return result["children"]  # !
