from weakref import WeakKeyDictionary
import logging

from todo_tracker.nodes.node import Node, nodecreator, _NodeListRoot
from todo_tracker.nodes.tasks import BaseTask
from todo_tracker.util import setter

logger = logging.getLogger(__name__)


class ProxiedAttr(object):
    """
    Override the presence of an attribute on the proxy with a
    retrieval of some sort
    """
    def __init__(self, name, is_node=False, disable=None):
        self.name = name
        self.is_node = is_node
        self.disable = disable

    def __get__(self, instance, owning_class):
        if instance._px_target is None or (
                self.disable and getattr(instance, self.disable, False)):
            return getattr(instance, self.name + "_default", None)
        _my_name = self.name
        _is_node = self.is_node

        proxy_root = instance._px_root
        target_result = getattr(instance._px_target, self.name)
        assert not proxy_root.is_owned(target_result) or \
                proxy_root is target_result
        if self.is_node:
            return proxy_root.get_proxy(target_result)
        return target_result

    def __set__(self, instance, value):
        assert instance._px_target is not None
        assert self.is_node, ("Only node ProxiedAttrs can be written to; "
                "others should wrap inherited methods and class attrs")

        if instance._px_root.is_owned(value):
            value = value._px_target

        setattr(instance._px_target, self.name, value)


class ProxyNode(Node):
    """
               multiline: attr
                textless: attr
           text_required: attr
                toplevel: attr
            can_activate: attr
             children_of: attr
        allowed_children: attr
        preferred_parent: attr

                 options: AttributeError
            _option_dict: AttributeError !

                __init__: internal
          _init_children: unused
                children: node
              _next_node: node
              _prev_node: node

               __initing: auto
                    root: attr
               node_type: auto
                  parent: node
                    text: auto

               _validate: attr
           continue_text: attr

               setoption: attr
           option-values: attr

            iter_parents: inherit/indirect
      iter_flat_children: inherit/indirect
            iter_forward: inherit/indirect
           iter_backward: inherit/indirect
           next_neighbor: inherit/indirect
           prev_neighbor: inherit/indirect
                    find: inherit/indirect
                find_one: inherit/indirect
                  create: inherit/indirect

                addchild: func/indirect
             createchild: inherit/indirect
             removechild: inherit/indirect
                  detach: inherit/indirect
                    copy: func/indirect

           make_skeleton: inherit/indirect
         children_export: func/stub

                   start: attr
                  finish: attr

           load_finished: inherit/stub
                auto_add: func/stub
            ui_serialize: attr
            search_texts: attr
             search_tags: attr
           user_creation: attr
            _search_tags: AttributeError
                 __str__: func/indirect
                _do_repr: func/indirect
                __repr__: inherit/indirect


                -------------------

                  active: nonproxied



    """
    multiline = ProxiedAttr("multiline")
    textless = ProxiedAttr("textless")
    text_required = ProxiedAttr("text_required")
    toplevel = ProxiedAttr("toplevel")
    can_activate = ProxiedAttr("can_activate")

    @property
    def options(self):
        raise AttributeError

    children_of = ProxiedAttr("children_of")
    allowed_children = ProxiedAttr("allowed_children")
    preferred_parent = ProxiedAttr("preferred_parent")

    parent = ProxiedAttr("parent", is_node=True)

    @property
    def root(self):
        return self._px_root.root

    _next_node = ProxiedAttr("_next_node", is_node=True)
    _prev_node = ProxiedAttr("_prev_node", is_node=True)
    children = ProxiedAttr("children", is_node=True, disable="_px_nochildren")

    setoption = ProxiedAttr("setoption")
    # option_values = ProxiedAttr("option_values")

    def option_values(self):
        # TODO: cheap hack
        result = self._px_target.option_values()
        realresult = []
        realresult.append(("active", None, self.root.active_node is self))
        for key, value, show in result:
            if key == "active":
                continue
            realresult.append((key, value, show))
        return realresult

    validate = ProxiedAttr("validate")
    continue_text = ProxiedAttr("continue_text")

    start = ProxiedAttr("start")
    finish = ProxiedAttr("finish")

    search_texts = ProxiedAttr("search_texts")
    search_tags = ProxiedAttr("search_tags")
    user_creation = ProxiedAttr("user_creation")

    _nonproxied = (
        "active",
        "children_default",

        "_px_target",
        "_px_root",
        "_px_nochildren",
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
        "_do_repr",
        "id"
    )

    def __init__(self, proxy_root, target):
        if target is proxy_root:
            self._px_nochildren = True
            self.children_default = ReferenceNodeList(proxy_root, None)
            object.__setattr__(self, "text", "<recursing>")
        self._px_target = target
        self._px_root = proxy_root
        self.referred_to = set()

    def addchild(self, child, before=None, after=None):
        before = self._px_root.unwrap(before)
        after = self._px_root.unwrap(after)
        child = self._px_root.unwrap(child)

        if child.parent is not None:
            assert self._px_root.unwrap(child.parent) is self._px_target
            child.parent = None

        result = self._px_target.addchild(child, before=before, after=after)
        return self._px_root.get_proxy(result)

    def copy(self, parent=None, children=True, options=True):
        if parent is None:
            parent = self.parent

        parent = self._px_root.unwrap(parent)
        return self._px_target.copy(parent, children, options)

    def detach(self):
        return self._px_target.detach()

    def children_export(self):
        return []

    def ui_serialize(self, result=None):
        if result is None:
            result = {}

        result = self._px_target.ui_serialize(result)

        if getattr(self, "active", False):
            result["active"] = True
        if "options" in result:
            del result["options"]

        return Node.ui_serialize(self, result)

        #self._px_target.ui_serialize()

        #return result

    def __getattr__(self, name):
        """
        Fallback in case there isn't a ProxiedAttr
        Most attributes will be retrieved this way; for instance,
        node type and text.
        """
        if name == "options":
            raise AttributeError("proxied nodes do not have"
                " direct access to the options list; use set_option "
                "and option_values")
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

    def __init__(self, proxy_root, target):
        self._next_node_default = self
        self._prev_node_default = self

        self._px_root = proxy_root
        self._px_target = target

    @property
    def length(self):
        if self._px_target is None:
            return 0
        return self._px_target.length

    def insert(self, child, before=None, after=None):  # pragma: no cover
        raise Exception("this should never be called")

    def remove(self, child):
        child = self._px_root.unwrap(child)

        self._px_target.remove(child)


@nodecreator("reference")
@nodecreator("work on")
@nodecreator("workon")
class Reference(BaseTask):

    def __init__(self, *args, **kwargs):
        self.proxies = WeakKeyDictionary()
        self._px_root = self
        self._real_px_target = None
        self._px_didstart = False
        self._px_dostart = False
        self._propagate_started = True
        BaseTask.__init__(self, *args, **kwargs)

        #if self.node_type in ["reference", "work on"]:
        #    self.node_type = "reference"

    def addchild(self, child, before=None, after=None):
        before = self._px_root.unwrap(before)
        after = self._px_root.unwrap(after)
        child = self._px_root.unwrap(child)

        if child.parent is not None:
            assert self._px_root.unwrap(child.parent) is self._px_target
            child.parent = None

        result = self._px_target.addchild(child, before=before, after=after)
        return self._px_root.get_proxy(result)

    @setter
    def _px_target(self, newvalue):
        assert self._px_can_target or newvalue is None
        self._real_px_target = newvalue
        if self.finished is None:
            self.finished = getattr(newvalue, "finished", self.finished)
        self.children = self.get_proxy(newvalue.children)

    @setter
    def started(self, value):
        self._realstarted = value
        if (self._propagate_started
                and self._px_target is not None
                and value
                and not getattr(self._px_target, "started", False)):
            try:
                self._px_target.started = self.started
            except AttributeError:
                pass

    def _init_children(self):
        self.children = ReferenceNodeList(self, None)
        self._next_node = None
        self._prev_node = None

    def _find_target(self):
        _px_target = self.find_one(self.text)
        assert _px_target is not None, "No target found for %r" % self
        return _px_target

    @property
    def _px_can_target(self):
        return not self.finished

    def load_finished(self, target=None):
        if self._px_can_target:
            if target is not None:
                self._px_target = target
            else:
                self._px_target = self._find_target()

        if self._px_dostart:
            self._px_start()
        self.started = self.started

    def is_owned(self, node):
        return getattr(node, "_px_root", None) is self

    def get_proxy(self, target):
        if target is None:
            return None
        if target is self._px_target:
            return self
        try:
            return self.proxies[target]
        except KeyError:
            is_nodelist = hasattr(target, "insert") and hasattr(target,
                    "remove")
            is_node = hasattr(target, "node_type") and hasattr(target, "text")

            assert is_nodelist != is_node  # != is boolean XOR

            if is_nodelist:
                newnode = ReferenceNodeList(self, target)
            else:
                newnode = ProxyNode(self, target)

            self.proxies[target] = newnode
            return newnode

    def unwrap(self, node):
        if not self.is_owned(node):
            return node
        assert node._px_target is not None
        return node._px_target

    def children_export(self):
        return []

    def start(self):
        if self._px_target is not None:
            self._px_start()
        else:
            self._px_dostart = True

    def _px_start(self):
        try:
            self._propagate_started = False

            BaseTask.start(self)
            if (self._px_target.can_activate
                    and not getattr(self._px_target, "started", None)):
                self._px_target.start()
                self._px_didstart = True
            self._px_dostart = False
        finally:
            self._propagate_started = True

    def _finish_cleanup(self):
        self._real_px_target = None
        self.children = ReferenceNodeList(self, None)
        self.proxies = None

    def finish(self):
        BaseTask.finish(self)
        self._finish_cleanup()

    def unfinish(self):
        temp_target = self._find_target()
        assert temp_target is not None, "cannot unfinish if my target is gone!"

        result = temp_target.unfinish()
        if not result:
            return result

        assert BaseTask.unfinish(self), ("was unable to unfinish reference!"
                    " tree state is probably bad!")
        assert not self.finished
        self.proxies = WeakKeyDictionary()
        self._px_dostart = False

        self.load_finished(temp_target)
        return True

    def __str__(self):
        if self._px_target is None:
            return Node.__str__(self)
        result = "%s: %s" % (self.node_type, self._px_target.text)
        return result.partition("\n")[0]


@nodecreator("depends")
@nodecreator("depend")
@nodecreator("dep")
class Depends(Reference):

    def __init__(self, *a, **kw):
        self._propagate_finished = True
        self._px_dofinish = False
        self._px_didfinish = False
        Reference.__init__(self, *a, **kw)

        if self.node_type in ["depend", "dep"]:
            self.node_type = "depends"

    def load_finished(self, target=None):
        Reference.load_finished(self, target)
        if self._px_dofinish:
            self._px_finish()
        print "attempting to set finished..."
        self.finished = self.finished
        print "...done"

        if self.finished:
            self._finish_cleanup()

    @setter
    def finished(self, value):
        self._realfinished = value

        if (self._propagate_finished
                and self._px_target is not None
                and value
                and not getattr(self._px_target, "finished", False)):
            try:
                self._px_target.finished = value
            except AttributeError:
                pass

    @property
    def _px_can_target(self):
        return True

    def finish(self):
        if self._px_target is not None:
            self._px_finish()
        else:
            self._px_dofinish = True

    def _px_finish(self):
        try:
            self._propagate_finished = False

            if (self._px_target.can_activate
                    and not getattr(self._px_target, "finished", None)):
                self._px_target.finish()
                self._px_didfinish = True
            self._px_dofinish = False
            Reference.finish(self)
        finally:
            self._propagate_finished = True
