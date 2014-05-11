from __future__ import unicode_literals, print_function

from datetime import datetime

import pytest

from treeoflife.userinterface import Event
from treeoflife.tracker import Tracker
from treeoflife import navigation
from treeoflife import searching
from treeoflife.nodes import days


def s(command):
    "[s]egments. convenience function for verbose thingy"
    return command.query.queries[-1].segments


def test_createauto_todo_integration():
    tracker = Tracker(skeleton=False)
    days = tracker.root.createchild("days")
    day = days.createchild("day", "today")
    tracker.root.activate(day)
    tracker.root.createchild("todo bucket", None)

    command = navigation.CreateAutoCommand("todo: \xfctest", tracker.root)
    assert command.results == [
        searching._CreateResult(s(command), 0, day,
                actions=["do_nothing"])
    ]

    assert not tracker.root.find("todo bucket > todo: \xfctest").first()
    command.execute()
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

    command = navigation.CreateAutoCommand("task: test", tracker.root)
    z = [
        searching._CreateResult(s(command), 0, day, ["activate"])]
    assert command.results == z
    command.execute()
    node = day.find("test").one()
    assert tracker.root.active_node is node

    command = navigation.CreateAutoCommand("today", tracker.root)
    assert command.results == [
        searching._NodeResult(day, ["activate"])]
    command.execute()
    assert tracker.root.active_node is day

    command = navigation.CreateAutoCommand("task: test", tracker.root)
    assert command.results == [
        searching._NodeResult(node, ["activate"])]
    command.execute()
    assert tracker.root.active_node is node


def test_create(setdt):
    setdt(2014, 5, 9, 12)
    tracker = Tracker(skeleton=False)

    tracker.deserialize("str",
        "days\n"
        "    day: today\n"
        "        @active\n"
    )
    day = tracker.root.find("today").one()

    command = navigation.CreateCommand("task: derp", tracker.root)
    z = [
        searching._CreateResult(s(command), 0, day, ["activate"])]
    command.execute()
    assert tracker.root.active_node is day
    assert tracker.root.find("today > derp").one()


def test_activate(setdt):
    setdt(2014, 5, 9, 12)
    tracker = Tracker(skeleton=False)

    tracker.deserialize("str",
        "days\n"
        "    day: today\n"
        "        @active\n"
        "        task: derp\n"
    )
    day = tracker.root.find("today").one()
    node = day.find(">").one()

    command = navigation.ActivateCommand("task: derp", tracker.root)
    assert command.results == [
        searching._NodeResult(node, ["activate"])]
    command.execute()
    assert tracker.root.active_node is node


def test_createauto_noresults(setdt):
    setdt(2014, 5, 9, 12)
    tracker = Tracker(skeleton=False)

    tracker.deserialize("str",
        "task: something\n"
        "days\n"
        "    day: today\n"
        "        @active\n"
    )
    command = navigation.CreateAutoCommand("derp", tracker.root)
    assert len(command.results) == 0
    assert command.preview()
    command.execute()
    assert len(tracker.root.find("today >").list()) == 0


@pytest.fixture
def donecmd_nodes(setdt):
    setdt(2014, 5, 9, 12)
    tracker = Tracker(skeleton=False)

    tracker.deserialize("str",
        "days\n"
        "    day: today\n"
        "        task: origin\n"
        "            @active\n"
        "            task: child1\n"
        "            task: child2\n"
        "            task: child3\n"
        "        task: peer1\n"
        "        task: peer2\n"
    )
    origin = tracker.root.find("** > origin").one()
    child1, child2, child3 = origin.children
    peer1, peer2 = origin.find("->")
    return (tracker, origin, child1, child2, child3, peer1, peer2)


def test_done_children(donecmd_nodes):
    tracker, origin, child1, child2, child3, peer1, peer2 = donecmd_nodes

    command = navigation.DoneCommand(tracker.root)
    assert command.results == [
        searching._NodeResult(child1, ["activate"]),
        searching._NodeResult(child2, ["activate"]),
        searching._NodeResult(child3, ["activate"])
    ]
    command.execute()
    assert not origin.finished
    assert tracker.root.active_node is child1


def test_done_following(donecmd_nodes):
    tracker, origin, child1, child2, child3, peer1, peer2 = donecmd_nodes

    for child in (child1, child2, child3):
        child.finished = datetime.now()

    command = navigation.DoneCommand(tracker.root)
    assert command.results == [
        searching._NodeResult(peer1, ["finishactivate"]),
        searching._NodeResult(peer2, ["finishactivate"]),
    ]
    command.execute()
    assert tracker.root.active_node is peer1


def test_done_parents(donecmd_nodes):
    tracker, origin, child1, child2, child3, peer1, peer2 = donecmd_nodes

    for node in (child1, child2, child3, peer1, peer2):
        node.finished = datetime.now()

    command = navigation.DoneCommand(tracker.root)
    assert command.results == [
        searching._NodeResult(origin.parent, ["finishactivate"]),
    ]
    command.execute()
    assert tracker.root.active_node is origin.parent
