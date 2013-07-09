from datetime import datetime

import pytest

from todo_tracker.tracker import Tracker, nodecreator
from todo_tracker.file_storage import serialize_to_str
from todo_tracker.test.util import FakeNodeCreator
from todo_tracker import navigation
from todo_tracker.nodes import tasks


class FakeDatetime(object):
    def __init__(self, time):
        self.time = time

    def now(self):
        return self.time


def test_registration():
    assert nodecreator.creators["task"] == tasks.Task


def test_task():
    tracker = Tracker(nodecreator=FakeNodeCreator(tasks.Task),
            skeleton=False)

    tracker.deserialize("str",
        "task: a task\n"
        "    @started: June 7, 2010 7:00 AM"
    )


def test_active_option():
    tracker = Tracker(nodecreator=FakeNodeCreator(tasks.Task),
            skeleton=False)

    tracker.deserialize("str",
        "task: a task\n"
        "    @active"
    )

    assert tracker.root.active_node.text == "a task"


def test_activate_deactivate(monkeypatch):
    from todo_tracker.nodes import tasks
    monkeypatch.setattr(tasks, "datetime",
            FakeDatetime(datetime(2012, 10, 24)))
    tracker = Tracker(nodecreator=FakeNodeCreator(tasks.Task),
            skeleton=False)

    tracker.deserialize("str",
        "task: 1\n"
        "    @active\n"
        "task: 2\n"
        "task: 3\n"
    )

    monkeypatch.setattr(tasks, "datetime",
            FakeDatetime(datetime(2012, 10, 25)))
    navigation.done(tracker)
    navigation.done(tracker)

    assert tracker.serialize("str") == (
        "task: 1\n"
        "    @finished: 1d after October 24, 2012 12:00:00 AM\n"
        "task: 2\n"
        "    @finished: 0s after October 25, 2012 12:00:00 AM\n"
        "task: 3\n"
        "    @started: October 25, 2012 12:00:00 AM\n"
        "    @active\n"
    )
