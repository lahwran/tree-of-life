from datetime import datetime, date, time, timedelta

from twisted.python import log

from todo_tracker.nodes.node import Node, nodecreator
from todo_tracker import timefmt
from todo_tracker.nodes.tasks import BaseTask
from todo_tracker.nodes.misc import Archived

task_types = ("day", "sleep")


class DateTask(BaseTask):
    chidren_of = ("days",)
    text_required = True

    @property
    def can_activate(self):
        return super(DateTask, self).can_activate and self.acceptable()

    @property
    def text(self):
        return timefmt.date_to_str(self.date)

    @text.setter
    def text(self, new):
        self.date = timefmt.str_to_date(new)


@nodecreator("day")
class Day(DateTask):
    def __gt__(self, other):
        return self.date > other.date

    def __lt__(self, other):
        if other.node_type == "sleep":
            return self.date <= other.date
        return self.date < other.date

    def acceptable(self):
        """
        Returns level of acceptable-ness of activating this day
        """
        now = datetime.now()
        origin = datetime.combine(self.date, time.min)
        start = origin + timedelta(hours=6)
        end = origin + timedelta(days=1)
        morning = end + timedelta(hours=6)
        if now < origin or now > morning:
            return 0
        if now >= end or now <= start:
            return 1
        return 3


@nodecreator("sleep")
class Sleep(DateTask):
    def __gt__(self, other):
        if other.node_type == "day":
            return self.date >= other.date
        return self.date > other.date

    def __lt__(self, other):
        return self.date < other.date

    def acceptable(self):
        # because sleep is shifted forwards
        if (datetime.now() - timedelta(hours=12)).date() == self.date:
            return 2
        return 0


@nodecreator("days")
class Days(Node):
    textless = True
    toplevel = True
    allowed_children = [
        "day",
        "archived",
        "unarchive",
        "sleep"
    ]

    def __init__(self, *args):
        super(Days, self).__init__(*args)
        self.day_children = {}
        self.archive_date = (datetime.now() - timedelta(days=31)).date()

    def active_day(self):
        for parent in self.root.active_node.iter_parents():
            if parent.parent is self:
                return parent
        return None

    def sleep(self, amount=None, until=None):
        current = self.active_day()
        if current.node_type == "sleep":
            raise Exception("already sleeping")

        assert current.node_type == "day"

        sleep_day = (datetime.now() - timedelta(hours=4)).date()
        warn_skip = []
        sleep_node = None

        for node in current.iter_forward():
            if node.node_type in task_types:
                if node.date > sleep_day:
                    sleep_node = None
                    break
                elif node.node_type == "sleep" and node.date == sleep_day:
                    sleep_node = node
                    break
                else:
                    warn_skip.append(node)

        if sleep_node is None:
            sleep_node = Sleep("sleep", "today", self)
            sleep_node.initialize(date=sleep_day, amount=amount, until=until)
            self.addchild(sleep_node)
        else:
            sleep_node.update(amount=amount, until=until)

        for node in warn_skip:
            sleep_node.createchild("comment", "WARNING: skipped %r" % node)

        if not sleep_node.can_activate:
            raise Exception("Couldn't activate sleep node")
        prev_active = self.root.active_node
        self.root.activate(sleep_node)

        for node in prev_active.iter_parents():
            node.finish()
            if node is current:
                break

    @classmethod
    def make_skeleton(cls, root):
        root.days = root.find_node(["days"]) or root.createchild('days')

        do_activate = False
        if root.active_node is None:
            do_activate = True
        else:
            for parent in root.active_node.iter_parents():
                if (parent.node_type in task_types and
                        parent.acceptable()):
                    break
            else:
                do_activate = True

        if do_activate:
            acceptables = []
            for child in root.days.children:
                if child.node_type in task_types:
                    acceptability = child.acceptable()
                    if acceptability:
                        if not child.can_activate:
                            log.msg(("WARNING: node was acceptable but could "
                                "not activate: %r") % child)
                            continue
                        acceptables.append((acceptability, child))

            if acceptables:
                acceptables = sorted(acceptables, key=lambda x: x[0])
                root.activate(acceptables[-1][1])
            else:
                today = root.days.createchild("day", "today")
                root.activate(today)

    def addchild(self, child, before=None, after=None):
        if child.node_type in task_types:
            if before is not None or after is not None:
                log.msg("attempted to specify position of days-sorted node")

            before = None
            after = None
            for existing_child in reversed(self.children):
                if existing_child.node_type not in task_types:
                    continue

                if (existing_child.node_type == child.node_type and
                        existing_child.date == child.date):
                    log.msg("WARNING: duplicate nodes added: %r and %r"
                            % (existing_child, child))
                elif existing_child < child:
                    break
                else:
                    before = existing_child
        if child.node_type not in self.allowed_children:
            raise Exception("node %s cannot be child of %r" % (
                child._do_repr(parent=False), self))

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
