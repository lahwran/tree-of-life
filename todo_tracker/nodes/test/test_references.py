from todo_tracker.tracker import Tracker, nodecreator
from todo_tracker import navigation
from todo_tracker import searching
from todo_tracker.nodes import references

import pytest


@pytest.fixture
def tracker():
    tracker = Tracker(skeleton=False)
    return tracker


def _dump(nodes, getiterator=lambda x: x.children, depth=0):
    result = []
    for node in nodes:
        result.append(" " * depth * 4 + str(node))
        result.extend(_dump(getiterator(node), getiterator, depth + 1))
    return result


def test_reference(tracker):
    tracker.deserialize("str",
        "task: target\n"
        "    task: somechild\n"
        "        task: somechild\n"
        "    comment: derp\n"
        "reference: <- target\n"
    )

    assert len(tracker.root.find_one("reference").children) == 2

    assert _dump(tracker.root.find("reference")) == [
        "reference: <- target",
        "    <proxy>: task: somechild",
        "        <proxy>: task: somechild",
        "    <proxy>: comment: derp"
    ]


def test_nested_reference(tracker):
    tracker.deserialize("str",
        "task: target\n"
        "    task: somechild\n"
        "        task: somechild\n"
        "    comment: derp\n"
        "task: some other thingy\n"
        "    task: do some work\n"
        "        reference: << > target\n"
        "    task: do some other work\n"
        "reference: <- task\n"
    )

    x = _dump(tracker.root.find("reference"))
    y = [
        "reference: <- task",
        "    <proxy>: task: do some work",
        "        <proxy>: reference: << > target",
        "            <proxy>: task: somechild",
        "                <proxy>: task: somechild",
        "            <proxy>: comment: derp",
        "    <proxy>: task: do some other work"
    ]
    assert x == y


def test_nested_createchild(tracker):
    tracker.deserialize("str",
        "task: target\n"
        "    task: somechild\n"
        "        task: somechild\n"
        "    comment: derp\n"
        "task: some other thingy\n"
        "    task: do some work\n"
        "        reference: << > target\n"
        "    task: do some other work\n"
        "reference: <- task\n"
    )

    somechild = tracker.root.find_one("reference > task > "
                "reference > somechild")
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
        "        reference: << > target",
        "            <proxy>: task: somechild",
        "                <proxy>: task: somechild",
        "                <proxy>: task: test",
        "            <proxy>: comment: derp",
        "    task: do some other work",
        "reference: <- task",
        "    <proxy>: task: do some work",
        "        <proxy>: reference: << > target",
        "            <proxy>: task: somechild",
        "                <proxy>: task: somechild",
        "                <proxy>: task: test",
        "            <proxy>: comment: derp",
        "    <proxy>: task: do some other work"
    ]


def test_createchild(tracker):
    tracker.deserialize("str",
        "task: target\n"
        "    task: somechild\n"
        "        task: somechild\n"
        "    comment: derp\n"
        "reference: <- target\n"
    )

    somechild = tracker.root.find_one("reference > somechild")
    somechild.createchild("task", "test")

    assert _dump(tracker.root.find("*")) == [
        "task: target",
        "    task: somechild",
        "        task: somechild",
        "        task: test",
        "    comment: derp",
        "reference: <- target",
        "    <proxy>: task: somechild",
        "        <proxy>: task: somechild",
        "        <proxy>: task: test",
        "    <proxy>: comment: derp",
    ]


def test_parent(tracker):
    tracker.deserialize("str",
        "task: target 1\n"
        "    task: target 2\n"
        "        task: target 3\n"
        "reference: <-"
    )

    proxy_3 = tracker.root.find_one("reference > * > target 3")
    proxy_2 = tracker.root.find_one("reference > target 2")
    reference = tracker.root.find_one("reference")
    assert proxy_3.parent is proxy_2
    assert proxy_2.parent is reference


class TestProxynode(object):
    def test_activate(self, tracker):
        tracker.deserialize("str",
            "task: target 1\n"
            "    task: target 2\n"
            "        task: target 3\n"
            "reference: <-\n"
            "days\n"
            "    day: today\n"
            "        reference: << > reference\n"
            "            @active\n"
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

    def test_reposition(self, tracker):
        tracker.deserialize("str",
            "task: target 1\n"
            "    task: target 2\n"
            "        task: target 3\n"
            "    task: target 4\n"
            "reference: <- target 1\n"
        )

        target_3 = tracker.root.find_one("task > task > target 3")
        target_4 = tracker.root.find_one("task > target 4")

        proxy_3 = tracker.root.find_one("reference > task > target 3")
        proxy_4 = tracker.root.find_one("reference > target 4")

        proxy_3 = proxy_3.detach()
        proxy_3.parent = proxy_4

        proxy_4.addchild(proxy_3)

        assert _dump(tracker.root.find("*")) == [
            "task: target 1",
            "    task: target 2",
            "    task: target 4",
            "        task: target 3",
            "reference: <- target 1",
            "    <proxy>: task: target 2",
            "    <proxy>: task: target 4",
            "        <proxy>: task: target 3",
        ]

    def test_reposition_2(self, tracker):
        tracker.deserialize("str",
            "task: target 1\n"
            "    task: target 2\n"
            "        task: target 3\n"
            "    task: target 4\n"
            "reference: <-\n"
            "reference: <-\n"
        )

        target_3 = tracker.root.find_one("task > task > target 3")
        target_4 = tracker.root.find_one("task > target 4")

        proxy_3 = tracker.root.find_one("reference -> "
                "reference > task > target 3")

        detached = proxy_3.detach()
        detached.parent = target_4

        target_4.addchild(detached)
        assert target_4.find_one("*") is target_3

        assert _dump(tracker.root.find("*")) == [
            "task: target 1",
            "    task: target 2",
            "    task: target 4",
            "        task: target 3",
            "reference: <-",
            "    <proxy>: task: target 2",
            "    <proxy>: task: target 4",
            "        <proxy>: task: target 3",
            "reference: <-",
            "    <proxy>: task: target 2",
            "    <proxy>: task: target 4",
            "        <proxy>: task: target 3",
        ]

    def test_reposition_3(self, tracker):
        tracker.deserialize("str",
            "task: target 1\n"
            "    task: target 2\n"
            "    task: target 3\n"
            "reference: <- target 1\n"
        )

        target_2 = tracker.root.find_one("task > target 2")
        target_3 = tracker.root.find_one("task > target 3")

        proxy_2 = tracker.root.find_one("reference > target 2")

        detached = proxy_2.detach()
        detached.parent = target_3

        target_3.addchild(detached)
        assert target_3.find_one("*") is target_2

        assert _dump(tracker.root.find("*")) == [
            "task: target 1",
            "    task: target 3",
            "        task: target 2",
            "reference: <- target 1",
            "    <proxy>: task: target 3",
            "        <proxy>: task: target 2",
        ]

    def test_copy_1(self, tracker):
        tracker.deserialize("str",
            "task: target 1\n"
            "    task: target 2\n"
            "        task: target 3\n"
            "    task: target 4\n"
            "reference: <- target 1\n"
        )

        target_3 = tracker.root.find_one("task > task > target 3")
        target_4 = tracker.root.find_one("task > target 4")

        proxy_3 = tracker.root.find_one("reference > task > target 3")
        proxy_4 = tracker.root.find_one("reference > target 4")

        target_3_new = proxy_3.copy()
        target_3_new.parent = proxy_4

        proxy_4.addchild(target_3_new)

        assert _dump(tracker.root.find("*")) == [
            "task: target 1",
            "    task: target 2",
            "        task: target 3",
            "    task: target 4",
            "        task: target 3",
            "reference: <- target 1",
            "    <proxy>: task: target 2",
            "        <proxy>: task: target 3",
            "    <proxy>: task: target 4",
            "        <proxy>: task: target 3",
        ]

    def test_copy_2(self, tracker):
        tracker.deserialize("str",
            "task: target 1\n"
            "    task: target 2\n"
            "        task: target 3\n"
            "    task: target 4\n"
            "reference: <- target 1\n"
        )

        target_3 = tracker.root.find_one("task > task > target 3")
        target_4 = tracker.root.find_one("task > target 4")

        proxy_3 = tracker.root.find_one("reference > task > target 3")
        proxy_4 = tracker.root.find_one("reference > target 4")

        target_3_new = proxy_3.copy(parent=proxy_4)

        target_4.addchild(target_3_new)

        assert _dump(tracker.root.find("*")) == [
            "task: target 1",
            "    task: target 2",
            "        task: target 3",
            "    task: target 4",
            "        task: target 3",
            "reference: <- target 1",
            "    <proxy>: task: target 2",
            "        <proxy>: task: target 3",
            "    <proxy>: task: target 4",
            "        <proxy>: task: target 3",
        ]

    def test_creation(self, tracker):
        tracker.deserialize("str",
            "task: target 1\n"
            "    task: target 2\n"
            "reference: <-"
        )

        target_2 = tracker.root.find_one("reference > ")

        target_2.createchild("task", "test")

        assert _dump(tracker.root.find("*")) == [
            "task: target 1",
            "    task: target 2",
            "        task: test",
            "reference: <-",
            "    <proxy>: task: target 2",
            "        <proxy>: task: test"
        ]

    def test_whacky_reposition_setparent(self, tracker):
        tracker.deserialize("str",
            "task: to reference\n"
            "    task: dummy\n"
            "        task: move me\n"
            "    task: parent\n"
            "reference: <- to reference\n"
        )

        proxy = tracker.root.find_one("reference > task > move me")
        parent = tracker.root.find_one("reference > task: parent")
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
            "reference: <- to reference",
            "    <proxy>: task: dummy",
            "    <proxy>: task: parent",
            "        <proxy>: task: move me",
        ]

    def test_whacky_reposition_noneparent(self, tracker):
        tracker.deserialize("str",
            "task: to reference\n"
            "    task: dummy\n"
            "        task: move me\n"
            "    task: parent\n"
            "reference: <- to reference\n"
        )

        proxy = tracker.root.find_one("reference > task > move me")
        parent = tracker.root.find_one("reference > task: parent")
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
            "reference: <- to reference",
            "    <proxy>: task: dummy",
            "    <proxy>: task: parent",
            "        <proxy>: task: move me",
        ]

    def test_set_text(self, tracker):
        tracker.deserialize("str",
            "task: to reference\n"
            "    task: to rename\n"
            "reference: <-"
        )

        to_rename = tracker.root.find_one('reference > to rename')
        to_rename.text = "renamed"

        assert _dump(tracker.root.children) == [
            "task: to reference",
            "    task: renamed",
            "reference: <-",
            "    <proxy>: task: renamed"
        ]

    def test_export(self, tracker):
        tracker.deserialize("str",
            "task: to reference\n"
            "    task: parent\n"
            "        task: child 1\n"
            "        task: child 2\n"
            "        task: child 3\n"
            "reference: <-"
        )

        from todo_tracker.file_storage import serialize

        assert serialize(tracker.root.find_one("reference > parent")) == [
            "task: parent"
        ]

    def test_no_options(self, tracker):
        tracker.deserialize("str",
            "task: to reference\n"
            "    task: target\n"
            "reference: <-"
        )

        target = tracker.root.find_one("reference > target")

        with pytest.raises(AttributeError) as excinfo:
            target.options

        assert "do not have" in excinfo.value.message


class TestRefnode(object):
    def test_creation(self, tracker):
        tracker.deserialize("str",
            "task: target 1\n"
            "reference: <-"
        )

        ref = tracker.root.find_one("reference")

        ref.createchild("task", "test")

        assert _dump(tracker.root.find("*")) == [
            "task: target 1",
            "    task: test",
            "reference: <-",
            "    <proxy>: task: test"
        ]

    def test_unfinish(self, tracker):
        tracker.deserialize("str",
            "task: target 1\n"
            "    task: target 2\n"
            "days\n"
            "    day: today\n"
            "        @active\n"
            "        reference: << >\n"
        )

        navigation.done(tracker.root)
        refnode = tracker.root.find_one("** > reference")
        assert refnode.active
        assert tracker.root.active_node is refnode
        assert refnode.started
        assert not refnode.finished
        assert _dump([refnode]) == [
            "reference: << >",
            "    <proxy>: task: target 2"
        ]
        navigation.finish("<", tracker.root)
        assert refnode.finished
        assert _dump([refnode]) == [
            "reference: << >"
        ]
        assert not refnode.active
        assert tracker.root.active_node.node_type == "day"

        navigation.forceactivate(">", tracker.root)
        assert refnode.active
        assert tracker.root.active_node is refnode
        assert refnode.started
        assert not refnode.finished
        assert _dump([refnode]) == [
            "reference: << >",
            "    <proxy>: task: target 2"
        ]

    def test_unfinish_notinitialized(self, tracker):
        tracker.deserialize("str",
            "task: target 1\n"
            "    task: target 2\n"
            "days\n"
            "    day: today\n"
            "        @active\n"
            "        reference: << >\n"
            "            @started\n"
            "            @finished\n"
        )

        refnode = tracker.root.find_one("** > reference")
        assert refnode.finished
        assert _dump([refnode]) == [
            "reference: << >"
        ]
        assert not refnode.active
        assert tracker.root.active_node.node_type == "day"

        navigation.forceactivate(
            searching.Query(">"), tracker.root)
        assert refnode.active
        assert tracker.root.active_node is refnode
        assert refnode.started
        assert not refnode.finished
        assert _dump([refnode]) == [
            "reference: << >",
            "    <proxy>: task: target 2"
        ]

    def test_initial_state(self, tracker):
        ref = references.Reference("reference", "<-")

        assert ref._px_target is None
        assert ref.children.length == 0

        tracker.deserialize("str",
            "task: target\n"
            "    task: child\n"
        )

        tracker.root.addchild(ref)

        assert ref._px_target is tracker.root.find_one("task")

    def test_export(self, tracker):
        tree = (
            "task: target\n"
            "    task: somechild\n"
            "        task: somechild\n"
            "    comment: derp\n"
            "reference: <- target\n"
        )
        tracker.deserialize("str", tree)

        assert tracker.serialize("str") == tree

    def test_removechild(self, tracker):
        tracker.deserialize("str",
            "task: referenced\n"
            "    task: toremove\n"
            "reference: <-\n"
        )
        reference = tracker.root.find_one("reference")

        toremove = reference.find_one("task")
        reference.removechild(toremove)
        assert _dump(tracker.root.children) == [
            "task: referenced",
            "reference: <-"
        ]


def test_child_loop(tracker):
    tracker.deserialize("str",
        "task: a\n"
        "    task: b\n"
        "        task: e\n"
        "        task: f\n"
        "        task: g\n"
        "    task: c\n"
        "    task: d\n"
        "reference: <-"
    )

    a = tracker.root.find_one("reference")
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
    def test_proxied_create(self, tracker):
        tracker.deserialize("str",
            "task: target\n"
            "reference: <-"
        )
        creator = searching.Creator("reference > task: test")
        nodes = creator(tracker.root)
        assert len(nodes) == 1
        node = nodes[0]
        proxy = tracker.root.find_one("reference > test")
        assert node is proxy

    def test_mini_child_loop(self, tracker):
        tracker.deserialize("str",
            "task: target\n"
            "reference: <-"
        )
        creator = searching.Creator("reference > task: test")
        nodes = creator(tracker.root)
        assert len(nodes) == 1

        proxy_task = tracker.root.find_one("reference > test")
        target_task = tracker.root.find_one("target > test")
        reference = tracker.root.find_one("reference")
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


def test_simple_interaction(tracker):
    tracker.deserialize("str",
        "task: target\n"
        "days\n"
        "    day: today\n"
        "        @started\n"
        "        reference: << > target\n"
        "            @active\n"
    )

    navigation.createauto("task: test", tracker)

    active_node = tracker.root.active_node
    proxy = tracker.root.find_one("days > today > reference > test")
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

    proxy_active = tracker.root.find_one("days > day > reference > test 2")
    assert proxy_active is tracker.root.active_node


def test_another_interaction(tracker):
    tracker.deserialize("str",
        "task: target\n"
        "days\n"
        "    day: today\n"
        "        @started\n"
        "        reference: << > target\n"
        "            @active\n"
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

    proxy_active = tracker.root.find_one("days > day > reference > test 2")
    assert proxy_active is tracker.root.active_node

# test displaying as active
# search contexts or search quoting are required to make references useful
# test finished-loading creation of reference
