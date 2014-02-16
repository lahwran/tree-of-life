from __future__ import unicode_literals, print_function

import pytest
import string
import time
from itertools import izip_longest
from random import Random

from treeoflife import searching
from treeoflife.tracker import Tracker
from treeoflife.parseutil import ParseError
from treeoflife.test.util import FakeNodeCreator, match
from treeoflife.nodes.misc import GenericActivate
from treeoflife.file_storage import serialize


@pytest.fixture(params=[searching.parse_single, searching.parse])
def makequery(request):
    return request.param


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
    q = searching.parse_single(querytext)
    assert q.segments[0].pattern.type == node_type
    assert q.segments[0].pattern.text == text
    assert len(q.segments) == 1


def test_search(makequery):
    tracker = Tracker(False, FakeNodeCreator(GenericActivate))

    origin = tracker.root.createchild("task", "origin")
    target1 = origin.createchild("task", "target1")
    ignoreme = origin.createchild("task", "ignoreme")
    ignoreme.createchild("task", "ignore me too")
    peer = tracker.root.createchild("task", "peer")
    target2 = peer.createchild("task", "Target2")

    query1 = makequery("task: target1")
    assert query1(origin).list() == [target1]
    assert repr(query1)

    query2 = makequery("-> task: PEER > task: tarGet2")
    assert query2(origin).list() == [target2]
    assert repr(query2)


def test_id_lookup(makequery):
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

    query1 = makequery("#abcde")
    assert query1(origin).list() == [target1]
    assert query1(target2).list() == [target1]
    assert repr(query1)

    query2 = searching.parse_single("#orign -> task: peer > task: target2")
    assert query2(ignoreme).list() == [target2]
    assert query2(tracker.root).list() == [target2]
    assert repr(query2)

    query3 = makequery("#trgt2>")
    assert query3(ignoreme).list() == targetlist
    assert query3(tracker.root).list() == targetlist
    assert repr(query3)

    query4 = makequery("*: #abcde")
    assert query4(origin).list() == [target3]
    assert repr(query4)


def test_id_lookup_invalid():
    with pytest.raises(Exception):
        print(makequery("-> #orign"))
    with pytest.raises(Exception):
        print(makequery("-> task -> #orign"))
    with pytest.raises(Exception):
        print(makequery("#orign test"))


def test_pluralities():
    tracker = Tracker(False, FakeNodeCreator(GenericActivate))

    origin = tracker.root.createchild("task", "origin")

    targets = []

    for i in range(10):
        targets.append(tracker.root.createchild("task", "target %d" % i))

    query1 = searching.parse_single("-> * :{first}")
    assert query1(origin).list() == [targets[0]]
    assert repr(query1)

    query1 = searching.parse_single("-> * :{last}")
    assert query1(origin).list() == [targets[-1]]
    assert repr(query1)

    query1 = searching.parse_single("-> * :{many}")
    assert query1(origin).list() == targets
    assert repr(query1)


def test_flatten(makequery):
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

    query1 = makequery("**")

    assert query1(origin).list() == nodes
    assert repr(query1)

    query2 = makequery("** > task: target")
    a = query2(origin).list()
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

    query1 = searching.parse_single("task")
    assert query1(origin).list() == targets
    assert repr(query1)

    query2 = searching.parse_single("target1")
    assert query2(origin).list() == [target1]
    assert repr(query2)

    query3 = searching.parse_single("target2")
    assert query3(origin).list() == [target2]
    assert repr(query3)


def test_prev_peer():
    tracker = Tracker(False, FakeNodeCreator(GenericActivate))

    target1 = tracker.root.createchild("task", "target1")
    tracker.root.createchild("comment", "ignoreme")
    tracker.root.createchild("task", "don't ignore me")
    tracker.root.createchild("comment", "legitimately ignore me")
    target2 = tracker.root.createchild("task", "target2")
    origin = tracker.root.createchild("task", "origin")

    query1 = searching.parse_single("<- target1")
    assert query1(origin).list() == [target1]
    assert repr(query1)

    query2 = searching.parse_single("<- target2")
    assert query2(origin).list() == [target2]
    assert repr(query2)


def test_parents():
    tracker = Tracker(False, FakeNodeCreator(GenericActivate))

    parent3 = tracker.root.createchild("task", "parent3")
    parent2 = parent3.createchild("task", "parent2")
    parent1 = parent2.createchild("task", "parent1")
    origin1 = parent1.createchild("task", "origin1")

    expected = [
        parent1, parent2, parent3, tracker.root
    ]

    query = searching.parse_single("<")
    assert query(origin1).list() == expected
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

    query1 = searching.parse_single("task :{target}")
    assert query1(origin1).list() == targets
    assert repr(query1)

    query1 = searching.parse_single("task :{nontarget}")
    assert query1(origin1).list() == nontargets
    assert repr(query1)


def test_node_with_colon():
    tracker = Tracker(False, FakeNodeCreator(GenericActivate))
    origin = tracker.root.createchild("task", 'origin')
    target = tracker.root.createchild("task", 'target: with colon')

    query = searching.parse_single("-> task: target: with colon")
    assert query(origin).list() == [target]
    assert repr(query)


class TestCreate(object):
    def test_create_node(self):
        tracker = Tracker(False, FakeNodeCreator(GenericActivate))

        origin = tracker.root.createchild("task", "origin")

        creator = searching.parse_create("task: Target")
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

        creator = searching.parse_create("task: target")
        created = creator(origin)

        results = list(origin.children)
        assert (results[:2] + results[3:]) == nodes
        assert results[2].node_type == "task"
        assert results[2].text == "target"
        assert created == results[2]
        assert repr(creator)

    def test_existing_query(self):
        tracker = Tracker(False, FakeNodeCreator(GenericActivate))

        origin = tracker.root.createchild("task", "origin")

        selector = searching.parse_single("task: target")

        creator = searching.parse_create(query=selector)
        creator(origin)

        assert match("\n".join(serialize(origin)), (
            "task#?????: origin\n"
            "    task#?????: target"
        ))
        assert repr(creator)

    # removed this functionality

    #def test_multi_create(self):
    #    tracker = Tracker(False)

    #    nodes = []

    #    origin = tracker.root.createchild("task", "origin")
    #    nodes.append(origin.createchild("task", "finished"))
    #    nodes[-1].start()
    #    nodes[-1].finish()
    #    nodes.append(origin.createchild("task", "finished 2"))
    #    nodes[-1].start()
    #    nodes[-1].finish()
    #    nodes.append(origin.createchild("task", "started"))
    #    nodes[-1].start()
    #    nodes.append(origin.createchild("task", "untouched"))
    #    nodes.append(origin.createchild("task", "untouched 2"))

    #    selector = searching.parse_single("task: target :{many}")
    #    #import pudb; pudb.set_trace()
    #    creator = searching.parse_create(query=selector)
    #    #import pytest; pytest.set_trace()
    #    created = creator(origin)

    #    results = list(origin.children)
    #    assert [
    #        results[0],
    #        results[1],
    #        results[3],
    #        results[5],
    #        results[7],
    #    ] == nodes
    #    assert results[2].node_type == "task"
    #    assert results[2].text == "target"
    #    assert results[4].node_type == "task"
    #    assert results[4].text == "target"
    #    assert results[6].node_type == "task"
    #    assert results[6].text == "target"
    #    assert created == [results[2], results[4], results[6]]
    #    assert repr(creator)

    def test_after_create(self):
        tracker = Tracker(False, FakeNodeCreator(GenericActivate))

        origin = tracker.root.createchild("task", "origin")
        origin.createchild("task", "1")
        origin.createchild("task", "2")
        origin.createchild("task", "3")
        origin.createchild("task", "4")
        origin.createchild("task", "5")

        creator = searching.parse_create_single("task: target :{first, after}")
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

        creator = searching.parse_create_single(
                "task: target :{after, last, finished}")
        created = creator(origin)

        results = list(origin.children)
        assert (results[:2] + results[3:]) == nodes
        assert results[2].node_type == "task"
        assert results[2].text == "target"
        assert created == results[2]
        assert repr(creator)

    def test_last(self):
        creator = searching.parse_create_single("+task: last")
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
        creator = searching.parse_create_single("-task: first")
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
        creator = searching.parse_create_single("<- +task: first")
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
        creator = searching.parse_create_single("<- -task: first")
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
        creator = searching.parse_create_single("<- task: mid")
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
        creator = searching.parse_create_single("<- task: mid")
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
        creator = searching.parse_create_single(
                "<- task: first :{before, last}")
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
        creator = searching.parse_create_single("-> task: mid")
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
        creator = searching.parse_create_single(
                "<- task: target :{first, started}")
        assert not creator.is_before
        assert creator.last_segment.tags == set(["started"])
        assert creator.last_segment.plurality == "first"
        assert repr(creator)

    def test_empty_prev_peer(self):
        tracker = Tracker(False)
        origin = tracker.root.createchild("task", "origin")
        creator = searching.parse_create("<- task: derp")
        creator(origin)
        assert match("\n".join(serialize(tracker.root, is_root=True)), (
            "task#?????: derp\n"
            "task#?????: origin"
        ))
        assert repr(creator)

    def test_empty_next_peer(self):
        tracker = Tracker(False)
        origin = tracker.root.createchild("task", "origin")
        creator = searching.parse_create("-> task: derp")
        creator(origin)
        assert match("\n".join(serialize(tracker.root, is_root=True)), (
            "task#?????: origin\n"
            "task#?????: derp"
        ))
        assert repr(creator)

    def test_default_first(self):
        creator = searching.parse_create("-> > task: target")

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
        creator = searching.parse_create("-> :{last} > task: target")

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

    #def test_many(self):
    #    creator = searching.parse_create("-> :{many} > task: TARGET")

    #    tracker = Tracker(False, FakeNodeCreator(GenericActivate))

    #    origin = tracker.root.createchild("task", "origin")
    #    tracker.root.createchild("task", "expected 1")
    #    tracker.root.createchild("task", "no longer expected 2")
    #    tracker.root.createchild("task", "no longer expected 3")

    #    creator(origin)

    #    assert match("\n".join(serialize(tracker.root, is_root=True)), (
    #        "task#?????: origin\n"
    #        "task#?????: expected 1\n"
    #        "    task#?????: TARGET\n"
    #        "task#?????: no longer expected 2\n"
    #        "task#?????: no longer expected 3\n"
    #    ))
    #    assert repr(creator)


# crashers
# :{first} < :{last} < :{last}
# :{first} < :{last} ->
# < :{last}
# derp :{ derp

def test_massive(makequery):
    tracker = Tracker(False, FakeNodeCreator(GenericActivate))
    for x in range(10):  # 10 nodes ....
        tracker.root.createchild("node")

    # this loop is to warm up the jit.
    for _ in range(3):
        initial = time.time()
        explosive = "><><><><><><><><><><><><><><><><><><>"
        # ... to the power of len([x for x in explosive if x == ">"]) ...
        massive_query = makequery(explosive)
        for x in range(3):
            with pytest.raises(searching.TooManyMatchesError):
                # ... should abort after a fixed number of ticks
                results = massive_query(tracker.root).list()
        final = time.time()
        delta = final - initial
        print(delta)

    # and said aborting of the search should be nice and early,
    # so the user doesn't see any performance issues
    if makequery is searching.parse_single:
        assert delta < 0.3
    else:
        assert delta < 0.6


def test_queries_structure():
    tracker = Tracker(False, FakeNodeCreator(GenericActivate))

    query = searching.parse_single("> task: 'rigidly defined node'")
    queries = searching.Queries(query)

    origin = tracker.root.createchild("task", "origin")
    target1 = origin.createchild("task", "rigidly defined node")

    assert queries.queries == (query,)

    assert queries(origin).nodes().list() == [target1]
    assert queries(origin).list() == queries(origin).nodes().list()
    # assert list(queries(origin).results)
    # assert list(queries(origin).actions)
    assert queries(origin).first() is target1
    assert queries(origin).first() is queries(origin).one()

    with pytest.raises(searching.NoMatchesError):
        queries(target1).one()
    assert queries(target1).first() is None


# to test: filters. create obeys filters. create only creates one node.
# create only uses first filter.
