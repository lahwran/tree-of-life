from todo_tracker.tracker import Tracker, nodecreator
from todo_tracker import navigation


def _dump(nodes, getiterator=lambda x: x.children, depth=0):
    result = []
    for node in nodes:
        result.append(" " * depth * 4 + str(node))
        result.extend(_dump(getiterator(node), getiterator, depth + 1))
    return result


def test_reference():
    tracker = Tracker(skeleton=False)
    tracker.deserialize("str",
        "task: target\n"
        "    task: somechild\n"
        "        task: somechild\n"
        "    comment: derp\n"
        "reference: <- target\n"
    )

    assert _dump(tracker.root.find("reference")) == [
        "reference: <- target",
        "    <proxy>: task: somechild",
        "        <proxy>: task: somechild",
        "    <proxy>: comment: derp"
    ]


def test_nested_reference():
    tracker = Tracker(skeleton=False)
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


def test_nested_createchild():
    tracker = Tracker(skeleton=False)
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


def test_createchild():
    tracker = Tracker(skeleton=False)
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


def test_export():
    tracker = Tracker(skeleton=False)
    tree = (
        "task: target\n"
        "    task: somechild\n"
        "        task: somechild\n"
        "    comment: derp\n"
        "reference: <- target\n"
    )
    tracker.deserialize("str", tree)

    assert tracker.serialize("str") == tree


def test_parent():
    tracker = Tracker(skeleton=False)
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


def test_activate():
    tracker = Tracker(skeleton=False)
    tracker.deserialize("str",
        "task: target 1\n"
        "    task: target 2\n"
        "        task: target 3\n"
        "days\n"
        "    day: today\n"
        "        reference: << > target 1\n"
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

    reference = tracker.root.find_one("** > reference")
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


def test_reposition():
    tracker = Tracker(skeleton=False)
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

    proxy_3.detach()
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


def test_reposition_2():
    tracker = Tracker(skeleton=False)
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

    proxy_3.detach()
    proxy_3.parent = target_4

    target_4.addchild(proxy_3)
    assert target_4.find_one("*") is target_3

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


def test_copy_1():
    tracker = Tracker(skeleton=False)
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


def test_copy_2():
    tracker = Tracker(skeleton=False)
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

# test each attribute in Node
# test flattened iteration
# test arbitrary attr proxying
# test interacting with doubly nested references
