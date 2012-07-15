
from todo_tracker.tracker import Tracker, nodecreator
from todo_tracker.nodes import Task
from todo_tracker.test.util import FakeNodeCreator

def test_registration():
    assert nodecreator.creators["task"] == Task

def test_task():
    tracker = Tracker(FakeNodeCreator(Task))

    tracker.load(
        "task: a task\n"
        "    @started: June 7, 2010 7:00 AM"
    )
