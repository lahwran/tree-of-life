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

def test_reference_set_reset():
    tracker = Tracker(auto_skeleton=False)

    target1 = tracker.root\
        .createchild("task", "something")\
        .createchild("task", "sub_thing")
    target2 = tracker.root.createchild("task", "something else")
    target2.createchild("task", "sub thing 1")
    target2.createchild("task", "sub thing 2")

    reference = tracker.root.createchild("work on", "something > sub_thing")
    assert reference.target is target1
    assert target1.referred_to == set([reference])

    reference.text = "something else"
    assert target1.referred_to == set()
    assert target2.referred_to == set([reference])
    assert reference.target is target2

def test_nested_reference():
    tracker = Tracker(auto_skeleton=False)

    target = tracker.root.createchild("task", "something")
    child = target.createchild("task", "subthing")

    reference = tracker.root.createchild("work on", "something")
    assert set(reference.proxies.keys()) == set([target, target.children])

    subref = reference.createchild("work on", "subthing")
    assert list(reference.children) == [subref]
    assert list(reversed(reference.children)) == [subref]
    assert reference.target is target
    assert subref.target is child

def test_reference_autoproxy():
    tracker = Tracker(auto_skeleton=False)

    target = tracker.root.createchild("task", "something")
    child1 = target.createchild("task", "subthing 1")
    child2 = target.createchild("task", "subthing 2")
    child3 = target.createchild("task", "subthing 3")
    child2_5 = child2.createchild("task", "subthing 2.5")

    reference = tracker.root.createchild("work on", "something")

    assert [(child.node_type, child.text) for child in reference.children] == [
        ("work on", "subthing 1"),
        ("work on", "subthing 2"),
        ("work on", "subthing 3"),
    ]
    assert [(child.node_type, child.text) for child in reversed(reference.children)] == [
        ("work on", "subthing 3"),
        ("work on", "subthing 2"),
        ("work on", "subthing 1"),
    ]
    assert list(reference.children)[1].children.next_neighbor.text == "subthing 2.5"
    assert not any(child.is_solid for child in reference.children)
    assert reference.is_solid

def test_reference_emptyproxy():
    tracker = Tracker(auto_skeleton=False)

    target = tracker.root.createchild("task", "something")

    reference = tracker.root.createchild("work on", "something")
    assert list(reference.children) == []

def test_addchild_passthrough():
    tracker = Tracker(auto_skeleton=False)

    target = tracker.root.createchild("task", "something")

    reference = tracker.root.createchild("work on", "something")
    child1 = reference.createchild("task", "subthing 1")
    child2 = reference.createchild("task", "subthing 2")
    child3 = reference.createchild("task", "subthing 3")
    child2_5 = child2.createchild("task", "subthing 2.5")

    assert [(child.node_type, child.text) for child in reference.children] == [
        ("work on", "subthing 1"),
        ("work on", "subthing 2"),
        ("work on", "subthing 3"),
    ]
    assert [(child.node_type, child.text) for child in target.children] == [
        ("task", "subthing 1"),
        ("task", "subthing 2"),
        ("task", "subthing 3"),
    ]
    assert [(child.node_type, child.text) for child in reversed(reference.children)] == [
        ("work on", "subthing 3"),
        ("work on", "subthing 2"),
        ("work on", "subthing 1"),
    ]
    assert list(reference.children)[1].children.next_neighbor.text == "subthing 2.5"
    assert not any(child.is_solid for child in reference.children)
    assert reference.is_solid

def test_addchild_relative():
    tracker = Tracker(auto_skeleton=False)

    target = tracker.root.createchild("task", "something")
    target.createchild("task", "subthing 1")
    target.createchild("task", "subthing 3")

    reference = tracker.root.createchild("work on", "something")

    prev_node, next_node = reference.children

    created = reference.createchild("task", "subthing 2", after=prev_node, before=next_node)
    assert [(child.node_type, child.text) for child in reference.children] == [
        ("work on", "subthing 1"),
        ("work on", "subthing 2"),
        ("work on", "subthing 3"),
    ]
    assert [(child.node_type, child.text) for child in target.children] == [
        ("task", "subthing 1"),
        ("task", "subthing 2"),
        ("task", "subthing 3"),
    ]
    assert not any(child.is_solid for child in reference.children)
    assert reference.is_solid

def test_finish_solidify():
    tracker = Tracker(auto_skeleton=False)

    target = tracker.root.createchild("task", "something")
    child1 = target.createchild("task", "subthing 1")
    child2 = target.createchild("task", "subthing 2")
    child3 = target.createchild("task", "subthing 3")
    child2_5 = child2.createchild("task", "subthing 2.5")

    reference = tracker.root.createchild("work on", "something")

    tracker.activate(reference)

    tracker.activate_next()
    assert list(reference.children)[0].is_solid
    assert tracker.active_node.text == "subthing 1"

    tracker.activate_next()
    assert list(reference.children)[1].is_solid
    assert tracker.active_node.text == "subthing 2"


    assert [(child.node_type, child.text) for child in reference.children] == [
        ("worked on", "subthing 1"),
        ("work on", "subthing 2"),
        ("work on", "subthing 3"),
    ]

    assert reference.children_export() == list(reference.children)[0:2]

def test_jump_past_inactive():
    tracker = Tracker(auto_skeleton=False)

    target = tracker.root.createchild("task", "something")
    child1 = target.createchild("task", "subthing 1")
    child1_1 = child1.createchild("task", "subthing 1.1")
    child1_1_1 = child1_1.createchild("task", "subthing 1.1.1")

    reference = tracker.root.createchild("work on", "something")

    reference1_1_1 = reference.find_node(["*", "*", "*"])

    tracker.activate(reference1_1_1)

    assert reference.children_export() == [reference.find_node(["*"])]
