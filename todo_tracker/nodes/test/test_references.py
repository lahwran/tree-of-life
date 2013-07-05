from todo_tracker.tracker import Tracker, nodecreator


def _dump(nodes, getiterator=lambda x: x.children, depth=0):
    result = []
    for node in nodes:
        result.append(" "*depth*4 + str(node))
        result.extend(_dump(getiterator(node), getiterator, depth+1))
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


# test each attribute in Node
# test flattened iteration
# test arbitrary attr proxying
# test interacting with doubly nested references
