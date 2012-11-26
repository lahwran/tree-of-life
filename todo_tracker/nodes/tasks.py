from datetime import datetime

from todo_tracker.nodes.node import Node, Option, BooleanOption, nodecreator
from todo_tracker import timefmt


class ActiveMarker(BooleanOption):
    name = "active"

    def set(self, node, value):
        super(ActiveMarker, self).set(node, value)
        node.root.activate(node)


@nodecreator("worked on")
class BaseTask(Node):
    options = (
        timefmt.DatetimeOption("started"),
        timefmt.DatetimeOption("finished"),
        ActiveMarker()
    )

    def __init__(self, *args):
        super(BaseTask, self).__init__(*args)

        self.started = None
        self.finished = None
        self.active = False

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

    def ui_serialize(self, result=None):
        if result is None:
            result = {}

        result["active"] = self.active
        result["finished"] = bool(self.finished)
        return super(BaseTask, self).ui_serialize(result)

@nodecreator("task")
@nodecreator("project")
@nodecreator("bug")
@nodecreator("feature")
class Task(BaseTask):
    multiline = True

    def __init__(self, *args):
        super(Task, self).__init__(*args)


@nodecreator("category")
class Category(Node):
    # should be passthrough
    pass


@nodecreator("event")
class Event(BaseTask):
    multiline = True
    options = (
        timefmt.DatetimeOption("when"),
        # need "where" option maybe
    )
