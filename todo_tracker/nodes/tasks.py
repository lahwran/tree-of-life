from datetime import datetime

from todo_tracker.tracker import Tree, Option, BooleanOption, nodecreator
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

@nodecreator("category")
class Category(Tree):
    # should be passthrough
    pass

@nodecreator("event")
class Event(BaseTask):
    multiline = True
    options = (
        ("when", timefmt.datetime_option),
        ("where", Option()),
    )