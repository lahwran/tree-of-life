from weakref import WeakKeyDictionary
import logging

from todo_tracker.nodes.node import Node, nodecreator, _NodeListRoot
from todo_tracker.nodes.tasks import BaseTask

logger = logging.getLogger(__name__)


class ProxiedAttr(object):
    """
    Override the presence of an attribute on the proxy with a
    retrieval of some sort
    """
    def __init__(self, name, is_node=False):
        self.name = name
        self.is_node = is_node

    def __get__(self, instance, owning_class):
        if instance._px_target is None:
            return getattr(instance, self.name + "_default", None)
        _my_name = self.name
        _is_node = self.is_node

        proxy_root = instance._px_root
        target_result = getattr(instance._px_target, self.name)
        assert not proxy_root.is_owned(target_result)
        if self.is_node:
            return proxy_root.get_proxy(target_result)
        return target_result

    def __set__(self, instance, value):
        assert instance._px_target is not None

        if self.is_node:
            if instance._px_root.is_owned(value):
                value = value._px_target
        else:
            assert not instance._px_root.is_owned(value)

        setattr(instance._px_target, self.name, value)

class ProxyNode(Node):
    multiline = ProxiedAttr("multiline")
    textless = ProxiedAttr("textless")
    text_required = ProxiedAttr("text_required")
    toplevel = ProxiedAttr("toplevel")
    can_activate = ProxiedAttr("can_activate")
    @property
    def options(self): raise AttributeError("proxied nodes do not have"
                " direct access to the options list; use set_option "
                "and option_values")
    children_of = ProxiedAttr("children_of")
    allowed_children = ProxiedAttr("allowed_children")
    preferred_parent = ProxiedAttr("preferred_parent")

    parent = ProxiedAttr("parent", is_node=True)
    @property
    def root(self):
        return self._px_root.root
    _next_node = ProxiedAttr("_next_node", is_node=True)
    _prev_node = ProxiedAttr("_prev_node", is_node=True)
    children = ProxiedAttr("children", is_node=True)

    setoption = ProxiedAttr("setoption")
    option_values = ProxiedAttr("option_values")

    _nonproxied = (
        "_px_target",
        "_px_root",
        "children",
        "referred_to",

        "iter_parents",
        "iter_flat_children",
        "iter_forward",
        "iter_backward",
        "next_neighbor",
        "prev_neighbor",
        "find",
        "find_one",
        "create",
        "createchild",
        "removechild",
        "detach",
        
        "make_skeleton",
        "load_finished",
        "auto_add",
        "_do_repr"
    )

    def __init__(self, proxy_root, target):
        self._px_target = target
        self._px_root = proxy_root
        self.referred_to = set()

    def addchild(self, child, before=None, after=None):
        assert not self._px_root.is_owned(child)

        before = self._px_root.unwrap(before)
        after = self._px_root.unwrap(after)

        if child.parent is not None: 
            assert child.parent is self
            child.parent = None

        result = self._px_target.addchild(child, before=before, after=after)
        return self._px_root.get_proxy(result)

    def children_export(self):
        return []

    def __str__(self):
        return "<proxy>: " + Node.__str__(self)

    def __getattr__(self, name):
        """
        Fallback in case there isn't a ProxiedAttr
        Most attributes will be retrieved this way; for instance,
        node type and text.
        """
        return getattr(self._px_target, name)

    def __setattr__(self, name, value):
        if name in ProxyNode._nonproxied:
            object.__setattr__(self, name, value)
        else:
            setattr(self._px_target, name, value)

    # this adds all class-level defined thingies to the list of non-proxied
    # values
    _nonproxied += tuple(locals().keys())
    _nonproxied = set(_nonproxied)

class ReferenceNodeList(_NodeListRoot):
    _next_node = ProxiedAttr("_next_node", is_node=True)
    _prev_node = ProxiedAttr("_prev_node", is_node=True)

    def __init__(self, proxy_root, target, is_root=False):
        self._next_node_default = self
        self._prev_node_default = self

        self._px_root = proxy_root
        self._px_is_root = is_root
        assert target is not None or is_root
        self._px_target = target

    def length(self):
        if self.target is None:
            return 0
        return self.target.length()

    def insert(self, child, before=None, after=None):
        before = self._px_root.unwrap(before)
        after = self._px_root.unwrap(after)
        
        


@nodecreator("reference")
class Reference(BaseTask):

    def __init__(self, *args):
        self.proxies = WeakKeyDictionary()
        self._px_root = self
        self._px_target_real = None
        BaseTask.__init__(self, *args)

    @property
    def _px_target(self):
        return self._px_target_real

    @_px_target.setter
    def _px_target(self, newvalue):
        self._px_target_real = newvalue
        self.children = self.get_proxy(newvalue.children)

    def _init_children(self):
        self.children = ReferenceNodeList(self, None, is_root=True)
        self._next_node = None
        self._prev_node = None

    def load_finished(self):
        self._px_target = self.find_one(self.text)
        assert self._px_target is not None

    def is_owned(self, node):
        return getattr(node, "_px_root", None) is self

    def get_proxy(self, target):
        if target is None:
            return None
        try:
            return self.proxies[target]
        except KeyError:
            is_nodelist = hasattr(target, "insert") and hasattr(target, "remove")
            is_node = hasattr(target, "node_type") and hasattr(target, "text")

            assert is_nodelist != is_node  # != is boolean XOR

            if is_nodelist and not is_node:
                newnode = ReferenceNodeList(self, target)
            elif is_node and not is_nodelist:
                newnode = ProxyNode(self, target)

            self.proxies[target] = newnode
            return newnode

    def unwrap(self, node):
        if not self.is_owned(node):
            return
        assert node._px_target is not None
        return node._px_target

    def children_export(self):
        return []
