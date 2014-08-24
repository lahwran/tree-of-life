from __future__ import unicode_literals, print_function

import inspect
import operator
import logging
import weakref
import random
import datetime

from treeoflife.ordereddict import OrderedDict
from treeoflife.exceptions import (ListIntegrityError, LoadError,
        CantStartNodeError)
from treeoflife.util import HandlerDict
from treeoflife import file_storage

logger = logging.getLogger(__name__)


class _NodeCreatorTracker(HandlerDict):
    name = "creators"
    autodetect = False

    def create(self, node_type, text, parent, validate=True, nodeid=None):
        from treeoflife.nodes import import_all
        try:
            creator = self.creators[node_type]
        except KeyError:
            raise LoadError("No such node type: %r" % node_type)
        result = creator(node_type, text, parent, nodeid=nodeid)
        if result and validate:
            result._validate()
        return result

    def exists(self, node_type):
        return node_type in self.creators

    def values(self):
        return self.creators.values()

    def __call__(self, name):
        return self.add(name)


nodecreator = _NodeCreatorTracker()


class _NodeListIter(object):
    def __init__(self, nodelist, init_node=None, reverse=False):
        self.nodelist = nodelist

        if init_node is not None:
            self.node = init_node
        else:
            self.node = self.nodelist

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

    def __repr__(self):
        return "NodeListIter(%r)" % (self.node,)


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

    #-------------------------------------------------#
    #                 initialization                  #
    #-------------------------------------------------#

    def __init__(self, node_type, text, parent=None, nodeid=None):
        self.id = nodeid

        self._init_children()

        self.__initing = True  # hack for assignment hooks

        self.root = None
        self.node_type = node_type
        self.parent = parent  # bootstrap parent for use in text hook
        self.text = text

        self.__initing = False
        self.parent = parent  # re-run the parent assignment hooks!

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
        if newparent is not None and self.root is not newparent.root:
            self.root = newparent.root

    @property
    def root(self):
        return self._root

    @root.setter
    def root(self, root):
        self._root = root
        if root is not None:
            if self.id is None:
                self.id = root.generate_id()
            if self.id in root.ids:  # pragma: no cover
                raise LoadError("Duplicate node IDs #%s: %r and %r" % (self.id,
                    self, self.root.ids[self.id]))
            root.ids[self.id] = self
        if (root is not None and not root.loading_in_progress
                and not self.__initing):
            self.load_finished()

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

    def continue_text(self, text):
        if not self.multiline:
            raise LoadError("%r node cannot have newline in text" % self)
        if self.text is None:
            raise LoadError("Cannot add new line to text of node %r,"
                    " since it has no text set" % self)

        self.text += "\n"
        self.text += text

    #-------------------------------------------------#
    #                     options                     #
    #-------------------------------------------------#

    def setoption(self, option, value):
        options = self._option_dict()
        try:
            handler = options[option]
        except KeyError:
            raise LoadError("node %r has no such option %r" % (self, option))

        handler.set(self, value)

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
        self._option_dict_cache = result
        return result

    def option_values(self):
        result = []
        for name, handler in self._option_dict().items():
            show, item = handler.get(self)
            result.append((name, item, show))
        return result

    #-------------------------------------------------#
    #            iterators and movement               #
    #-------------------------------------------------#

    def iter_parents(self, skip_root=False):
        node = self

        while True:
            if skip_root and node is self.root:
                break
            if node is None:
                break
            yield node
            node = node.parent

    def iter_flat_children(self, skipper=False):
        stack = [iter(self.children)]

        def skip():
            skip.skip = True

        while len(stack):
            try:
                item = next(stack[-1])
            except StopIteration:
                stack.pop()
            else:
                if skipper:
                    skip.skip = False
                    yield len(stack), item, skip
                    if not skip.skip:
                        stack.append(iter(item.children))
                else:
                    yield len(stack), item
                    stack.append(iter(item.children))

    def iter_forward(self):
        return _NodeListIter(self.parent.children, init_node=self)

    def iter_backward(self):
        return _NodeListIter(self.parent.children, init_node=self,
                reverse=True)

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

    def find(self, query, rigid=False):
        from treeoflife import searching
        if rigid:
            query = searching.parse_single(query)
        else:
            query = searching.parse(query)
        return query(self)

    #-------------------------------------------------#
    #          adding and removing children           #
    #-------------------------------------------------#

    def create(self, *a, **kw):
        from treeoflife import searching
        creator = searching.parse_create(*a, **kw)
        return creator(self)

    def addchild(self, child, before=None, after=None):
        if (self.allowed_children is not None and
                child.node_type != "" and
                child.node_type not in self.allowed_children):
            raise LoadError("node %s cannot be child of %r" %
                    (child._do_repr(parent=False), self))
        if child.parent is not self and child.parent is not None:
            raise LoadError("node %r does not expect to be a child of %r" %
                    (child, self))
        if before and before.parent is not self:
            raise LoadError("node %r cannot be before node %r as child of %r" %
                    (child, before, self))
        if after and after.parent is not self:
            raise LoadError("node %r cannot be after node %r as child of %r" %
                    (child, after, self))
        self.children.insert(child, before, after)

        if child.parent is None:
            child.parent = self
            child._validate()

        ihook = getattr(child, "_insertion_hook", None)
        if ihook is not None:
            ihook()

        return child

    def createchild(self, node_type, text=None, nodeid=None, **keywords):
        node = self.root.nodecreator.create(node_type, text, self,
                nodeid=nodeid)
        return self.addchild(node, **keywords)

    def removechild(self, child):
        self.children.remove(child)
        child.parent = None

    def detach(self):
        if self.parent:
            self.parent.removechild(self)
        if self.root:
            del self.root.ids[self.id]
        return self

    def copy(self, parent=None, children=True, options=True, nodeid=None):
        if parent is None:
            parent = self.parent

        newnode = self.root.nodecreator.create(self.node_type, self.text,
                parent, nodeid=nodeid)
        if options:
            for option, value, show in self.option_values():
                if show:
                    newnode.setoption(option, value)
        if children:
            for child in self.children_export():
                child_copy = child.copy(parent=newnode)
                newnode.addchild(child_copy)
        return newnode

    #-------------------------------------------------#
    #        hooks for subclasses to override         #
    #-------------------------------------------------#

    @property
    def active_id(self):
        return self.id

    @classmethod
    def make_skeleton(self, root):
        pass

    def children_export(self):
        return list(self.children)

    def start(self):
        """
        Called to start the node
        (todo: isn't this a task-specific thing?)
        """
        if not self.can_activate:
            raise CantStartNodeError("can't start node %r" % self)

    def finish(self):
        """
        Called when the node is finished
        (todo: isn't this a task-specific thing?)
        """

    def load_finished(self):
        """
        Called when the  system is ready for the node to do
        things to the tree
        """

    def auto_add(self, creator, root):
        self.root = root
        if self.preferred_parent is not None:
            parent = creator.find(self.preferred_parent).one()
            parent.addchild(self)
            return parent
        else:
            return None

    def ui_dictify(self, result=None):
        """
        Called to create a json version of the node, for the ui
        """
        if result is None:
            result = {}

        if "options" not in result:
            options = [dict(zip(["type", "text"], option)) for option
                    in self.option_values() if option[-1]]
            if options:
                result["options"] = options
        if "children" not in result:
            children = [child.id for child in self.children]
            if children:
                result["children"] = children
        result["type"] = self.node_type
        result["text"] = self.text
        result["id"] = self.id
        result["active_id"] = self.active_id
        return result

    def ui_graph(self):
        nodes = {self.id: self.ui_dictify()}
        for depth, node, skip in self.iter_flat_children(skipper=True):
            d = node.ui_dictify()
            if d is None:
                skip()
                continue
            nodes[node.id] = d
        return nodes

    def search_texts(self):
        """
        Called to determine what texts the node will match
        """
        return set([self.node_type]), set([self.text])

    def search_tags(self):
        """
        called to determine what tags the node will match
        """
        return set()

    def user_creation(self):
        """
        called when the node is created by user interaction
        (not called on deserialize)
        """

    #-------------------------------------------------#
    #                      misc                       #
    #-------------------------------------------------#

    def _search_tags(self):
        tags = set(self.search_tags())
        if self.can_activate:
            tags.add("can_activate")
        else:
            tags.add("cannot_activate")
        return tags

    def __str__(self):
        if self.text:
            result = "%s: %s" % (self.node_type, self.text)
        else:
            result = self.node_type
        return result.partition("\n")[0]

    def _format_repr_error(self, errors, name):
        import traceback
        result = "EXCEPTION IN REPR: %s\n" % name
        if errors is not None:
            errors.append(result + traceback.format_exc())
        return "[! " + name + " !]"

    def _format_repr_errors(self, errors):
        if not errors:
            return ""
        result = ""
        for error in errors:
            result += "\n\n"
            result += error
        return result

    def _do_repr(self, parent=True, exceptions=False):
        if exceptions:
            errors = []
        else:
            errors = None
        do_parent = parent
        del parent

        try:
            node_type = getattr(self, "node_type", None)
        except Exception as e:
            node_type = self._format_repr_error(
                    errors, "node_type")
        try:
            text = getattr(self, "text", None)
        except Exception as e:
            text = self._format_repr_error(
                    errors, "text")

        if do_parent:
            parent_repr = "None"
            try:
                parent = getattr(self, "parent", None)
            except Exception as e:
                parent = None
                parent_repr = self._format_repr_error(
                        errors, "self.parent")
            if parent is not None:
                try:
                    parent_repr = str(parent)
                except Exception as e:
                    parent_repr = self._format_repr_error(
                            errors, "str(parent)")

            return "<%s (%s) %r: %r>" % (
                    type(self).__name__,
                    parent_repr,
                    node_type,
                    text
            ) + self._format_repr_errors(errors)
        else:
            return "<%s %r: %r>" % (
                    type(self).__name__,
                    node_type,
                    text
            ) + self._format_repr_errors(errors)

    def __repr__(self):
        return self._do_repr()


@nodecreator('-')
def continue_text(node_type, text, parent, nodeid):
    parent.continue_text(text)


@nodecreator("")
class EmptyLineNode(Node):
    pass


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
    """
    log is a list of events:
    [
        (path, eventtype, time),
        (path, eventtype, time),
        ...
    ]
    where path is a list of nodes:
    [
        (id, node_type, text),
        (id, node_type, text),
        ...
    ]
    and where eventtype is a string, and time is a datetime object.
    """
    can_activate = True

    def __init__(self, tracker, nodecreator, loading_in_progress=False):
        self.ids = weakref.WeakValueDictionary()
        self.nodecreator = nodecreator
        self.tracker = tracker
        self.loading_in_progress = loading_in_progress

        super(TreeRootNode, self).__init__("life", None, None, nodeid="00000")
        self.root = self

        self.editor_callback = None

        self.log = []

        self.days = None
        self.active_node = self
        self.todo = None
        self.todo_review = None

    def load_finished(self):
        if getattr(self, "_alarm_hook", None) is not None:
            self._alarm_hook()

    def make_skeleton(self):
        for node_class in set(self.nodecreator.values()):
            func = getattr(node_class, "make_skeleton", None)
            if func:
                func(self)

    def log_activation(self, deepestnode):
        path = [(node.id, node.node_type, node.text)
                for node in list(deepestnode.iter_parents())[::-1]]
        logitem = (path, "activation", datetime.datetime.now())
        self.log.append(logitem)

    def activate(self, node, force=False):
        # jump to a particular node as active
        if not node.can_activate:
            if force:
                unfinish = getattr(node, "unfinish", None)
            else:
                unfinish = None
            if unfinish is None or not unfinish():
                logger.warn("Attempted to activate node: %r", node)
                return

        self.active_node = node
        self.log_activation(self.active_node)
        for parent_node in list(node.iter_parents())[::-1]:
            try:
                parent_node.start()
            except CantStartNodeError:
                if parent_node is node:
                    raise

    def generate_id(self):
        for x in xrange(10):
            nodeid = "".join(random.choice(file_storage.nodeidchars)
                    for x in xrange(5))
            if nodeid in self.ids:
                continue
            return nodeid
        else:  # pragma: no cover
            raise Exception("10 tries to generate node id failed. wat? %s"
                    % nodeid)

#    def _skip_ignored(self, peergetter, node):
#        while node is not None:
#            if node.can_activate:
#                return node
#            node = peergetter(node)
#        return None
#
#    def _descend(self, peergetter, node):
#        while peergetter(node.children):
#            next_node = peergetter(node.children)
#            next_node = self._skip_ignored(peergetter, next_node)
#            if next_node:
#                node = next_node
#            else:
#                break
#        return node
#
#    def _navigate(self, peerattr):
#        #TODO: does not take skipping already-done ones into account
#        #TODO: it doesn't?
#        peergetter = operator.attrgetter(peerattr)
#
#        node = self.active_node
#
#        newnode = self._descend(peergetter, node)
#        if newnode is not node:
#            self.activate(newnode)
#            return
#
#        newnode = self._skip_ignored(peergetter, peergetter(node))
#        if newnode is not None:
#            self.activate(newnode)
#            node.finish()
#            return
#
#        newnode = self._skip_ignored(peergetter, node.parent)
#        if newnode:
#            self.activate(newnode)
#            node.finish()
#            return
#
#    def activate_next(self, *args, **keywords):
#        return self._navigate("next_neighbor", *args, **keywords)
#
#    def activate_prev(self, *args, **keywords):
#        return self._navigate("prev_neighbor", *args, **keywords)
#
#    def _create_related(self, node_type, text, relation, activate):
#        newnode = self.active_node.parent.createchild(node_type, text,
#                **{relation: self.active_node})
#        if activate:
#            self.activate(newnode)
#        return newnode
#
#    def create_before(self, node_type, text=None, activate=True):
#        return self._create_related(node_type, text, "before", activate)
#
#    def create_after(self, node_type, text=None, activate=True):
#        return self._create_related(node_type, text, "after", activate)
#
#    def create_child(self, node_type, text=None, activate=True):
#        newnode = self.active_node.createchild(node_type, text)
#        if activate:
#            self.activate(newnode)
#        return newnode
