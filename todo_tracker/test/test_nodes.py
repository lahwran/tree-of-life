from datetime import datetime

from todo_tracker.tracker import Tracker, nodecreator
from todo_tracker import nodes
from todo_tracker.file_storage import serialize_to_str
from todo_tracker.test.util import FakeNodeCreator

class FakeDatetime(object):
    def __init__(self, time):
        self.time = time

    def now(self):
        return self.time

def test_registration():
    assert nodecreator.creators["task"] == nodes.Task

def test_task():
    tracker = Tracker(FakeNodeCreator(nodes.Task), auto_skeleton=False)

    tracker.load(
        "task: a task\n"
        "    @started: June 7, 2010 7:00 AM"
    )

def test_active_option():
    tracker = Tracker(FakeNodeCreator(nodes.Task), auto_skeleton=False)

    tracker.load(
        "task: a task\n"
        "    @active"
    )

    assert tracker.active_node.text == "a task"

def test_activate_deactivate(monkeypatch):
    monkeypatch.setattr(nodes, "datetime", FakeDatetime(datetime(2012, 10, 24)))
    tracker = Tracker(FakeNodeCreator(nodes.Task), auto_skeleton=False)

    tracker.load(
        "task: 1\n"
        "    @active\n"
        "task: 2\n"
        "task: 3\n"
    )

    tracker.activate_next()
    tracker.activate_next()

    assert serialize_to_str(tracker.root) == (
        "task: 1\n"
        "    @started: October 24, 2012 12:00 AM\n"
        "    @finished: October 24, 2012 12:00 AM\n"
        "task: 2\n"
        "    @started: October 24, 2012 12:00 AM\n"
        "    @finished: October 24, 2012 12:00 AM\n"
        "task: 3\n"
        "    @started: October 24, 2012 12:00 AM\n"
        "    @active\n"
    )


