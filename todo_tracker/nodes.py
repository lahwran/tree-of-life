import datetime

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

    def start(self):
        if self.started:
            return
            # wtf do we do now?
            raise Exception("fixme, need to do something about restarts")
        self.started = datetime.datetime.now()

    def finish(self):
        self.finished = datetime.datetime.now()

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
        if not datetime.datetime.now().date() == self.date:
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
        tracker.days = self
        self.day_children = {}

    @property
    def today(self):
        today = datetime.now().date()
        try:
            result = self.day_children[today]
        except KeyError:
            result = self.createchild("day", today)
        return result

    def addchild(self, child):
        if child.node_type == "repeating tasks":
            if self.repeating_tasks is not None:
                raise Exception("herp derp")
            self.repeating_tasks = child
            return

        before = None
        after = None

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
@nodecreator("todo")
class Comment(Tree):
    multiline = True

@nodecreator("event")
class Event(BaseTask):
    multiline = True
    options = (
        ("when", SimpleOption(IEstimatedDatetime)),
        ("where", SimpleOption(IString)),
    )

@nodecreator("todo bucket")
class TodoBucket(Tree):
    toplevel = True
    allowed_children = ["todo"]

    def __init__(self, node_type, text, parent, tracker):
        super(TodoBucket, self).__init__(node_type, text, parent, tracker)
        tracker.todo = self
