from __future__ import unicode_literals, print_function

from treeoflife.userinterface import Event
from treeoflife.tracker import Tracker
from treeoflife import navigation
from treeoflife.nodes import days


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
    assert not tracker.root.find("todo bucket > todo: \xfctest").first()
    event._inject(navigation.createauto)
    assert tracker.root.find("todo bucket > todo: \xfctest").one()


def test_createauto_activatefirst(setdt):
    setdt(2014, 2, 19, 12)
    tracker = Tracker(skeleton=False)

    tracker.deserialize("str",
        "task: something\n"
        "days\n"
        "    day: today\n"
        "        @active\n"
        "    day: tomorrow\n"
        "    day: September 20, 2014\n"
    )

    day = tracker.root.find("today").one()
    assert tracker.root.active_node is day

    navigation.createauto("task: test", tracker.root)
    node = day.find("test").one()
    assert tracker.root.active_node is node

    navigation.createauto("today", tracker.root)
    assert tracker.root.active_node is day

    navigation.createauto("task: test", tracker.root)
    assert tracker.root.active_node is node
