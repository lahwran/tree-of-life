from datetime import datetime

from todo_tracker.nodes.node import Node, nodecreator
from todo_tracker import timefmt
from todo_tracker.nodes.tasks import BaseTask


@nodecreator("day")
class Day(BaseTask):
    chidren_of = ("days",)
    text_required = True

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


@nodecreator("days")
class Days(Node):
    textless = True
    toplevel = True
    allowed_children = ["repeating tasks", "day"]

    def __init__(self, *args):
        super(Days, self).__init__(*args)
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
            raise Exception("this addchild does not take order arguments")
        before = None
        after = None

        if (self.allowed_children is not None and
                child.node_type not in self.allowed_children):
            raise Exception("node %s cannot be child of %r" % (
                child._do_repr(parent=False), self))

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
