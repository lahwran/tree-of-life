from datetime import datetime, date, timedelta

from twisted.python import log

from todo_tracker.nodes.node import Node, nodecreator
from todo_tracker import timefmt
from todo_tracker.nodes.tasks import BaseTask
from todo_tracker.nodes.misc import Archived


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
    allowed_children = ["repeating tasks", "day", "archived", "unarchive"]

    def __init__(self, *args):
        super(Days, self).__init__(*args)
        self.repeating_tasks = None
        self.day_children = {}
        self.archive_date = (datetime.now() - timedelta(days=31)).date()

    @classmethod
    def make_skeleton(cls, root):
        root.days = root.find_node(["days"]) or root.createchild('days')
        today = root.find_node(["days", "day: today"])
        if not today:
            today = root.days.createchild('day', 'today')
        if (not root.active_node or
                today not in list(root.active_node.iter_parents())):
            root.activate(today)

    @property
    def today(self):
        today = datetime.now().date()
        try:
            result = self.day_children[today]
        except KeyError:
            result = self.createchild("day", today)
        return result

    def addchild(self, child, before=None, after=None):
        if child.node_type == "repeating tasks":
            if self.repeating_tasks is not None:
                raise Exception("herp derp")
            self.repeating_tasks = child
            return

        if child.node_type == "day":
            if before is not None or after is not None:
                log.msg("attempted to specify position of day node")

            if (self.allowed_children is not None and
                    child.node_type not in self.allowed_children):
                raise Exception("node %s cannot be child of %r" % (
                    child._do_repr(parent=False), self))

            for existing_child in self.children:
                if existing_child.node_type != "day":
                    if after is not None:
                        after = existing_child
                    continue

                if existing_child.date < child.date:
                    if after is None or existing_child.date > after.date:
                        after = existing_child
                elif existing_child.date > child.date:
                    if before is None or existing_child.date < before.date:
                        before = existing_child

        ret = super(Days, self).addchild(child, before=before, after=after)
        if child.node_type == "day":
            self.day_children[child.date] = child
        return ret

    def load_finished(self):
        for child in self.children:
            if child.node_type == "day" and child.date < self.archive_date:
                prev_node = child.prev_neighbor
                next_node = child.next_neighbor
                child.detach()
                self.addchild(Archived.fromnode(child, parent=self),
                        before=next_node, after=prev_node)

    def children_export(self):
        prefix = []
        if self.repeating_tasks is not None:
            prefix.append(self.repeating_tasks)
        return prefix + list(self.children)

    def ui_serialize(self, result=None):
        if result is None:
            result = {}

        today_string = timefmt.date_to_str(timefmt.str_to_date("today"))
        past_days = []
        future_days = []
        current = past_days
        for node in self.children:
            if node.text == today_string:
                current = future_days
            current.append(node)

        if "hidden_children" not in result and past_days:
            hidden = [child.ui_serialize() for child in past_days]
            result["hidden_children"] = hidden
        if "children" not in result and future_days:
            children = [child.ui_serialize() for child in future_days]
            result["children"] = children

        return super(Days, self).ui_serialize(result)
