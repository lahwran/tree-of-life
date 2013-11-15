import pytest
import string
import time
from itertools import izip_longest
from random import Random

from todo_tracker import searching
from todo_tracker.tracker import Tracker
from todo_tracker.parseutil import ParseError
from todo_tracker.test.util import FakeNodeCreator, match
from todo_tracker.nodes.misc import GenericActivate
from todo_tracker.file_storage import serialize


def test_tags_parsing():
    assert searching.SearchGrammar("around, the, world").tag_texts() == (
            "around", "the", "world")
    assert searching.SearchGrammar("around the world").tag_texts() == (
            "around the world",)


def test_derp():
    assert searching.SearchGrammar(" :{test}").tags() == ("test",)
    assert searching.SearchGrammar(" :{test}").tagged_node()
    assert searching.SearchGrammar("test :{test, test}").tagged_node()
    assert repr(searching.SearchGrammar("test > test :{test}").query())
    assert repr(searching.SearchGrammar("test :{test}").query())


@pytest.mark.parametrize(("querytext", "node_type", "text"), [
    ("reference: '<< > target'", "reference", "<< > target"),

    (r"reference: '<< > \'target'", "reference", r"""<< > 'target"""),

    (r"""reference: '<< > \\"target'""", "reference", r"""<< > \"target"""),

    (r'reference: "<< > \"target\""', "reference", '<< > "target"'),

    ("""reference: '<< > target > reference: "<< > *"' """,
        "reference", '<< > target > reference: "<< > *"'),

    ('''reference: "<< > target > reference: '<< > *'" ''',
        "reference", "<< > target > reference: '<< > *'"),

    ("task: do something with 'something'",
        "task", "do something with 'something'"),

    ('task: do something with "something"',
        "task", 'do something with "something"'),

    ('''task: do 'something' with "something"''',
        "task", 'do \'something\' with "something"'),
])
def test_quoting(querytext, node_type, text):
    q = searching.Query(querytext)
    assert q.segments[0].pattern.type == node_type
    assert q.segments[0].pattern.text == text
    assert len(q.segments) == 1


def test_search():
    tracker = Tracker(False, FakeNodeCreator(GenericActivate))

    origin = tracker.root.createchild("task", "origin")
    target1 = origin.createchild("task", "target1")
    ignoreme = origin.createchild("task", "ignoreme")
    ignoreme.createchild("task", "ignore me too")
    peer = tracker.root.createchild("task", "peer")
    target2 = peer.createchild("task", "Target2")

    query1 = searching.Query("task: target1")
    assert list(query1([origin])) == [target1]
    assert repr(query1)

    query2 = searching.Query("-> task: PEER > task: tarGet2")
    assert list(query2([origin])) == [target2]
    assert repr(query2)


def test_id_lookup():
    tracker = Tracker(False, FakeNodeCreator(GenericActivate))

    origin = tracker.root.createchild("task", "origin", nodeid="orign")
    target1 = origin.createchild("task", "target1", nodeid="abcde")
    target3 = origin.createchild("task", "#abcde")
    ignoreme = origin.createchild("task", "ignoreme")
    ignoreme.createchild("task", "ignore me too")
    peer = tracker.root.createchild("task", "peer")
    target2 = peer.createchild("task", "target2", nodeid="trgt2")
    targetlist = [
        target2.createchild("task") for x in range(10)]

    query1 = searching.Query("#abcde")
    assert list(query1([origin])) == [target1]
    assert list(query1([target2])) == [target1]
    assert repr(query1)

    query2 = searching.Query("#orign -> task: peer > task: target2")
    assert list(query2([ignoreme])) == [target2]
    assert list(query2([tracker.root])) == [target2]
    assert repr(query2)

    query3 = searching.Query("#trgt2>")
    assert list(query3([ignoreme])) == targetlist
    assert list(query3([tracker.root])) == targetlist
    assert repr(query3)

    query4 = searching.Query("*: #abcde")
    assert list(query4([origin])) == [target3]
    assert repr(query4)


def test_id_lookup_invalid():
    with pytest.raises(Exception):
        print searching.Query("-> #orign")
    with pytest.raises(Exception):
        print searching.Query("-> task -> #orign")
    with pytest.raises(Exception):
        print searching.Query("#orign test")


def test_pluralities():
    tracker = Tracker(False, FakeNodeCreator(GenericActivate))

    origin = tracker.root.createchild("task", "origin")

    targets = []

    for i in range(10):
        targets.append(tracker.root.createchild("task", "target %d" % i))

    query1 = searching.Query("-> * :{first}")
    assert list(query1([origin])) == [targets[0]]
    assert repr(query1)

    query1 = searching.Query("-> * :{last}")
    assert list(query1([origin])) == [targets[-1]]
    assert repr(query1)

    query1 = searching.Query("-> * :{many}")
    assert list(query1([origin])) == targets
    assert repr(query1)


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

    query1 = searching.Query("**")

    assert list(query1(origin)) == nodes
    assert repr(query1)

    query2 = searching.Query("** > task: target")
    a = list(query2(origin))
    assert a == targets
    assert repr(query2)


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

    query1 = searching.Query("task")
    assert list(query1(origin)) == targets
    assert repr(query1)

    query2 = searching.Query("target1")
    assert list(query2(origin)) == [target1]
    assert repr(query2)

    query3 = searching.Query("target2")
    assert list(query3(origin)) == [target2]
    assert repr(query3)


def test_prev_peer():
    tracker = Tracker(False, FakeNodeCreator(GenericActivate))

    target1 = tracker.root.createchild("task", "target1")
    tracker.root.createchild("comment", "ignoreme")
    tracker.root.createchild("task", "don't ignore me")
    tracker.root.createchild("comment", "legitimately ignore me")
    target2 = tracker.root.createchild("task", "target2")
    origin = tracker.root.createchild("task", "origin")

    query1 = searching.Query("<- target1")
    assert list(query1(origin)) == [target1]
    assert repr(query1)

    query2 = searching.Query("<- target2")
    assert list(query2(origin)) == [target2]
    assert repr(query2)


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

    query = searching.Query("<")
    assert list(query([origin1, origin2])) == expected
    assert repr(query)


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

    query1 = searching.Query("task :{target}")
    assert list(query1([origin1, origin2])) == targets
    assert repr(query1)

    query1 = searching.Query("task :{nontarget}")
    assert list(query1([origin1, origin2])) == nontargets
    assert repr(query1)


def test_node_with_colon():
    tracker = Tracker(False, FakeNodeCreator(GenericActivate))
    origin = tracker.root.createchild("task", 'origin')
    target = tracker.root.createchild("task", 'target: with colon')

    query = searching.Query("-> task: target: with colon")
    assert list(query(origin)) == [target]
    assert repr(query)


class TestCreate(object):
    def test_create_node(self):
        tracker = Tracker(False, FakeNodeCreator(GenericActivate))

        origin = tracker.root.createchild("task", "origin")

        creator = searching.Creator("task: Target")
        creator(origin)

        assert match("\n".join(serialize(origin)), (
            "task#?????: origin\n"
            "    task#?????: Target"
        ))
        assert repr(creator)

    def test_create_node_existing(self):
        tracker = Tracker(False)

        nodes = []

        origin = tracker.root.createchild("task", "origin")
        nodes.append(origin.createchild("task", "finished"))
        nodes[-1].start()
        nodes[-1].finish()
        nodes.append(origin.createchild("task", "finished 2"))
        nodes[-1].start()
        nodes[-1].finish()
        nodes.append(origin.createchild("task", "started"))
        nodes[-1].start()
        nodes.append(origin.createchild("task", "untouched"))
        nodes.append(origin.createchild("task", "untouched 2"))

        creator = searching.Creator("task: target")
        #import pytest; pytest.set_trace()
        #import pudb; pudb.set_trace()
        created = creator(origin)

        results = list(origin.children)
        assert (results[:2] + results[3:]) == nodes
        assert results[2].node_type == "task"
        assert results[2].text == "target"
        assert created == [results[2]]
        assert repr(creator)

    def test_existing_joinedsearch(self):
        tracker = Tracker(False, FakeNodeCreator(GenericActivate))

        origin = tracker.root.createchild("task", "origin")

        selector = searching.Query("task: target")

        creator = searching.Creator(joinedsearch=selector)
        creator(origin)

        assert match("\n".join(serialize(origin)), (
            "task#?????: origin\n"
            "    task#?????: target"
        ))
        assert repr(creator)

    def test_multi_create(self):
        tracker = Tracker(False)

        nodes = []

        origin = tracker.root.createchild("task", "origin")
        nodes.append(origin.createchild("task", "finished"))
        nodes[-1].start()
        nodes[-1].finish()
        nodes.append(origin.createchild("task", "finished 2"))
        nodes[-1].start()
        nodes[-1].finish()
        nodes.append(origin.createchild("task", "started"))
        nodes[-1].start()
        nodes.append(origin.createchild("task", "untouched"))
        nodes.append(origin.createchild("task", "untouched 2"))

        selector = searching.Query("task: target :{many}")
        #import pudb; pudb.set_trace()
        creator = searching.Creator(joinedsearch=selector)
        #import pytest; pytest.set_trace()
        created = creator(origin)

        results = list(origin.children)
        assert [
            results[0],
            results[1],
            results[3],
            results[5],
            results[7],
        ] == nodes
        assert results[2].node_type == "task"
        assert results[2].text == "target"
        assert results[4].node_type == "task"
        assert results[4].text == "target"
        assert results[6].node_type == "task"
        assert results[6].text == "target"
        assert created == [results[2], results[4], results[6]]
        assert repr(creator)

    def test_after_create(self):
        tracker = Tracker(False, FakeNodeCreator(GenericActivate))

        origin = tracker.root.createchild("task", "origin")
        origin.createchild("task", "1")
        origin.createchild("task", "2")
        origin.createchild("task", "3")
        origin.createchild("task", "4")
        origin.createchild("task", "5")

        creator = searching.Creator("task: target :{first, after}")
        creator(origin)

        assert match("\n".join(serialize(origin)), (
            "task#?????: origin\n"
            "    task#?????: 1\n"
            "    task#?????: target\n"
            "    task#?????: 2\n"
            "    task#?????: 3\n"
            "    task#?????: 4\n"
            "    task#?????: 5"
        ))
        assert repr(creator)

    def test_after_started(self):
        tracker = Tracker(False)

        nodes = []

        origin = tracker.root.createchild("task", "origin")
        nodes.append(origin.createchild("task", "finished"))
        nodes[-1].start()
        nodes[-1].finish()
        nodes.append(origin.createchild("task", "finished 2"))
        nodes[-1].start()
        nodes[-1].finish()
        nodes.append(origin.createchild("task", "started"))
        nodes[-1].start()
        nodes.append(origin.createchild("task", "untouched"))
        nodes.append(origin.createchild("task", "untouched 2"))

        creator = searching.Creator("task: target :{after, last, finished}")
        #import pytest; pytest.set_trace()
        created = creator(origin)

        results = list(origin.children)
        assert (results[:2] + results[3:]) == nodes
        assert results[2].node_type == "task"
        assert results[2].text == "target"
        assert created == [results[2]]
        assert repr(creator)

    def test_last(self):
        creator = searching.Creator("+task: last")
        assert not creator.is_before
        assert creator.last_segment.tags == set()
        assert creator.last_segment.plurality == "last"

        tracker = Tracker(False)

        nodes = []
        origin = tracker.root.createchild("task", "origin")

        nodes.append(origin.createchild("task", "finished"))
        nodes[-1].start()
        nodes[-1].finish()
        nodes.append(origin.createchild("task", "finished 2"))
        nodes[-1].start()
        nodes[-1].finish()
        nodes.append(origin.createchild("task", "started"))
        nodes[-1].start()
        nodes.append(origin.createchild("task", "untouched"))
        nodes.append(origin.createchild("task", "untouched 2"))

        creator(origin)

        results = list(origin.children)

        assert results[-1].node_type == "task"
        assert results[-1].text == "last"
        assert results[:-1] == nodes
        assert repr(creator)

    def test_early(self):
        creator = searching.Creator("-task: first")
        assert creator.is_before
        assert creator.last_segment.tags == set()
        assert creator.last_segment.plurality == "first"

        tracker = Tracker(False)

        nodes = []
        origin = tracker.root.createchild("task", "origin")

        nodes.append(origin.createchild("task", "finished"))
        nodes[-1].start()
        nodes[-1].finish()
        nodes.append(origin.createchild("task", "finished 2"))
        nodes[-1].start()
        nodes[-1].finish()
        nodes.append(origin.createchild("task", "started"))
        nodes[-1].start()
        nodes.append(origin.createchild("task", "untouched"))
        nodes.append(origin.createchild("task", "untouched 2"))

        creator(origin)

        results = list(origin.children)

        assert results[0].node_type == "task"
        assert results[0].text == "first"
        assert results[1:] == nodes
        assert repr(creator)

    def test_early_reversed(self):
        creator = searching.Creator("<- +task: first")
        assert creator.is_before
        assert creator.last_segment.tags == set()
        assert creator.last_segment.plurality == "last"

        tracker = Tracker(False)

        nodes = []

        nodes.append(tracker.root.createchild("task", "finished"))
        nodes[-1].start()
        nodes[-1].finish()
        nodes.append(tracker.root.createchild("task", "finished 2"))
        nodes[-1].start()
        nodes[-1].finish()
        nodes.append(tracker.root.createchild("task", "started"))
        nodes[-1].start()
        nodes.append(tracker.root.createchild("task", "untouched"))
        nodes.append(tracker.root.createchild("task", "untouched 2"))

        origin = tracker.root.createchild("task", "origin")
        nodes.append(origin)

        creator(origin)

        results = list(tracker.root.children)

        assert results[0].node_type == "task"
        assert results[0].text == "first"
        assert results[1:] == nodes
        assert repr(creator)

    def test_last_reversed(self):
        creator = searching.Creator("<- -task: first")
        assert not creator.is_before
        assert creator.last_segment.tags == set()
        assert creator.last_segment.plurality == "first"

        tracker = Tracker(False)

        nodes = []

        nodes.append(tracker.root.createchild("task", "finished"))
        nodes[-1].start()
        nodes[-1].finish()
        nodes.append(tracker.root.createchild("task", "finished 2"))
        nodes[-1].start()
        nodes[-1].finish()
        nodes.append(tracker.root.createchild("task", "started"))
        nodes[-1].start()
        nodes.append(tracker.root.createchild("task", "untouched"))
        nodes.append(tracker.root.createchild("task", "untouched 2"))

        origin = tracker.root.createchild("task", "origin")
        nodes.append(origin)

        creator(origin)

        results = list(tracker.root.children)

        assert results[-2].node_type == "task"
        assert results[-2].text == "first"
        assert results[:-2] + [origin] == nodes
        assert repr(creator)

    def test_default_reversed(self):
        creator = searching.Creator("<- task: mid")
        assert not creator.is_before
        assert creator.last_segment.tags == set(["can_activate"])
        assert creator.last_segment.plurality == "first"

        tracker = Tracker(False)

        nodes = []

        nodes.append(tracker.root.createchild("task", "finished"))
        nodes[-1].start()
        nodes[-1].finish()
        nodes.append(tracker.root.createchild("task", "started"))
        nodes[-1].start()
        nodes.append(tracker.root.createchild("task", "untouched"))
        nodes.append(tracker.root.createchild("task", "untouched 2"))
        nodes.append(tracker.root.createchild("task", "finished 2"))
        nodes[-1].start()
        nodes[-1].finish()

        origin = tracker.root.createchild("task", "origin")
        nodes.append(origin)

        creator(origin)

        results = list(tracker.root.children)

        assert results[-3].node_type == "task"
        assert results[-3].text == "mid"
        assert results[:-3] + results[-2:] == nodes
        assert repr(creator)

    def test_reversed_no_match(self):
        creator = searching.Creator("<- task: mid")
        assert not creator.is_before
        assert creator.last_segment.tags == set(["can_activate"])
        assert creator.last_segment.plurality == "first"

        tracker = Tracker(False)

        nodes = []

        nodes.append(tracker.root.createchild("task", "finished"))
        nodes[-1].start()
        nodes[-1].finish()
        nodes.append(tracker.root.createchild("task", "finished 2"))
        nodes[-1].start()
        nodes[-1].finish()

        origin = tracker.root.createchild("task", "origin")
        nodes.append(origin)

        creator(origin)

        results = list(tracker.root.children)

        assert results[-2].node_type == "task"
        assert results[-2].text == "mid"
        assert results[:-2] + results[-1:] == nodes
        assert repr(creator)

    def test_before_explicit(self):
        creator = searching.Creator("<- task: first :{before, last}")
        assert creator.is_before
        assert creator.last_segment.tags == set()
        assert creator.last_segment.plurality == "last"

        tracker = Tracker(False)

        nodes = []

        nodes.append(tracker.root.createchild("task", "finished"))
        nodes[-1].start()
        nodes[-1].finish()
        nodes.append(tracker.root.createchild("task", "finished 2"))
        nodes[-1].start()
        nodes[-1].finish()
        nodes.append(tracker.root.createchild("task", "started"))
        nodes[-1].start()
        nodes.append(tracker.root.createchild("task", "untouched"))
        nodes.append(tracker.root.createchild("task", "untouched 2"))

        origin = tracker.root.createchild("task", "origin")
        nodes.append(origin)

        creator(origin)

        results = list(tracker.root.children)

        assert results[0].node_type == "task"
        assert results[0].text == "first"
        assert results[1:] == nodes
        assert repr(creator)

    def test_after_match(self):
        creator = searching.Creator("-> task: mid")
        assert creator.is_before
        assert creator.last_segment.tags == set(["can_activate"])
        assert creator.last_segment.plurality == "first"

        tracker = Tracker(False)

        nodes = []

        origin = tracker.root.createchild("task", "origin")
        nodes.append(origin)

        nodes.append(tracker.root.createchild("task", "finished"))
        nodes[-1].start()
        nodes[-1].finish()
        nodes.append(tracker.root.createchild("task", "finished 2"))
        nodes[-1].start()
        nodes[-1].finish()
        nodes.append(tracker.root.createchild("task", "started 1"))
        nodes[-1].start()
        nodes.append(tracker.root.createchild("task", "untouched"))

        creator(origin)

        results = list(tracker.root.children)

        assert results[-3].node_type == "task"
        assert results[-3].text == "mid"
        assert results[:-3] + results[-2:] == nodes
        assert repr(creator)

    def test_other_tag(self):
        creator = searching.Creator("<- task: target :{first, started}")
        assert not creator.is_before
        assert creator.last_segment.tags == set(["started"])
        assert creator.last_segment.plurality == "first"
        assert repr(creator)

    def test_empty_prev_peer(self):
        tracker = Tracker(False)
        origin = tracker.root.createchild("task", "origin")
        creator = searching.Creator("<- task: derp")
        creator(origin)
        assert match("\n".join(serialize(tracker.root, is_root=True)), (
            "task#?????: derp\n"
            "task#?????: origin"
        ))
        assert repr(creator)

    def test_empty_next_peer(self):
        tracker = Tracker(False)
        origin = tracker.root.createchild("task", "origin")
        creator = searching.Creator("-> task: derp")
        creator(origin)
        assert match("\n".join(serialize(tracker.root, is_root=True)), (
            "task#?????: origin\n"
            "task#?????: derp"
        ))
        assert repr(creator)

    def test_default_first(self):
        creator = searching.Creator("-> > task: target")

        tracker = Tracker(False, FakeNodeCreator(GenericActivate))

        origin = tracker.root.createchild("task", "origin")
        tracker.root.createchild("task", "expected")
        tracker.root.createchild("task", "ignore 1")
        tracker.root.createchild("task", "ignore 2")
        tracker.root.createchild("task", "ignore 3")

        creator(origin)

        assert match("\n".join(serialize(tracker.root, is_root=True)), (
            "task#?????: origin\n"
            "task#?????: expected\n"
            "    task#?????: target\n"
            "task#?????: ignore 1\n"
            "task#?????: ignore 2\n"
            "task#?????: ignore 3"
        ))
        assert repr(creator)

    def test_last_2(self):
        creator = searching.Creator("-> :{last} > task: target")

        tracker = Tracker(False, FakeNodeCreator(GenericActivate))

        origin = tracker.root.createchild("task", "origin")
        tracker.root.createchild("task", "ignore 1")
        tracker.root.createchild("task", "ignore 2")
        tracker.root.createchild("task", "ignore 3")
        tracker.root.createchild("task", "expected")

        creator(origin)

        assert match("\n".join(serialize(tracker.root, is_root=True)), (
            "task#?????: origin\n"
            "task#?????: ignore 1\n"
            "task#?????: ignore 2\n"
            "task#?????: ignore 3\n"
            "task#?????: expected\n"
            "    task#?????: target"
        ))
        assert repr(creator)

    def test_many(self):
        creator = searching.Creator("-> :{many} > task: TARGET")

        tracker = Tracker(False, FakeNodeCreator(GenericActivate))

        origin = tracker.root.createchild("task", "origin")
        tracker.root.createchild("task", "expected 1")
        tracker.root.createchild("task", "expected 2")
        tracker.root.createchild("task", "expected 3")

        creator(origin)

        assert match("\n".join(serialize(tracker.root, is_root=True)), (
            "task#?????: origin\n"
            "task#?????: expected 1\n"
            "    task#?????: TARGET\n"
            "task#?????: expected 2\n"
            "    task#?????: TARGET\n"
            "task#?????: expected 3\n"
            "    task#?????: TARGET"
        ))
        assert repr(creator)


# crashers
# :{first} < :{last} < :{last}
# :{first} < :{last} ->
# < :{last}
# derp :{ derp

def test_massive():
    tracker = Tracker(False, FakeNodeCreator(GenericActivate))
    for x in range(10):
        tracker.root.createchild("node")

    massive_query = searching.Query("><><><><><><>")

    initial = time.time()
    for x in range(3):
        with pytest.raises(searching.TooManyMatchesError):
            results = list(massive_query(tracker.root))
    final = time.time()
    delta = final - initial

    assert delta < 0.3
