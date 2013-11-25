from __future__ import unicode_literals, print_function

from treeoflife.userinterface import Event
from treeoflife.tracker import Tracker
from treeoflife import navigation


def test_createauto_todo_integration():
    tracker = Tracker(skeleton=False)
    days = tracker.root.createchild("days")
    day = days.createchild("day", "today")
    tracker.root.activate(day)
    tracker.root.createchild("todo bucket", None)
    event = Event(None, tracker.root, "createauto",
        "todo: \xfctest",
        tracker
    )
    assert not tracker.root.find_one("todo bucket > todo: \xfctest")
#    import pytest; pytest.set_trace()
    navigation.createauto(event)
    assert tracker.root.find_one("todo bucket > todo: \xfctest")
