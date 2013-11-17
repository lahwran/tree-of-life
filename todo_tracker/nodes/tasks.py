from datetime import datetime

from todo_tracker.parseutil import Grammar
from todo_tracker.nodes.node import Node, Option, BooleanOption, nodecreator
from todo_tracker import timefmt


class ActiveMarker(BooleanOption):
    name = "active"

    def set(self, node, value):
        super(ActiveMarker, self).set(node, value)
        node.root.activate(node)

    def get(self, node):
        show, value = super(ActiveMarker, self).get(node)
        if show and node is not node.root.active_node:
            show = node.active = False
        return show, value


class _FinishGrammar(Grammar):
    grammar = """
    finished = (time.timedelta:td wss 'after' wss time.datetime:dt
                        -> ("both", (td, dt))
               |time.datetime:dt -> ("finished", dt)
               )
    """
    bindings = {
        "time": timefmt.TimeGrammar
    }


class StartedOption(timefmt.DatetimeOption):
    def set(self, node, value):
        if value is None:
            node.started = datetime.now()
        else:
            super(StartedOption, self).set(node, value)

    def get(self, node):
        if getattr(node, "finished", None) is not None:
            return False, None
        else:
            return super(StartedOption, self).get(node)


class FinishedOption(object):
    name = "finished"

    def set(self, node, value):
        if value is None:
            node.finished = datetime.now()
            return

        kind, value = _FinishGrammar(value).finished()
        if kind == "finished":
            node.finished = value
        elif kind == "both":
            delta, started = value
            node.finished = started + delta
            node.started = started

    def get(self, node):
        started = getattr(node, "started", None)
        finished = getattr(node, "finished", None)
        if finished is None:
            return False, None
        elif started is None:
            return True, timefmt.datetime_to_str(finished)
        else:
            delta = finished - started
            return True, "%s after %s" % (
                        timefmt.timedelta_to_str(delta),
                        timefmt.datetime_to_str(started) )


@nodecreator("worked on")
class BaseTask(Node):
    options = (
        StartedOption("started"),
        FinishedOption(),
        ActiveMarker()
    )

    def __init__(self, *args, **kwargs):
        super(BaseTask, self).__init__(*args, **kwargs)

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

    def unfinish(self):
        self.finished = None
        return True

    @property
    def can_activate(self):
        return self.finished is None

    def ui_dictify(self, result=None):
        if result is None:
            result = {}

        result["active"] = self.active
        result["finished"] = bool(self.finished)
        return super(BaseTask, self).ui_dictify(result)

    def search_tags(self):
        tags = Node.search_tags(self)
        if self.finished:
            tags.add("finished")
        else:
            tags.add("unfinished")
        if self.started:
            tags.add("started")
        else:
            tags.add("unstarted")
        if self.active:
            tags.add("active")
        else:
            tags.add("inactive")

        return tags


@nodecreator("task")
@nodecreator("question")
@nodecreator("problem")
@nodecreator("project")
@nodecreator("bug")
@nodecreator("feature")
class Task(BaseTask):
    multiline = True


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
