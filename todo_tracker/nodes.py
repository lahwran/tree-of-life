from datetime import datetime

from zope.interface import Interface
from crow2.adapterutil import IString

from todo_tracker.tracker import Tree, nodecreator, SimpleOption, BooleanOption
from todo_tracker.time import IDateTime, IDate, IEstimatedDatetime

class ActiveMarker(BooleanOption):
    def set(self, node, name, value):
        super(ActiveMarker, self).set(node, name, value)
        node.tracker.activate(node)


class BaseTask(Tree):
    options = (
        ("started", SimpleOption(IDateTime)),
        ("finished", SimpleOption(IDateTime)),
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
class Task(BaseTask):
    multiline = True
    options = (
        ("timeframe", SimpleOption(IEstimatedDatetime)),
    )

    def __init__(self, node_type, text, parent, tracker):
        super(Task, self).__init__(node_type, text, parent, tracker)

        self.timeframe = None

@nodecreator("day")
class Day(BaseTask):
    def __init__(self, node_type, text, parent, tracker):
        if text is None:
            raise Exception("date required")
        if parent.node_type != "days":
            raise Exception("can only be child of days")
        super(Day, self).__init__(node_type, text, parent, tracker)

    @property
    def text(self):
        return IString(self.date)

    @text.setter
    def text(self, new):
        self.date = IDate(new)

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
                after = existing_child
            elif existing_child.date > child.date:
                before = existing_child

        super(Days, self).addchild(child, before=before, after=after)
        self.day_children[child.date] = child

    def children_export(self):
        prefix = []
        if self.repeating_tasks is not None:
            prefix.append(self.repeating_tasks)
        return prefix + list(self.children)

@nodecreator("category")
class Category(Tree):
    toplevel = True

@nodecreator("comment")
@nodecreator("IGNORE")
class Comment(Tree):
    multiline = True

@nodecreator("event")
class Event(BaseTask):
    multiline = True
    options = (
        ("when", SimpleOption(IEstimatedDatetime)),
        ("where", SimpleOption(IString)),
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
        super(TodoBucket, self).addchild(child, *args, **keywords)
        self.move_review_task()

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

class _ReferenceNodeList(object):


class _ReferenceSlave(object):
    def __init__(self, begin, end):

@nodecreator("work on")
class Reference(BaseTask):
    def __init__(self, node_type, text, parent, tracker):
        super(Reference, self).__init__(node_type, text, parent, tracker)

    @property
    def text(self):
        nodes = list(self.target.iter_parents(skip_root=True))
        return " > ".join(node.text for node in reversed(nodes))

    @text.setter
    def text(self, newtext):
        path = [x.strip() for x in newtext.split(">")]
        node = self.tracker.find_node(path)
        if not isinstance(node, BaseTask):
            pass # herp derp
        if self.target:
            self.target.referred_to.remove(self)
        self.target = node
        self.target.referred_to.add(self)
