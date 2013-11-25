from __future__ import unicode_literals, print_function

from datetime import datetime
import pytest

from treeoflife.tracker import Tracker, nodecreator
from treeoflife.file_storage import serialize_to_str
from treeoflife.test.util import FakeNodeCreator, match
from treeoflife import navigation
from treeoflife.nodes import tasks


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
        "task: \xfca task\n"
        "    @started: June 7, 2010 7:00 AM"
    )


def test_active_option():
    tracker = Tracker(nodecreator=FakeNodeCreator(tasks.Task),
            skeleton=False)

    tracker.deserialize("str",
        "task: \xfca task\n"
        "    @active"
    )

    assert tracker.root.active_node.text == "\xfca task"


def test_activate_deactivate(monkeypatch):
    from treeoflife.nodes import tasks
    monkeypatch.setattr(tasks, "datetime",
            FakeDatetime(datetime(2012, 10, 24)))
    tracker = Tracker(nodecreator=FakeNodeCreator(tasks.Task),
            skeleton=False)

    tracker.deserialize("str",
        "task: \xfc1\n"
        "    @active\n"
        "task: \xfc2\n"
        "task: \xfc3\n"
    )

    monkeypatch.setattr(tasks, "datetime",
            FakeDatetime(datetime(2012, 10, 25)))
    navigation.done(tracker)
    navigation.done(tracker)

    assert match(tracker.serialize("str"), (
        "task#?????: \xfc1\n"
        "    @finished: 1d after October 24, 2012 12:00:00 AM\n"
        "task#?????: \xfc2\n"
        "    @finished: 0s after October 25, 2012 12:00:00 AM\n"
        "task#?????: \xfc3\n"
        "    @started: October 25, 2012 12:00:00 AM\n"
        "    @active\n"
    ))
