from weakref import WeakKeyDictionary

from todo_tracker.nodes.node import Node, nodecreator, _NodeListRoot
from todo_tracker.nodes.tasks import BaseTask


def _makeproxy(parent, proxied):
    return parent.root.nodecreator.create("work on", proxied.text, parent)


class _AutoReference(object):
    def __init__(self, name, target_name, is_nodelist):
        self.name = name
        self.target_name = target_name
        self.is_nodelist = is_nodelist

    def get_proxy(self, instance, target, value):
        proxies = instance.proxies
        try:
            return proxies[value]
        except KeyError:
            if self.is_nodelist and value is target:
                # never runs because it's always already proxied
                proxy = instance
            elif not self.is_nodelist and value is target.parent.children:
                # again, never runs because already proxied
                # should these be killed? they're still potential scenarios
                proxy = instance.parent.children
            else:
                proxy = _makeproxy(instance.parent, value)
            proxies[value] = proxy
            return proxy

    def __get__(self, instance, owner):
        result = vars(instance).get(self.name, None)
        if result is None and not getattr(instance, self.deleted_name, False):
            result = target = instance.target
            while True:
                result = getattr(result, self.target_name)
                if (isinstance(result, BaseTask) or
                        isinstance(result, _NodeListRoot)):
                    break
            result = self.get_proxy(instance, target, result)
        return result

    def __set__(self, instance, value):
        print "setting %r.%s to %r" % (instance, self.name, value)
        if not getattr(instance, self.deleted_name, False):
            if value is instance:
                value = None
        vars(instance)[self.name] = value

    @property
    def deleted_name(self):
        return "_" + self.name + "_deleted"

    def __delete__(self, instance):
        setattr(instance, self.deleted_name, True)


class _ReferenceNodeList(_NodeListRoot):
    is_reference = True
    _next_node = _AutoReference("_real_next_node", "_next_node", True)
    _prev_node = _AutoReference("_real_prev_node", "_prev_node", True)
    is_solid = True
    next_is_solid = True
    prev_is_solid = True

    def __init__(self, parent):
        self.parent = parent
        super(_ReferenceNodeList, self).__init__()

    @property
    def target(self):
        return self.parent.target.children

    @property
    def proxies(self):
        return self.parent.proxies

    @property
    def root(self):
        return self.parent.root

    @property
    def length(self):
        print "warning: calculating length of referencenodelist is O(n) time"
        result = 0
        for x in self:
            result += 1
        return result

    @length.setter
    def length(self, newvalue):
        pass

    def __repr__(self):
        return "%r.children" % getattr(self, "parent", None)


@nodecreator("reference")
class DummyReference(Node):
    is_reference = True
    _next_node = _AutoReference("_real_next_node", "_next_node", False)
    _prev_node = _AutoReference("_real_prev_node", "_prev_node", False)
    children_of = ("work on",)

    def __init__(self, node_type, text, parent):
        self.target = None
        self.proxies = parent.proxies

        super(Reference, self).__init__(node_type, text, parent)

    def _init_children(self):
        self.children = _ReferenceNodeList(self)
        self._real_next_node = None
        self._real_prev_node = None

    @property
    def text(self):
        textbody = (": " + self.target.text if self.target.text else "")
        return self.target.node_type + textbody

    @text.setter
    def text(self, newvalue):
        if self.target is not None:
            del self.proxies[self.target]
        self.target = self.parent.target.find_node([newvalue])
        self.proxies[self.target] = self


@nodecreator("work on")
class Reference(BaseTask):
    is_reference = True
    _next_node = _AutoReference("_real_next_node", "_next_node", False)
    _prev_node = _AutoReference("_real_prev_node", "_prev_node", False)
    allowed_children = ("work on", "reference")

    def __init__(self, node_type, text, parent):
        if parent.node_type != "work on":
            del self._next_node
            del self._prev_node
        self.target = None
        if parent.node_type == "work on":
            self.proxies = parent.proxies
        else:
            # there is no more waffles! I have them all!
            self.proxies = WeakKeyDictionary()

        super(Reference, self).__init__(node_type, text, parent)

    def _init_children(self):
        self.children = _ReferenceNodeList(self)
        self._real_next_node = None
        self._real_prev_node = None

    @property
    def point_of_reference(self):
        if self.parent.node_type == "work on":
            return self.parent.target
        return self.root

    @property
    def text(self):
        if self.target is None:
            return None
        nodes = []
        for node in self.target.iter_parents():  # pragma: no branch
            if node is self.point_of_reference:
                break
            nodes.append(node)
        return " > ".join(node.text for node in reversed(nodes))

    @text.setter
    def text(self, newtext):
        path = [("*: " + x.strip()) for x in newtext.split(">")]
        node = self.point_of_reference.find_node(path)
        if not isinstance(node, BaseTask):
            print "oops", node

        if self.target is not None:
            self.target.referred_to.remove(self)
            del self.proxies[self.target]
            del self.proxies[self.target.children]
        self.target = node
        self.target.referred_to.add(self)
        self.proxies[self.target] = self
        self.proxies[self.target.children] = self.children

    def _solidify_link(self, before, after):
        self.log(before, "<~ ~>", after)
        self.log(after._prev_node, "<~ ~>", before._next_node)
        before._next_node = after
        after._prev_node = before
        self.log(before, "<--->", after)
        self.log(after._prev_node, "<--->", before._next_node)

    def _do_solidify(self):
        self.log()
        solidified_links = 0
        if getattr(self._prev_node, "prev_is_solid", True):
            self._solidify_link(self._prev_node, self)
            solidified_links += 1
        if getattr(self._next_node, "next_is_solid", True):
            self._solidify_link(self, self._next_node)
            solidified_links += 1
        self.log("solidified_links", solidified_links)
        if not solidified_links:
            print "WARNING: could not solidify node %r" % self

    def solidify(self):
        self.log()
        for parent in self.iter_parents():
            try:
                solidify = parent._do_solidify
            except AttributeError:
                return
            solidify()

    @property
    def prev_is_solid(self):
        self.log()
        return self._real_prev_node is not None

    @property
    def next_is_solid(self):
        self.log()
        return self._real_next_node is not None

    @property
    def is_solid(self):
        self.log()
        options = [(name, item, show) for name, item, show
                in self.option_values() if show]
        return self.prev_is_solid or self.next_is_solid or len(options)

    def addchild(self, child, before=None, after=None):
        self.log()
        if child.node_type in self.allowed_children:
            return super(Reference, self).addchild(child,
                    before=before, after=after)
        else:
            try:
                if before:
                    before = before.target
                if after:
                    after = after.target
            except AttributeError:
                raise DealWithNonProxyError
            child.parent = self.target
            self.target.addchild(child, before=before, after=after)
            try:  # pragma: no branch
                proxy = self.proxies[child]
            except KeyError:
                proxy = _makeproxy(self, child)
            return proxy

    def children_export(self):
        self.log()
        results = []
        for child in self.children:
            try:
                solid = child.is_solid
            except AttributeError:
                solid = True
            if solid:
                results.append(child)
        return results

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, newvalue):
        self._active = newvalue
        self.log(newvalue)

    def log(self, *args):
        return
        try:
            import inspect
            frames = inspect.stack()
            print "%s.%s > " % (
                    repr(self), frames[1][3]), " ".join(str(x) for x in args)
        except:
            import traceback
            traceback.print_exc()

    def __repr__(self):
        return "(%r: %r)" % (
                getattr(self, "node_type", "[work on]"),
                getattr(self, "text", None))

    def finish(self, *args):
        super(Reference, self).finish(*args)
        self.node_type = "worked on"
