from todo_tracker.tracker import Tracker, nodecreator
from todo_tracker import navigation
from todo_tracker import searching
from todo_tracker.nodes import references
from todo_tracker.nodes import node

import pytest


@pytest.fixture
def tracker():
    tracker = Tracker(skeleton=False)
    return tracker


@pytest.fixture(params=["depends", "reference"])
def reftype(request):
    return request.param


def _dump(nodes, getiterator=lambda x: x.children, depth=0, proxyinfo=True,
        ids=False):
    result = []
    for node in nodes:
        if ids:
            strnode = "%s#%s: %s" % (node.node_type, node.id, node.text)
        else:
            strnode = "%s: %s" % (node.node_type, node.text)
        if proxyinfo and isinstance(node, references.ProxyNode):
            strnode = "proxy: " + strnode
        result.append(" " * depth * 4 + strnode)
        result.extend(_dump(getiterator(node), getiterator, depth + 1,
            proxyinfo=proxyinfo, ids=ids))
    return result


def test_reference(tracker, reftype):
    tracker.deserialize("str",
        "task#11111: target\n"
        "    task#22222: somechild\n"
        "        task#33333: somechild\n"
        "    comment#44444: derp\n"
        "%s#aaaaa: <- target\n" % reftype
    )

    assert len(tracker.root.find_one(reftype).children) == 2

    assert _dump(tracker.root.find(reftype), ids=True) == [
        "%s#aaaaa: #11111" % reftype,
        "    proxy: task#22222: somechild",
        "        proxy: task#33333: somechild",
        "    proxy: comment#44444: derp"
    ]


def test_nested_reference(tracker, reftype):
    tracker.deserialize("str",
        "task#trgt1: target\n"
        "    task: somechild\n"
        "        task: somechild\n"
        "    comment: derp\n"
        "task#trgt2: some other thingy\n"
        "    task: do some work\n"
        "        reference: << > target\n"
        "    task: do some other work\n"
        "%s: <- task\n" % reftype
    )

    x = _dump(tracker.root.find(reftype))
    y = [
        "%s: #trgt2" % reftype,
        "    proxy: task: do some work",
        "        proxy: reference: #trgt1",
        "            proxy: task: somechild",
        "                proxy: task: somechild",
        "            proxy: comment: derp",
        "    proxy: task: do some other work"
    ]
    assert x == y


def test_nested_createchild(tracker, reftype):
    tracker.deserialize("str",
        "task#trgt1: target\n"
        "    task: somechild\n"
        "        task: somechild\n"
        "    comment: derp\n"
        "task#trgt2: some other thingy\n"
        "    task: do some work\n"
        "        reference: << > target\n"
        "    task: do some other work\n"
        "%s: <- task\n" % reftype
    )

    somechild = tracker.root.find_one("%s > task > "
                "reference > somechild" % reftype)
    node = somechild.createchild("task", "test")
    node2 = tracker.root.find_one("task > task > reference > task > test")
    assert node._px_target is node2
    assert node2._px_target is tracker.root.find_one("task > task > test")

    assert _dump(tracker.root.find("*")) == [
        "task: target",
        "    task: somechild",
        "        task: somechild",
        "        task: test",
        "    comment: derp",
        "task: some other thingy",
        "    task: do some work",
        "        reference: #trgt1",
        "            proxy: task: somechild",
        "                proxy: task: somechild",
        "                proxy: task: test",
        "            proxy: comment: derp",
        "    task: do some other work",
        "%s: #trgt2" % reftype,
        "    proxy: task: do some work",
        "        proxy: reference: #trgt1",
        "            proxy: task: somechild",
        "                proxy: task: somechild",
        "                proxy: task: test",
        "            proxy: comment: derp",
        "    proxy: task: do some other work"
    ]


def test_createchild(tracker, reftype):
    tracker.deserialize("str",
        "task#trgt1: target\n"
        "    task: somechild\n"
        "        task: somechild\n"
        "    comment: derp\n"
        "%s: <- target\n" % reftype
    )

    somechild = tracker.root.find_one("%s > somechild" % reftype)
    somechild.createchild("task", "test")

    assert _dump(tracker.root.find("*")) == [
        "task: target",
        "    task: somechild",
        "        task: somechild",
        "        task: test",
        "    comment: derp",
        "%s: #trgt1" % reftype,
        "    proxy: task: somechild",
        "        proxy: task: somechild",
        "        proxy: task: test",
        "    proxy: comment: derp",
    ]


def test_parent(tracker, reftype):
    tracker.deserialize("str",
        "task: target 1\n"
        "    task: target 2\n"
        "        task: target 3\n"
        "%s: <-" % reftype
    )

    proxy_3 = tracker.root.find_one("%s > * > target 3" % reftype)
    proxy_2 = tracker.root.find_one("%s > target 2" % reftype)
    reference = tracker.root.find_one(reftype)
    assert proxy_3.parent is proxy_2
    assert proxy_2.parent is reference


class TestProxynode(object):
    def test_activate(self, tracker, reftype):
        tracker.deserialize("str",
            "task: target 1\n"
            "    task: target 2\n"
            "        task: target 3\n"
            "%s: <-\n"
            "days\n"
            "    day: today\n"
            "        reference: << > %s\n"
            "            @active\n" % (reftype, reftype)
        )

        root = tracker.root

        navigation.done(tracker)
        assert root.active_node is root.find_one(
                "days > day > reference > task")
        navigation.done(tracker)
        assert root.active_node is root.find_one(
                "days > day > reference > task > task")
        navigation.done(tracker)
        assert root.active_node is root.find_one(
                "days > day > reference > task")
        navigation.done(tracker)
        assert root.active_node is root.find_one(
                "days > day > reference")
        navigation.done(tracker)
        assert root.active_node is root.find_one(
                "days > day")

        reference = tracker.root.find_one("days > day > reference")
        target_3 = tracker.root.find_one("** > target 3")
        target_2 = tracker.root.find_one("** > target 2")
        target_1 = tracker.root.find_one("target 1")

        assert reference.started
        assert target_1.started
        assert target_2.started > target_1.started
        assert target_3.started > target_2.started
        assert target_3.finished > target_3.started
        assert target_2.finished > target_3.finished
        assert not target_1.finished
        assert reference.finished > target_2.finished

    def test_reposition(self, tracker, reftype):
        tracker.deserialize("str",
            "task#trgt1: target 1\n"
            "    task: target 2\n"
            "        task: target 3\n"
            "    task: target 4\n"
            "%s: <- target 1\n" % reftype
        )

        target_3 = tracker.root.find_one("task > task > target 3")
        target_4 = tracker.root.find_one("task > target 4")

        proxy_3 = tracker.root.find_one("%s > task > target 3" % reftype)
        proxy_4 = tracker.root.find_one("%s > target 4" % reftype)

        proxy_3 = proxy_3.detach()
        proxy_3.parent = proxy_4

        proxy_4.addchild(proxy_3)

        assert _dump(tracker.root.find("*")) == [
            "task: target 1",
            "    task: target 2",
            "    task: target 4",
            "        task: target 3",
            "%s: #trgt1" % reftype,
            "    proxy: task: target 2",
            "    proxy: task: target 4",
            "        proxy: task: target 3",
        ]

    def test_reposition_2(self, tracker, reftype):
        tracker.deserialize("str",
            "task#trgt1: target 1\n"
            "    task: target 2\n"
            "        task: target 3\n"
            "    task: target 4\n"
            "%s#trgt2: <-\n"
            "reference: <-\n" % reftype
        )

        target_3 = tracker.root.find_one("task > task > target 3")
        target_4 = tracker.root.find_one("task > target 4")

        proxy_3 = tracker.root.find_one("%s -> "
                "reference > task > target 3" % reftype)

        detached = proxy_3.detach()
        detached.parent = target_4

        target_4.addchild(detached)
        assert target_4.find_one("*") is target_3

        assert _dump(tracker.root.find("*")) == [
            "task: target 1",
            "    task: target 2",
            "    task: target 4",
            "        task: target 3",
            "%s: #trgt1" % reftype,
            "    proxy: task: target 2",
            "    proxy: task: target 4",
            "        proxy: task: target 3",
            "reference: #trgt2",
            "    proxy: task: target 2",
            "    proxy: task: target 4",
            "        proxy: task: target 3",
        ]

    def test_reposition_3(self, tracker, reftype):
        tracker.deserialize("str",
            "task#trgt1: target 1\n"
            "    task: target 2\n"
            "    task: target 3\n"
            "%s: <- target 1\n" % reftype
        )

        target_2 = tracker.root.find_one("task > target 2")
        target_3 = tracker.root.find_one("task > target 3")

        proxy_2 = tracker.root.find_one("%s > target 2" % reftype)

        detached = proxy_2.detach()
        detached.parent = target_3

        target_3.addchild(detached)
        assert target_3.find_one("*") is target_2

        assert _dump(tracker.root.find("*")) == [
            "task: target 1",
            "    task: target 3",
            "        task: target 2",
            "%s: #trgt1" % reftype,
            "    proxy: task: target 3",
            "        proxy: task: target 2",
        ]

    def test_copy_1(self, tracker, reftype):
        tracker.deserialize("str",
            "task#trgt1: target 1\n"
            "    task: target 2\n"
            "        task: target 3\n"
            "    task: target 4\n"
            "%s: <- target 1\n" % reftype
        )

        target_3 = tracker.root.find_one("task > task > target 3")
        target_4 = tracker.root.find_one("task > target 4")

        proxy_3 = tracker.root.find_one(reftype + " > task > target 3")
        proxy_4 = tracker.root.find_one(reftype + " > target 4")

        target_3_new = proxy_3.copy()
        target_3_new.parent = proxy_4

        proxy_4.addchild(target_3_new)

        assert _dump(tracker.root.find("*")) == [
            "task: target 1",
            "    task: target 2",
            "        task: target 3",
            "    task: target 4",
            "        task: target 3",
            "%s: #trgt1" % reftype,
            "    proxy: task: target 2",
            "        proxy: task: target 3",
            "    proxy: task: target 4",
            "        proxy: task: target 3",
        ]

    def test_copy_2(self, tracker, reftype):
        tracker.deserialize("str",
            "task#trgt1: target 1\n"
            "    task: target 2\n"
            "        task: target 3\n"
            "    task: target 4\n"
            "%s: <- target 1\n" % reftype
        )

        target_3 = tracker.root.find_one("task > task > target 3")
        target_4 = tracker.root.find_one("task > target 4")

        proxy_3 = tracker.root.find_one(reftype + "> task > target 3")
        proxy_4 = tracker.root.find_one(reftype + "> target 4")

        target_3_new = proxy_3.copy(parent=proxy_4)

        target_4.addchild(target_3_new)

        assert _dump(tracker.root.find("*")) == [
            "task: target 1",
            "    task: target 2",
            "        task: target 3",
            "    task: target 4",
            "        task: target 3",
            reftype + ": #trgt1",
            "    proxy: task: target 2",
            "        proxy: task: target 3",
            "    proxy: task: target 4",
            "        proxy: task: target 3",
        ]

    def test_creation(self, tracker, reftype):
        tracker.deserialize("str",
            "task#trgt1: target 1\n"
            "    task: target 2\n"
            "%s: <-" % reftype
        )

        target_2 = tracker.root.find_one(reftype + " > ")

        target_2.createchild("task", "test")

        assert _dump(tracker.root.find("*")) == [
            "task: target 1",
            "    task: target 2",
            "        task: test",
            reftype + ": #trgt1",
            "    proxy: task: target 2",
            "        proxy: task: test"
        ]

    def test_whacky_reposition_setparent(self, tracker, reftype):
        tracker.deserialize("str",
            "task#toref: to reference\n"
            "    task: dummy\n"
            "        task: move me\n"
            "    task: parent\n"
            "%s: <- to reference\n" % reftype
        )

        proxy = tracker.root.find_one(reftype + " > task > move me")
        parent = tracker.root.find_one(reftype + "> task: parent")
        move_me = proxy._px_target

        move_me.detach()

        # this is to make sure assigning to parent doesn't blow things up
        proxy.parent = parent
        assert proxy.parent is parent

        parent.addchild(proxy)

        assert _dump(tracker.root.children) == [
            "task: to reference",
            "    task: dummy",
            "    task: parent",
            "        task: move me",
            reftype + ": #toref",
            "    proxy: task: dummy",
            "    proxy: task: parent",
            "        proxy: task: move me",
        ]

    def test_whacky_reposition_noneparent(self, tracker, reftype):
        tracker.deserialize("str",
            "task#toref: to reference\n"
            "    task: dummy\n"
            "        task: move me\n"
            "    task: parent\n"
            "%s: <- to reference\n" % reftype
        )

        proxy = tracker.root.find_one(reftype + "> task > move me")
        parent = tracker.root.find_one(reftype + "> task: parent")
        move_me = proxy._px_target

        move_me.detach()

        # this is to make sure assigning to parent doesn't blow things up
        proxy.parent = None
        assert proxy.parent is None

        parent.addchild(proxy)

        assert _dump(tracker.root.children) == [
            "task: to reference",
            "    task: dummy",
            "    task: parent",
            "        task: move me",
            reftype + ": #toref",
            "    proxy: task: dummy",
            "    proxy: task: parent",
            "        proxy: task: move me",
        ]

    def test_set_text(self, tracker, reftype):
        tracker.deserialize("str",
            "task#toref: to reference\n"
            "    task: to rename\n"
            "%s: <-" % reftype
        )

        to_rename = tracker.root.find_one(reftype + ' > to rename')
        to_rename.text = "renamed"

        assert _dump(tracker.root.children) == [
            "task: to reference",
            "    task: renamed",
            reftype + ": #toref",
            "    proxy: task: renamed"
        ]

    def test_export(self, tracker, reftype):
        tracker.deserialize("str",
            "task: to reference\n"
            "    task#aaaaa: parent\n"
            "        task: child 1\n"
            "        task: child 2\n"
            "        task: child 3\n"
            "%s: <-" % reftype
        )

        from todo_tracker.file_storage import serialize

        assert serialize(tracker.root.find_one(reftype + " > parent")) == [
            "task#aaaaa: parent"
        ]

    def test_no_options(self, tracker, reftype):
        tracker.deserialize("str",
            "task: to reference\n"
            "    task: target\n"
            "%s: <-" % reftype
        )

        target = tracker.root.find_one(reftype + "> target")

        with pytest.raises(AttributeError) as excinfo:
            target.options

        assert "do not have" in excinfo.value.message


class TestRefnode(object):
    def test_creation(self, tracker, reftype):
        tracker.deserialize("str",
            "task#abcde: target 1\n"
            "{}: <-".format(reftype)
        )

        ref = tracker.root.find_one(reftype)

        ref.createchild("task", "test")

        assert _dump(tracker.root.find("*")) == [
            "task: target 1",
            "    task: test",
            reftype + ": #abcde",
            "    proxy: task: test"
        ]

    def test_unfinish(self, tracker, reftype):
        tracker.deserialize("str",
            "task#abcde: target 1\n"
            "    task: target 2\n"
            "days\n"
            "    day: today\n"
            "        @active\n"
            "        {}: << >\n".format(reftype)
        )

        navigation.done(tracker.root)
        refnode = tracker.root.find_one("** > " + reftype)
        assert refnode.active
        assert tracker.root.active_node is refnode
        assert refnode.started
        assert not refnode.finished
        assert _dump([refnode]) == [
            reftype + ": #abcde",
            "    proxy: task: target 2"
        ]
        navigation.finish("<", tracker.root)
        target = tracker.root.find_one("task: target 1")
        if reftype == "depends":
            assert target.finished
        else:
            assert not target.finished
        assert refnode.finished
        assert _dump([refnode]) == [
            reftype + ": #abcde"
        ]
        assert not refnode.active
        assert tracker.root.active_node.node_type == "day"

        navigation.forceactivate(">", tracker.root)
        assert refnode.active
        assert tracker.root.active_node is refnode
        assert refnode.started
        assert not refnode.finished
        assert not target.finished
        assert _dump([refnode]) == [
            reftype + ": #abcde",
            "    proxy: task: target 2"
        ]

    def test_unfinish_notinitialized(self, tracker, reftype):
        tracker.deserialize("str",
            "task#abcde: target 1\n"
            "    task: target 2\n"
            "days\n"
            "    day: today\n"
            "        @active\n"
            "        {}: << >\n"
            "            @started\n"
            "            @finished\n".format(reftype)
        )

        refnode = tracker.root.find_one("** > " + reftype)
        assert refnode.finished
        assert _dump([refnode]) == [
            reftype + ": " + refnode.text
        ]
        assert not refnode.active
        assert tracker.root.active_node.node_type == "day"
        target = tracker.root.find_one("task: target 1")
        if reftype == "depends":
            assert target.finished
        else:
            assert not target.finished

        navigation.forceactivate(
            searching.Query(">"), tracker.root)
        assert refnode.active
        assert tracker.root.active_node is refnode
        assert refnode.started
        assert not refnode.finished
        assert not refnode._px_target.finished
        assert _dump([refnode]) == [
            reftype + ": #abcde",
            "    proxy: task: target 2"
        ]

    def test_unfinish_targetfinished(self, tracker, reftype):
        tracker.deserialize("str",
            "task#abcde: target 1\n"
            "    @started\n"
            "    @finished\n"
            "    task: target 2\n"
            "days\n"
            "    day: today\n"
            "        @active\n"
            "        {}: << >\n"
            "            @started\n"
            "            @finished\n".format(reftype)
        )

        refnode = tracker.root.find_one("** > " + reftype)
        assert refnode.finished
        assert _dump([refnode]) == [
            reftype + ": " + refnode.text
        ]
        assert not refnode.active
        assert tracker.root.active_node.node_type == "day"
        target = tracker.root.find_one("task: target 1")
        assert target.finished

        navigation.forceactivate(
            searching.Query(">"), tracker.root)
        assert refnode.active
        assert tracker.root.active_node is refnode
        assert refnode.started
        assert not refnode.finished
        assert not refnode._px_target.finished
        assert _dump([refnode]) == [
            reftype + ": #abcde",
            "    proxy: task: target 2"
        ]

    def test_initial_state(self, tracker, reftype):
        creator = tracker.nodecreator.creators[reftype]
        ref = creator(reftype, "<-")

        assert ref._px_target is None
        assert ref.children.length == 0

        tracker.deserialize("str",
            "task: target\n"
            "    task: child\n"
        )

        tracker.root.addchild(ref)

        assert ref._px_target is tracker.root.find_one("task")

    def test_export(self, tracker, reftype):
        tree = (
            "task#55555: target\n"
            "    task#44444: somechild\n"
            "        task#33333: somechild\n"
            "    comment#22222: derp\n"
            "{}#11111: %s\n".format(reftype)
        )
        tracker.deserialize("str", tree % "<- target")

        assert tracker.serialize("str") == tree % "#55555"

    def test_removechild(self, tracker, reftype):
        tracker.deserialize("str",
            "task#abcde: referenced\n"
            "    task: toremove\n"
            "{}: <-\n".format(reftype)
        )
        reference = tracker.root.find_one(reftype)

        toremove = reference.find_one("task")
        reference.removechild(toremove)
        assert _dump(tracker.root.children) == [
            "task: referenced",
            "{}: #abcde".format(reftype)
        ]


def test_child_loop(tracker, reftype):
    tracker.deserialize("str",
        "task: a\n"
        "    task: b\n"
        "        task: e\n"
        "        task: f\n"
        "        task: g\n"
        "    task: c\n"
        "    task: d\n"
        "%s: <-" % reftype
    )

    a = tracker.root.find_one(reftype)
    b = a.find_one("b")
    c = a.find_one("c")
    d = a.find_one("d")
    e = a.find_one("b > e")
    f = a.find_one("b > f")
    g = a.find_one("b > g")

    assert a.children._next_node is b
    assert a.children is b._prev_node
    assert c is b._next_node
    assert c._prev_node is b
    assert c._next_node is d
    assert c is d._prev_node
    assert a.children is d._next_node
    assert a.children._prev_node is d

    assert b.children._next_node is e
    assert b.children is e._prev_node
    assert f is e._next_node
    assert f._prev_node is e
    assert f._next_node is g
    assert f is g._prev_node
    assert b.children is g._next_node
    assert b.children._prev_node is g


class TestSearchCreateIntegration(object):
    def test_proxied_create(self, tracker, reftype):
        tracker.deserialize("str",
            "task: target\n"
            "%s: <-" % reftype
        )
        creator = searching.Creator(reftype + " > task: test")
        nodes = creator(tracker.root)
        assert len(nodes) == 1
        node = nodes[0]
        proxy = tracker.root.find_one(reftype + "> test")
        assert node is proxy

    def test_mini_child_loop(self, tracker, reftype):
        tracker.deserialize("str",
            "task: target\n"
            "%s: <-" % reftype
        )
        creator = searching.Creator(reftype + "> task: test")
        nodes = creator(tracker.root)
        assert len(nodes) == 1

        proxy_task = tracker.root.find_one(reftype + "> test")
        target_task = tracker.root.find_one("target > test")
        reference = tracker.root.find_one(reftype)
        target = tracker.root.find_one("target")

        unwrap = reference.unwrap
        wrap = reference.get_proxy

        assert unwrap(reference) is target
        assert wrap(target) is reference
        assert unwrap(proxy_task) is target_task
        assert wrap(target_task) is proxy_task

        assert target_task._next_node is target.children
        assert target_task._prev_node is target.children
        assert proxy_task._next_node is reference.children
        assert proxy_task._prev_node is reference.children

        assert target_task.parent is target
        assert proxy_task.parent is reference


def test_simple_interaction(tracker, reftype):
    tracker.deserialize("str",
        "task: target\n"
        "days\n"
        "    day: today\n"
        "        @started\n"
        "        %s: << > target\n"
        "            @active\n" % reftype
    )

    navigation.createauto("task: test", tracker)

    active_node = tracker.root.active_node
    proxy = tracker.root.find_one("days > today > " + reftype + " > test")
    target = tracker.root.find_one("target > test")
    assert active_node is proxy
    assert proxy is not target
    assert proxy._px_target is target
    assert proxy._px_root.get_proxy(target) is proxy

    navigation.createfinish("-> task: test 2", tracker)

    target = tracker.root.find_one("target")
    assert target.started
    first_child = target.children.next_neighbor
    assert first_child.started
    assert first_child.finished
    second_child = first_child.next_neighbor
    assert second_child.started
    assert not second_child.finished

    proxy_active = tracker.root.find_one("days > day > "
            + reftype + "> test 2")
    assert proxy_active is tracker.root.active_node


def test_another_interaction(tracker, reftype):
    tracker.deserialize("str",
        "task: target\n"
        "days\n"
        "    day: today\n"
        "        @started\n"
        "        %s: << > target\n"
        "            @active\n" % reftype
    )

    navigation.createauto("task: test 1", tracker)
    navigation.createfinish("< > +task: test 2", tracker)

    target = tracker.root.find_one("target")

    assert target.started
    first_child = target.children.next_neighbor
    assert first_child.started
    assert first_child.finished
    second_child = first_child.next_neighbor
    assert second_child.started
    assert not second_child.finished

    proxy_active = tracker.root.find_one("days > day > "
            + reftype + " > test 2")
    assert proxy_active is tracker.root.active_node


def test_str(tracker, reftype):
    tracker.deserialize("str",
        "task#abcde: target\n"
        "    comment: to test against\n"
        "%s: <-\n" % reftype
    )

    proxy = tracker.root.find_one(reftype + " > comment")
    proxy_target = proxy._px_target
    assert str(proxy) == str(proxy_target)

    ref = tracker.root.find_one(reftype)
    assert str(ref) == reftype + ": target"

    if reftype == "reference":
        ref2 = references.Reference("reference", "<- task: target")
        assert str(ref2) == "reference: <- task: target"
        assert ref2.text == "<- task: target"

        tracker.root.addchild(ref2)
        assert str(ref2) == reftype + ": target"
        assert ref2.text == "#abcde"
    elif reftype == "depends":
        for x in ["depends", "dep", "depend"]:
            ref2 = references.Depends(x, "<- task: target")
            assert str(ref2) == "depends: <- task: target"

            tracker.root.addchild(ref2)
            assert str(ref2) == reftype + ": target"
    else:  # pragma: no cover
        assert False


def test_active(tracker, reftype):
    tracker.deserialize("str",
        "task: target\n"
        "    task: to activate\n"
        "days\n"
        "    day: today\n"
        "        @started\n"
        "        %s: << > target\n"
        "            @active\n" % reftype
    )

    to_activate = tracker.root.find_one("days > day > "
            + reftype + " > to activate")
    target = to_activate._px_target

    tracker.root.activate(to_activate)
    assert tracker.root.active_node is to_activate
    assert to_activate.active
    assert not target.active
    options = to_activate.option_values()
    assert ("active", None, True) in options
    options = target.option_values()
    assert ("active", None, True) not in options

    ui_dict = to_activate.ui_serialize()
    options = [frozenset(x.items()) for x in ui_dict["options"]]
    assert set((("type", "active"), ("text", None))) in options
    assert ui_dict["active"]


def test_active_anomaly(tracker):
    return
    tracker.deserialize("str",
        "task: target\n"
        "days\n"
        "    day: today\n"
        "        @started\n"
        "        %s: << > target\n"
        "            @active\n" % reftype
    )

    # try a creator
    to_activate = tracker.root.find_one("days > day > "
            + reftype + " > to activate")
    target = to_activate._px_target

    tracker.root.activate(to_activate)
    assert tracker.root.active_node is to_activate
    assert to_activate.active
    assert not target.active
    options = to_activate.option_values()
    assert ("active", None, True) in options
    options = target.option_values()
    assert ("active", None, True) not in options

    ui_dict = to_activate.ui_serialize()
    options = [frozenset(x.items()) for x in ui_dict["options"]]
    assert set((("type", "active"), ("text", None))) in options
    assert ui_dict["active"]


def test_recursion(tracker, reftype):
    tracker.deserialize("str",
        "task#abcde: target\n"
        "    task: something\n"
        "        %s: < target\n" % reftype
    )

    assert _dump(tracker.root.children) == [
        "task: target",
        "    task: something",
        "        %s: #abcde" % reftype,
        "            proxy: task: something",
        "                proxy: %s: <recursing>" % reftype,
    ]


def test_ui_serialize(tracker, reftype):
    tracker.deserialize("str",
        "task: target\n"
        "    task: child\n"
        "%s: <-\n" % reftype
    )

    child = tracker.root.find_one(reftype + " > child")
    ui_info = child.ui_serialize({
        "input": True
    })
    assert ui_info["input"]
    assert "options" not in ui_info
    assert not ui_info.get("active", False)
    assert not ui_info.get("finished", False)


def test_ui_serialize_finished(tracker, reftype):
    tracker.deserialize("str",
        "task: target\n"
        "    task: child\n"
        "        @started\n"
        "        @finished\n"
        "%s: <-\n" % reftype
    )

    child = tracker.root.find_one(reftype + " > child")
    ui_info = child.ui_serialize({
        "input": True
    })
    assert ui_info["input"]
    assert 'options' in ui_info
    assert ui_info["options"][0]["type"] == "finished"
    assert not ui_info.get("active", False)
    assert ui_info.get("finished", False)


def test_no_query_finished(tracker, monkeypatch):
    # this one does _not_ apply to depends, hence no reftype
    # depends has to do a query to make sure the target is marked
    monkeypatch.setattr(references.Reference, "find_one", None)
    tracker.deserialize("str",
        "reference: <-\n"
        "    @started\n"
        "    @finished"
    )


def test_reference_finished(tracker, reftype):
    tracker.deserialize("str",
        "task: finished node\n"
        "    @started: June 1, 2013 1:00 am\n"
        "    @finished: June 1, 2013 2:00 am\n"
        "%s: <-" % reftype
    )

    reference = tracker.root.find_one(reftype)
    assert not reference.started
    assert reference.finished


def test_depends_finished_node(tracker, reftype):
    tracker.deserialize("str",
        "task: finished node\n"
        "    @started: June 1, 2013 1:00 am\n"
        "    @finished: June 1, 2013 2:00 am\n"
        "%s: <-\n"
        "    @finished: June 2, 2013 2:00 am" % reftype
    )

    reference = tracker.root.find_one(reftype)
    target = tracker.root.find_one("task")
    assert not reference.started
    assert reference.finished
    assert reference.finished > target.finished


def test_reference_started(tracker, reftype):
    tracker.deserialize("str",
        "task: finished node\n"
        "%s: <-\n"
        "    @started: June 1, 2013 1:00 am\n" % reftype
    )

    reference = tracker.root.find_one(reftype)
    target = reference._px_target
    assert reference.started == target.started
    assert not reference._px_didstart


def test_depends_propogate_finished(tracker):
    tracker.deserialize("str",
        "task: finished node\n"
        "depends: <-\n"
        "    @started: June 1, 2013 1:00 am\n"
        "    @finished: June 2, 2013 1:00 am\n"
    )

    dep = tracker.root.find_one("depends")
    target = tracker.root.find_one("task")
    assert dep._px_target is None
    assert dep.finished == target.finished
    assert not dep._px_didfinish


def test_reference_category(tracker, reftype):
    tracker.deserialize("str",
        "category: stuff\n"
        "    task: stuff\n"
        "days\n"
        "    day: today\n"
        "        %s: << > category" % reftype
    )

    ref = tracker.root.find_one('** > ' + reftype)
    tracker.root.activate(ref)

    assert ref.started


def test_reference_category_existingtime(tracker, reftype):
    tracker.deserialize("str",
        "category: stuff\n"
        "    task: stuff\n"
        "days\n"
        "    day: today\n"
        "        %s: << > category\n"
        "            @started: December 19, 1994 11:55 PM" % reftype
    )

    ref = tracker.root.find_one('** > ' + reftype)

    assert ref.started


def test_unwriteable_started(tracker, monkeypatch, reftype):
    called = []

    class NonTaskNode(node.Node):
        def __setattr__(self, name, value):
            if name == "started":
                called.append(True)
                raise AttributeError
            node.Node.__setattr__(self, name, value)

    monkeypatch.setitem(tracker.nodecreator.creators,
            "nontask", NonTaskNode)

    tracker.deserialize("str",
        "nontask: something\n"
        "    task: something else\n"
        "        task: something else 3\n"
        "    task: something else 2\n"
        "days\n"
        "    day: today\n"
        "        %s: << >\n"
        "            @started\n" % reftype
    )

    ref = tracker.root.find_one("days > day > " + reftype)

    assert called[0]
    assert ref.started
    assert not hasattr(ref._px_target, "started")


def test_unwriteable_finished(tracker, monkeypatch):
    called = []

    class NonTaskNode(node.Node):
        def __setattr__(self, name, value):
            if name == "finished":
                called.append(True)
                raise AttributeError
            node.Node.__setattr__(self, name, value)

    monkeypatch.setitem(tracker.nodecreator.creators,
            "nontask", NonTaskNode)

    tracker.deserialize("str",
        "nontask: something\n"
        "    task: something else\n"
        "        task: something else 3\n"
        "    task: something else 2\n"
        "days\n"
        "    day: today\n"
        "        depends: << >\n"
        "            @started\n"
        "            @finished\n"
    )

    ref = tracker.root.find_one("days > day > depends")

    assert called[0]
    assert ref.finished
    assert not hasattr(ref._px_target, "finished")


# search contexts or search quoting are required to make references useful
# test finish with behavior being called
# test target nodes with no finished or started slots
