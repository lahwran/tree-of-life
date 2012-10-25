from datetime import datetime

from todo_tracker.nodes.node import Node, Option, BooleanOption, nodecreator
from todo_tracker import timefmt


class ActiveMarker(BooleanOption):
    def set(self, node, name, value):
        super(ActiveMarker, self).set(node, name, value)
        node.root.activate(node)


@nodecreator("worked on")
class BaseTask(Node):
    options = (
        ("started", timefmt.datetime_option),
        ("finished", timefmt.datetime_option),
        ("active", ActiveMarker())
    )

    def __init__(self, *args):
        super(BaseTask, self).__init__(*args)

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

    def __init__(self, *args):
        super(Task, self).__init__(*args)

        self.timeframe = None


@nodecreator("category")
class Category(Node):
    # should be passthrough
    pass


@nodecreator("event")
class Event(BaseTask):
    multiline = True
    options = (
        ("when", timefmt.datetime_option),
        ("where", Option()),
    )
