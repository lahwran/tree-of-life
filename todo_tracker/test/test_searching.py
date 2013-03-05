import pytest

from todo_tracker import searching
from todo_tracker.tracker import Tracker
from todo_tracker.parseutil import ParseError
from todo_tracker.test.util import FakeNodeCreator
from todo_tracker.nodes.misc import GenericActivate


def test_tags_parsing():
    assert searching.SearchGrammar("around, the, world").tag_texts() == (
            "around", "the", "world")
    assert searching.SearchGrammar("around the world").tag_texts() == (
            "around the world",)


def test_derp():
    assert searching.SearchGrammar(" :{test}").tags() == ("test",)
    assert searching.SearchGrammar(" :{test}").tagged_node()
    assert searching.SearchGrammar("test :{test, test}").tagged_node()
    searching.SearchGrammar("test > test :{test}").query()
    searching.SearchGrammar("test :{test}").query()


def test_search():
    tracker = Tracker(False, FakeNodeCreator(GenericActivate))

    origin = tracker.root.createchild("task", "origin")
    target1 = origin.createchild("task", "target1")
    ignoreme = origin.createchild("task", "ignoreme")
    ignoreme.createchild("task", "ignore me too")
    peer = tracker.root.createchild("task", "peer")
    target2 = peer.createchild("task", "target2")

    query1 = searching.query("task: target1")
    assert list(query1([origin])) == [target1]

    query2 = searching.query("-> task: peer > task: target2")
    assert list(query2([origin])) == [target2]


def test_pluralities():
    tracker = Tracker(False, FakeNodeCreator(GenericActivate))

    origin = tracker.root.createchild("task", "origin")

    targets = []

    for i in range(10):
        targets.append(tracker.root.createchild("task", "target %d" % i))

    query1 = searching.query("-> * :{first}")
    assert list(query1([origin])) == [targets[0]]

    query1 = searching.query("-> * :{last}")
    assert list(query1([origin])) == [targets[-1]]

    query1 = searching.query("-> * :{many}")
    assert list(query1([origin])) == targets


def test_flatten():
    tracker = Tracker(False, FakeNodeCreator(GenericActivate))

    origin = tracker.root.createchild("task", "origin")

    nodes = []
    targets = []

    nodes.append(origin.createchild("task", "a"))
    nodes.append(nodes[-1].createchild("task", "target"))
    targets.append(nodes[-1])
    nodes.append(origin.createchild("task", "c"))
    nodes.append(nodes[-1].createchild("task", "target"))
    targets.append(nodes[-1])
    nodes.append(nodes[-1].createchild("task", "e"))
    nodes.append(nodes[-2].createchild("task", "target"))
    targets.append(nodes[-1])
    nodes.append(nodes[-1].createchild("task", "g"))
    nodes.append(origin.createchild("task", "target"))
    targets.append(nodes[-1])
    nodes.append(nodes[-1].createchild("task", "target"))
    targets.append(nodes[-1])
    nodes.append(nodes[-1].createchild("task", "target"))
    targets.append(nodes[-1])
    nodes.append(nodes[-2].createchild("task", "k"))

    query1 = searching.query("**")

    assert list(query1(origin)) == nodes

    query2 = searching.query("** > task: target")
    a = list(query2(origin))
    assert a == targets


def test_flat_text():
    tracker = Tracker(False, FakeNodeCreator(GenericActivate))

    origin = tracker.root.createchild("task", "origin")

    targets = []
    target1 = origin.createchild("task", "target1")
    targets.append(target1)
    origin.createchild("comment", "ignoreme")
    targets.append(origin.createchild("task", "don't ignore me"))
    origin.createchild("comment", "legitimately ignore me")
    target2 = origin.createchild("task", "target2")
    targets.append(target2)

    query1 = searching.query("task")
    assert list(query1(origin)) == targets

    query2 = searching.query("target1")
    assert list(query2(origin)) == [target1]

    query3 = searching.query("target2")
    assert list(query3(origin)) == [target2]


def test_prev_peer():
    tracker = Tracker(False, FakeNodeCreator(GenericActivate))

    target1 = tracker.root.createchild("task", "target1")
    tracker.root.createchild("comment", "ignoreme")
    tracker.root.createchild("task", "don't ignore me")
    tracker.root.createchild("comment", "legitimately ignore me")
    target2 = tracker.root.createchild("task", "target2")
    origin = tracker.root.createchild("task", "origin")

    query1 = searching.query("<- target1")
    assert list(query1(origin)) == [target1]

    query2 = searching.query("<- target2")
    assert list(query2(origin)) == [target2]


def test_parents():
    tracker = Tracker(False, FakeNodeCreator(GenericActivate))

    parent6 = tracker.root.createchild("task", "parent6")
    parent5 = parent6.createchild("task", "parent5")
    parent4 = parent5.createchild("task", "parent4")
    origin2 = parent4.createchild("task", "origin2")

    parent3 = tracker.root.createchild("task", "parent3")
    parent2 = parent3.createchild("task", "parent2")
    parent1 = parent2.createchild("task", "parent1")
    origin1 = parent1.createchild("task", "origin1")

    expected = [
        parent1, parent2, parent3, tracker.root,
        parent4, parent5, parent6, tracker.root
    ]

    query = searching.query("<")
    assert list(query([origin1, origin2])) == expected


def test_tags_filtering():
    class CustomGeneric(GenericActivate):
        def search_tags(self):
            return self.text.split()

    tracker = Tracker(False, FakeNodeCreator(CustomGeneric))

    targets = []
    nontargets = []

    origin1 = tracker.root.createchild("task", "origin")
    targets.append(origin1.createchild("task", "target node"))
    nontargets.append(origin1.createchild("task", "nontarget node"))
    targets.append(origin1.createchild("task", "target node"))
    nontargets.append(origin1.createchild("task", "nontarget node"))

    origin2 = tracker.root.createchild("task", "origin")
    targets.append(origin2.createchild("task", "target node"))
    nontargets.append(origin2.createchild("task", "nontarget node"))
    targets.append(origin2.createchild("task", "target node"))
    nontargets.append(origin2.createchild("task", "nontarget node"))

    query1 = searching.query("task :{target}")
    assert list(query1([origin1, origin2])) == targets

    query1 = searching.query("task :{nontarget}")
    assert list(query1([origin1, origin2])) == nontargets


def test_node_with_colon():
    tracker = Tracker(False, FakeNodeCreator(GenericActivate))
    origin = tracker.root.createchild("task", 'origin')
    target = tracker.root.createchild("task", 'target: with colon')

    query = searching.query("-> task: target: with colon")
    assert list(query(origin)) == [target]
