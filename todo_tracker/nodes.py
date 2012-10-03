from weakref import WeakKeyDictionary
from datetime import datetime

from todo_tracker.tracker import Tree, nodecreator, Option, BooleanOption
from todo_tracker import timefmt

class ActiveMarker(BooleanOption):
    def set(self, node, name, value):
        super(ActiveMarker, self).set(node, name, value)
        node.tracker.activate(node)


@nodecreator("worked on")
class BaseTask(Tree):
    options = (
        ("started", timefmt.datetime_option),
        ("finished", timefmt.datetime_option),
        ("active", ActiveMarker())
    )
    def __init__(self, node_type, text, parent, tracker):
        super(BaseTask, self).__init__(node_type, text, parent, tracker)

        self.started = None
        self.finished = None
        self.active = False

        self.referred_to = set()

    def start(self):
        if self.started:
            return
            # wtf do we do now?
            raise Exception("fixme, need to do something about restarts")
        self.started = datetime.now()

    def finish(self):
        self.finished = datetime.now()

    @property
    def can_activate(self):
        return self.finished is None

@nodecreator("task")
@nodecreator("project")
@nodecreator("bug")
@nodecreator("feature")
class Task(BaseTask):
    multiline = True
    options = (
        ("timeframe", timefmt.datetime_option),
    )

    def __init__(self, node_type, text, parent, tracker):
        super(Task, self).__init__(node_type, text, parent, tracker)

        self.timeframe = None

@nodecreator("day")
class Day(BaseTask):
    chidren_of = ("days",)
    text_required = True

    def __init__(self, node_type, text, parent, tracker):
        super(Day, self).__init__(node_type, text, parent, tracker)

    @property
    def text(self):
        return timefmt.date_to_str(self.date)

    @text.setter
    def text(self, new):
        self.date = timefmt.str_to_date(new)

    @property
    def can_activate(self):
        if not datetime.now().date() == self.date:
            return False
        return super(Day, self).can_activate

@nodecreator("repeating tasks")
class RepeatingTasks(Tree):
    textless = True

@nodecreator("days")
class Days(Tree):
    textless = True
    toplevel = True
    allowed_children = ["repeating tasks", "day"]

    def __init__(self, node_type, text, parent, tracker):
        super(Days, self).__init__(node_type, text, parent, tracker)
        self.repeating_tasks = None
        self.day_children = {}

    @property
    def today(self):
        today = datetime.now().date()
        try:
            result = self.day_children[today]
        except KeyError:
            result = self.createchild("day", today)
        return result

    def addchild(self, child, *args, **keywords):
        if child.node_type == "repeating tasks":
            if self.repeating_tasks is not None:
                raise Exception("herp derp")
            self.repeating_tasks = child
            return

        if len(args) or len(keywords):
            raise Exception("this addchild does not take any special arguments")
        before = None
        after = None

        if self.allowed_children is not None and child.node_type not in self.allowed_children:
            raise Exception("node %s cannot be child of %r" % (child._do_repr(parent=False), self))

        for existing_child in self.children:
            if existing_child.date < child.date:
                if after is None or existing_child.date > after.date:
                    after = existing_child
            elif existing_child.date > child.date:
                if before is None or existing_child.date < before.date:
                    before = existing_child

        ret = super(Days, self).addchild(child, before=before, after=after)
        self.day_children[child.date] = child
        return ret

    def children_export(self):
        prefix = []
        if self.repeating_tasks is not None:
            prefix.append(self.repeating_tasks)
        return prefix + list(self.children)

@nodecreator("category")
class Category(Tree):
    # should be passthrough
    pass

@nodecreator("comment")
@nodecreator("IGNORE")
class Comment(Tree):
    multiline = True

@nodecreator("event")
class Event(BaseTask):
    multiline = True
    options = (
        ("when", timefmt.datetime_option),
        ("where", Option()),
    )

@nodecreator("todo")
class TodoItem(Tree):
    children_of = ["todo bucket"]
    allowed_children = []
    multiline = True

@nodecreator("todo bucket")
class TodoBucket(Tree):
    toplevel = True
    allowed_children = ["todo"]

    def __init__(self, node_type, text, parent, tracker):
        super(TodoBucket, self).__init__(node_type, text, parent, tracker)

    def load_finished(self):
        self.tracker.todo = self

    def move_review_task(self):
        todo_review = self.tracker.todo_review
        if not len(self.children):
            self.tracker.todo_review = None
            todo_review.detach()
            return

        active = self.tracker.active_node
        if not active:
            return # not much we can do :(
        newparent = None
        after_node = None
        for node in active.iter_parents():
            after_node = newparent
            newparent = node
            if node is self.tracker.root or newparent.node_type == "day":
                break

        if newparent == self or newparent == todo_review:
            raise Exception("about to have a fit")
        if todo_review and after_node is todo_review:
            after_node = after_node.next_neighbor

        if todo_review:
            todo_review.detach()
            todo_review = todo_review.copy(parent=newparent)
            newparent.addchild(todo_review, after=after_node)
        else:
            todo_review = newparent.createchild("todo review", after=after_node)

        self.tracker.todo_review = todo_review

    def addchild(self, child, *args, **keywords):
        child = super(TodoBucket, self).addchild(child, *args, **keywords)
        self.move_review_task()
        return child

@nodecreator("todo review")
class TodoReview(BaseTask):
    textless = True
    def __init__(self, node_type, text, parent, tracker):
        super(TodoReview, self).__init__(node_type, text, parent, tracker)

    def load_finished(self):
        if self.tracker.todo_review and self.tracker.todo_review is not self:
            self.tracker.todo_review.detach()
        self.tracker.todo_review = self
        self.tracker.todo.move_review_task()

    def start(self):
        self.tracker.start_editor()

    def finish(self):
        super(TodoReview, self).finish()
        self.tracker.todo.move_review_task()


@nodecreator("_gennode")
class GenericNode(Tree):
    multiline = True

    def __init__(self, node_type="_gennode", text=None, parent=None, tracker=None):
        super(GenericNode, self).__init__(node_type, text, parent, tracker)
        self.metadata = {}

    def setoption(self, option, value):
        self.metadata[option] = value

    def option_values(self, adapter=None):
        return [(x, y, True) for x, y in self.metadata.items()]

@nodecreator("_genactive")
class GenericActivate(GenericNode):
    def __init__(self, node_type="_genactive", text=None, parent=None, tracker=None):
        super(GenericActivate, self).__init__(node_type, text, parent, tracker)
        self.deactivate = False

    def setoption(self, option, value):
        if option == "active":
            self.tracker.activate(self)
        super(GenericActivate, self).setoption(option, value)

    @property
    def active(self):
        return "active" in self.metadata

    @active.setter
    def active(self, newvalue):
        if "active" in self.metadata:
            del self.metadata["active"]

        if newvalue:
            self.metadata["active"] = None

    def start(self):
        if "deactivate" in self.metadata:
            del self.metadata["deactivate"]
            self.deactivate = True

    def finish(self):
        if self.deactivate:
            self.metadata["locked"] = None

    @property
    def can_activate(self):
        return not "locked" in self.metadata

def _makeproxy(parent, proxied):
    return parent.tracker.nodecreator.create("work on", proxied.text, parent, parent.tracker)

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
                proxy = instance # pragma: no cover - never runs because it's always already proxied
            elif not self.is_nodelist and value is target.parent.children:
                proxy = instance.parent.children # pragma: no cover - again, never runs because already proxied
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
                if isinstance(result, BaseTask) or isinstance(result, _NodeListRoot):
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

from todo_tracker.tracker import _NodeListRoot
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
    def tracker(self):
        return self.parent.tracker

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
class DummyReference(Tree):
    is_reference = True
    _next_node = _AutoReference("_real_next_node", "_next_node", False)
    _prev_node = _AutoReference("_real_prev_node", "_prev_node", False)
    children_of = ("work on",)

    def __init__(self, node_type, text, parent, tracker):
        self.target = None
        self.proxies = parent.proxies

        super(Reference, self).__init__(node_type, text, parent, tracker)

    def _init_children(self):
        self.children = _ReferenceNodeList(self)
        self._real_next_node = None
        self._real_prev_node = None

    @property
    def text(self):
        return self.target.node_type + (": " + self.target.text if self.target.text else "")

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

    def __init__(self, node_type, text, parent, tracker):
        if parent.node_type != "work on":
            del self._next_node
            del self._prev_node
        self.target = None
        if parent.node_type == "work on":
            self.proxies = parent.proxies
        else:
            # there is no more waffles! I have them all!
            self.proxies = WeakKeyDictionary()

        super(Reference, self).__init__(node_type, text, parent, tracker)


    def _init_children(self):
        self.children = _ReferenceNodeList(self)
        self._real_next_node = None
        self._real_prev_node = None


    @property
    def point_of_reference(self):
        if self.parent.node_type == "work on":
            return self.parent.target
        return self.tracker.root

    @property
    def text(self):
        if self.target is None:
            return None
        nodes = []
        for node in self.target.iter_parents(): # pragma: no branch
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
        options = [(name, item, show) for name, item, show in self.option_values() if show]
        return self.prev_is_solid or self.next_is_solid or len(options)

    def addchild(self, child, before=None, after=None):
        self.log()
        if child.node_type in self.allowed_children:
            return super(Reference, self).addchild(child, before=before, after=after)
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
            try: # pragma: no branch
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
            print "%s.%s > " % (repr(self), frames[1][3]), " ".join(str(x) for x in args)
        except:
            import traceback
            traceback.print_exc()

    def __repr__(self):
        return "(%r: %r)" % (getattr(self, "node_type", "[work on]"), getattr(self, "text", None))

    def finish(self, *args):
        super(Reference, self).finish(*args)
        self.node_type = "worked on"
